from __future__ import annotations

import json
import os
import signal
import subprocess

import pytest

from regie_bench.cli import (
    _event_usage,
    _invoke_regie,
    _summary,
    evaluate_trial,
    load_cases,
    prepare_case,
)


def test_case_catalog_covers_distinct_orchestration_outcomes():
    cases = load_cases()

    assert len(cases) == 7
    assert {case.expected_route for case in cases.values()} == {"direct", "planned"}
    assert {case.expected_outcome for case in cases.values()} == {
        "completed",
        "clarification",
        "infrastructure_halt",
    }


def test_event_usage_counts_agents_not_persisted_in_task_state():
    usage = _event_usage([
        {
            "component": "agent", "name": "codex:planner",
            "fresh_tokens": 10, "cached_tokens": 20, "cost_usd": 0.1,
        },
        {
            "component": "agent", "name": "codex:plan-reviewer",
            "fresh_tokens": 30, "cached_tokens": 40, "cost_usd": 0.2,
        },
        {"component": "gate", "name": "test"},
    ])

    assert usage == {
        "attempts": 2,
        "fresh_tokens": 40,
        "cached_tokens": 60,
        "cost_usd": 0.3,
        "models": ["codex:plan-reviewer", "codex:planner"],
    }


def test_invoke_regie_kills_process_group_when_interrupted(tmp_path, monkeypatch):
    class InterruptedProcess:
        pid = 4321
        returncode = None

        def __init__(self):
            self.communications = 0

        def communicate(self, timeout=None):
            self.communications += 1
            if self.communications == 1:
                raise KeyboardInterrupt
            return "partial output", None

    process = InterruptedProcess()
    signals = []
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))

    with pytest.raises(KeyboardInterrupt):
        _invoke_regie(tmp_path, tmp_path / "regie", 1)

    assert signals == [(process.pid, signal.SIGTERM)]
    assert "BENCHMARK INTERRUPTED" in (tmp_path / "regie.log").read_text()


def test_prepare_case_creates_clean_repo_and_isolated_local_origin(tmp_path):
    case = load_cases()["reject-blank-title"]

    trial = prepare_case(case, tmp_path, "claude", trial_id="trial-one")

    repo = trial / "repo"
    assert (repo / ".git").is_dir()
    assert (trial / "origin.git").is_dir()
    assert (trial / "regie-home").is_dir()
    assert 'enabled = ["claude"]' in (repo / "regie.toml").read_text()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    assert status.stdout == ""


def test_evaluate_clarification_uses_structured_blocked_question(tmp_path):
    case = load_cases()["clarify-multiselect"]
    trial = prepare_case(case, tmp_path, "codex", trial_id="trial-clarify")
    repo = trial / "repo"
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    state = {
        "stage": "halted",
        "execution_route": "direct",
        "halt_reason": "clarification needed on T1",
        "worktree_path": str(repo),
        "base_sha": base_sha,
        "planner_attempts": [],
        "product_owner_attempts": [],
        "final_review_attempts": [],
        "tasks": {
            "T1": {
                "attempts": {
                    "test": [],
                    "build": [
                        {
                            "binding": {"cli": "codex", "model": "test-model"},
                            "blocked_question": "Which bulk actions should multi-select enable?",
                            "metrics": {
                                "new_input_tokens": 10,
                                "cached_input_tokens": 20,
                                "cache_write_input_tokens": 2,
                                "output_tokens": 3,
                                "cost_usd": 0.01,
                            },
                        }
                    ],
                    "review": [],
                },
                "specialist_attempts": {},
            }
        },
    }
    run_dir = trial / "regie-home" / "runs" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(json.dumps(state))
    (run_dir / "events.jsonl").write_text(
        json.dumps({
            "kind": "attempt",
            "task": "T1",
            "stage": "build",
            "attempt": 1,
            "outcome": "blocked",
            "turns": 1,
            "duration_seconds": 4.5,
            "binding": {"cli": "codex", "model": "test-model"},
            "metrics": {
                "new_input_tokens": 10,
                "cached_input_tokens": 20,
                "cache_write_input_tokens": 2,
                "output_tokens": 3,
                "cost_usd": 0.01,
            },
        }) + "\n"
    )

    result = evaluate_trial(
        case,
        trial,
        label="test",
        provider="codex",
        regie_version="abc123",
        exit_code=0,
        elapsed=1.25,
    )

    assert result["passed"] is True
    assert result["fresh_tokens"] == 15
    assert result["cached_tokens"] == 20
    assert result["models"] == ["codex:test-model"]
    assert result["stage_breakdown"] == [{
        "component": "agent",
        "task": "T1",
        "stage": "build",
        "name": "codex:test-model",
        "attempt": 1,
        "outcome": "blocked",
        "turns": 1,
        "duration_seconds": 4.5,
        "fresh_tokens": 15,
        "cached_tokens": 20,
        "cost_usd": 0.01,
    }]
    assert (trial / "result.json").is_file()


def test_completed_case_evaluators_reject_the_unchanged_fixture(tmp_path):
    completed = [
        case for case in load_cases().values()
        if case.expected_outcome == "completed"
    ]

    for case in completed:
        trial = prepare_case(case, tmp_path, "codex", trial_id=f"trial-{case.id}")
        env = os.environ.copy()
        env["TARGET_REPO"] = str(trial / "repo")
        result = subprocess.run(
            ["node", "--test", str(case.evaluator)],
            cwd=trial / "repo",
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0, f"{case.id} evaluator accepts the baseline"


def test_summary_uses_medians_and_rates():
    records = [
        {
            "passed": True,
            "route_match": True,
            "elapsed_seconds": 1.0,
            "attempts": 1,
            "fresh_tokens": 100,
            "cached_tokens": 200,
            "cost_usd": 0.1,
        },
        {
            "passed": False,
            "route_match": True,
            "elapsed_seconds": 3.0,
            "attempts": 3,
            "fresh_tokens": 300,
            "cached_tokens": 400,
            "cost_usd": 0.3,
        },
    ]

    summary = _summary(records)

    assert summary["pass_rate"] == 0.5
    assert summary["route_accuracy"] == 1.0
    assert summary["median_seconds"] == 2.0
    assert summary["median_fresh_tokens"] == 200
