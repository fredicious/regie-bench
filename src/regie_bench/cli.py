from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = ROOT / "results"


@dataclass(frozen=True)
class Case:
    id: str
    fixture: str
    description: str
    expected_route: str
    expected_outcome: str
    path: Path
    evaluator: Path | None
    overlay: Path | None

    @property
    def brief(self) -> Path:
        return self.path / "brief.md"


def load_cases(root: Path = ROOT) -> dict[str, Case]:
    cases: dict[str, Case] = {}
    for manifest in sorted((root / "cases").glob("*/*/case.toml")):
        raw = tomllib.loads(manifest.read_text())
        case_id = raw["id"]
        if case_id in cases:
            raise ValueError(f"duplicate benchmark case: {case_id}")
        case_dir = manifest.parent
        evaluator = case_dir / raw["evaluator"] if raw.get("evaluator") else None
        overlay = case_dir / "overlay"
        cases[case_id] = Case(
            id=case_id,
            fixture=raw["fixture"],
            description=raw["description"],
            expected_route=raw["expected_route"],
            expected_outcome=raw["expected_outcome"],
            path=case_dir,
            evaluator=evaluator,
            overlay=overlay if overlay.is_dir() else None,
        )
    return cases


def _run(command: list[str], cwd: Path, *, check: bool = True,
         env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _git(repo: Path, *args: str) -> str:
    return _run(["git", *args], repo).stdout.strip()


def _copy_overlay(source: Path, destination: Path) -> None:
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _set_provider(config_path: Path, provider: str) -> None:
    if provider not in {"codex", "claude"}:
        raise ValueError("provider must be 'codex' or 'claude'")
    text = config_path.read_text()
    marker = 'enabled = ["codex"]'
    if marker not in text:
        raise ValueError(f"expected provider marker missing from {config_path}")
    config_path.write_text(text.replace(marker, f'enabled = ["{provider}"]'))


def prepare_case(case: Case, results_root: Path, provider: str,
                 trial_id: str | None = None) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    trial_id = trial_id or f"{stamp}-{case.id}-{time.time_ns() % 1_000_000_000:09d}"
    trial = results_root / trial_id
    if trial.exists():
        raise FileExistsError(trial)
    repo = trial / "repo"
    remote = trial / "origin.git"
    home = trial / "regie-home"
    trial.mkdir(parents=True)
    shutil.copytree(ROOT / "fixtures" / case.fixture, repo)
    if case.overlay:
        _copy_overlay(case.overlay, repo)
    _set_provider(repo / "regie.toml", provider)
    shutil.copy2(case.brief, trial / "brief.md")
    home.mkdir()

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Régie Bench")
    _git(repo, "config", "user.email", "regie-bench@example.invalid")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "benchmark fixture baseline")
    _run(["git", "init", "--bare", "-q", "--initial-branch=main", str(remote)], trial)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    metadata = {
        "schema_version": 1,
        "trial_id": trial_id,
        "case_id": case.id,
        "provider": provider,
        "prepared_at": datetime.now(UTC).isoformat(),
    }
    (trial / "trial.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return trial


def _regie_version(regie_root: Path) -> str:
    result = _run(["git", "status", "--porcelain"], regie_root, check=False)
    sha = _run(["git", "rev-parse", "HEAD"], regie_root, check=False).stdout.strip()
    return sha + ("+dirty" if result.stdout.strip() else "")


def _invoke_regie(trial: Path, regie_root: Path, timeout_minutes: int) -> tuple[int, float]:
    repo = trial / "repo"
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env["REGIE_HOME"] = str(trial / "regie-home")
    env["REGIE_NOTIFICATIONS"] = "0"
    command = [
        "uv", "run", "--project", str(regie_root), "regie", "run",
        str(trial / "brief.md"), "--repo", str(repo),
        "--profiles", str(regie_root / "profiles"), "--autonomous",
    ]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=trial,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout_minutes * 60)
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        output += f"\nBENCHMARK TIMEOUT after {timeout_minutes} minutes\n"
        exit_code = 124
    elapsed = time.monotonic() - started
    (trial / "regie.log").write_text(output)
    return exit_code, elapsed


def _state_path(trial: Path) -> Path | None:
    states = sorted((trial / "regie-home" / "runs").glob("*/state.json"))
    return states[-1] if states else None


def _all_attempts(state: dict[str, Any]) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for key in ("planner_attempts", "product_owner_attempts", "final_review_attempts"):
        attempts.extend(state.get(key, []))
    for task in state.get("tasks", {}).values():
        for stage_attempts in task.get("attempts", {}).values():
            attempts.extend(stage_attempts)
        for specialist_attempts in task.get("specialist_attempts", {}).values():
            attempts.extend(specialist_attempts)
    return attempts


def _usage(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "attempts": len(attempts),
        "fresh_tokens": 0,
        "cached_tokens": 0,
        "cost_usd": 0.0,
        "models": [],
    }
    models: set[str] = set()
    for attempt in attempts:
        metrics = attempt.get("metrics", {})
        totals["fresh_tokens"] += (
            metrics.get("new_input_tokens", 0)
            + metrics.get("cache_write_input_tokens", 0)
            + metrics.get("output_tokens", 0)
        )
        totals["cached_tokens"] += metrics.get("cached_input_tokens", 0)
        totals["cost_usd"] += metrics.get("cost_usd", 0.0)
        binding = attempt.get("binding", {})
        if binding.get("cli") and binding.get("model"):
            models.add(f'{binding["cli"]}:{binding["model"]}')
    totals["cost_usd"] = round(totals["cost_usd"], 6)
    totals["models"] = sorted(models)
    return totals


def _acceptance(case: Case, worktree: Path, trial: Path) -> tuple[bool | None, str]:
    if not case.evaluator:
        return None, "no acceptance evaluator for this outcome"
    env = os.environ.copy()
    env["TARGET_REPO"] = str(worktree)
    result = _run(["node", "--test", str(case.evaluator)], worktree, check=False, env=env)
    (trial / "acceptance.log").write_text(result.stdout)
    return result.returncode == 0, result.stdout


def evaluate_trial(case: Case, trial: Path, *, label: str, provider: str,
                   regie_version: str, exit_code: int, elapsed: float) -> dict[str, Any]:
    state_file = _state_path(trial)
    state = json.loads(state_file.read_text()) if state_file else {}
    attempts = _all_attempts(state)
    usage = _usage(attempts)
    worktree_value = state.get("worktree_path", "")
    worktree = Path(worktree_value) if worktree_value else trial / "repo"
    acceptance_passed, _ = _acceptance(case, worktree, trial)
    halt_reason = state.get("halt_reason") or ""
    blocked_questions = [
        attempt.get("blocked_question")
        for attempt in attempts
        if attempt.get("blocked_question")
    ]
    stage = state.get("stage", "missing")
    if case.expected_outcome == "completed":
        outcome_match = stage == "done" and acceptance_passed is True
    elif case.expected_outcome == "clarification":
        outcome_match = stage == "halted" and bool(blocked_questions)
    elif case.expected_outcome == "infrastructure_halt":
        setup_failed = (
            "setup failed before agent dispatch" in halt_reason.lower()
            or "environment setup failed" in halt_reason.lower()
        )
        outcome_match = (
            stage == "halted"
            and setup_failed
            and not attempts
        )
    else:
        raise ValueError(f"unknown expected outcome: {case.expected_outcome}")
    route_match = state.get("execution_route") == case.expected_route
    changed_files: list[str] = []
    if worktree.is_dir() and state.get("base_sha"):
        diff = _run(
            ["git", "diff", "--name-only", f'{state["base_sha"]}..HEAD'],
            worktree,
            check=False,
        ).stdout
        changed_files = [line for line in diff.splitlines() if line]
    result = {
        "schema_version": 1,
        "trial_id": trial.name,
        "case_id": case.id,
        "label": label,
        "provider": provider,
        "regie_version": regie_version,
        "expected_route": case.expected_route,
        "actual_route": state.get("execution_route"),
        "route_match": route_match,
        "expected_outcome": case.expected_outcome,
        "stage": stage,
        "halt_reason": halt_reason or None,
        "blocked_questions": blocked_questions,
        "acceptance_passed": acceptance_passed,
        "passed": outcome_match and route_match,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 3),
        "changed_files": changed_files,
        **usage,
    }
    (trial / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def _print_result(result: dict[str, Any]) -> None:
    verdict = "PASS" if result["passed"] else "FAIL"
    print(
        f'{verdict:4} {result["case_id"]:26} stage={result["stage"]:8} '
        f'route={result["actual_route"] or "?":7} attempts={result["attempts"]:2} '
        f'fresh={result["fresh_tokens"]:,} cached={result["cached_tokens"]:,} '
        f'{result["elapsed_seconds"]:.1f}s'
    )


def run_benchmark(case: Case, results_root: Path, regie_root: Path, provider: str,
                  label: str, repeat: int, timeout_minutes: int) -> int:
    regie_version = _regie_version(regie_root)
    failures = 0
    for _ in range(repeat):
        trial = prepare_case(case, results_root, provider)
        exit_code, elapsed = _invoke_regie(trial, regie_root, timeout_minutes)
        result = evaluate_trial(
            case,
            trial,
            label=label,
            provider=provider,
            regie_version=regie_version,
            exit_code=exit_code,
            elapsed=elapsed,
        )
        _print_result(result)
        print(f"      artifacts: {trial}")
        failures += not result["passed"]
    return 1 if failures else 0


def smoke(cases: dict[str, Case], results_root: Path) -> int:
    failures = 0
    for case in cases.values():
        trial = prepare_case(case, results_root, "codex")
        repo = trial / "repo"
        outputs = []
        case_passed = True
        for command in (["npm", "test"], ["npm", "run", "lint"], ["npm", "run", "build"]):
            result = _run(command, repo, check=False)
            outputs.append(result.stdout)
            case_passed = case_passed and result.returncode == 0
        (trial / "smoke.log").write_text("\n".join(outputs))
        failures += not case_passed
        verdict = "PASS" if case_passed else "FAIL"
        print(f"{verdict:4} {case.id}")
    return 1 if failures else 0


def _results(results_root: Path, label: str | None = None) -> list[dict[str, Any]]:
    records = []
    for path in sorted(results_root.glob("*/result.json")):
        record = json.loads(path.read_text())
        if label is None or record.get("label") == label:
            records.append(record)
    return records


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"trials": 0}
    return {
        "trials": len(records),
        "pass_rate": sum(record["passed"] for record in records) / len(records),
        "route_accuracy": sum(record["route_match"] for record in records) / len(records),
        "median_seconds": statistics.median(record["elapsed_seconds"] for record in records),
        "median_attempts": statistics.median(record["attempts"] for record in records),
        "median_fresh_tokens": statistics.median(record["fresh_tokens"] for record in records),
        "median_cached_tokens": statistics.median(record["cached_tokens"] for record in records),
        "median_cost_usd": statistics.median(record["cost_usd"] for record in records),
    }


def report(results_root: Path, baseline: str | None, candidate: str | None) -> int:
    labels = [label for label in (baseline, candidate) if label]
    if not labels:
        labels = sorted({record.get("label", "") for record in _results(results_root)})
    if not labels:
        print("No benchmark results found.")
        return 1
    summaries: dict[str, dict[str, Any]] = {}
    for label in labels:
        records = _results(results_root, label)
        summary = _summary(records)
        summaries[label] = summary
        if not summary["trials"]:
            print(f"{label}: no trials")
            continue
        print(
            f'{label}: {summary["trials"]} trials · '
            f'{summary["pass_rate"]:.0%} pass · {summary["route_accuracy"]:.0%} route · '
            f'{summary["median_seconds"]:.1f}s · {summary["median_fresh_tokens"]:,.0f} fresh · '
            f'${summary["median_cost_usd"]:.4f}'
        )
        for record in records:
            _print_result(record)
    if baseline and candidate:
        before = summaries.get(baseline, {"trials": 0})
        after = summaries.get(candidate, {"trials": 0})
        if before["trials"] and after["trials"]:
            print(
                f"delta {candidate} − {baseline}: "
                f'{after["pass_rate"] - before["pass_rate"]:+.0%} pass · '
                f'{after["route_accuracy"] - before["route_accuracy"]:+.0%} route · '
                f'{after["median_seconds"] - before["median_seconds"]:+.1f}s · '
                f'{after["median_fresh_tokens"] - before["median_fresh_tokens"]:+,.0f} fresh · '
                f'${after["median_cost_usd"] - before["median_cost_usd"]:+.4f}'
            )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repeatable Régie benchmarks")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="list benchmark cases")
    prepare = subparsers.add_parser("prepare", help="prepare a clean trial without running Régie")
    prepare.add_argument("case")
    prepare.add_argument("--provider", choices=("codex", "claude"), default="codex")
    run = subparsers.add_parser("run", help="run and evaluate one benchmark case")
    run.add_argument("case")
    run.add_argument("--regie-root", type=Path, default=ROOT.parent / "regie")
    run.add_argument("--provider", choices=("codex", "claude"), default="codex")
    run.add_argument("--label", default="working-tree")
    run.add_argument("--repeat", type=int, default=1)
    run.add_argument("--timeout-minutes", type=int, default=45)
    subparsers.add_parser("smoke", help="validate every fixture without calling a model")
    report_parser = subparsers.add_parser("report", help="summarize or compare result labels")
    report_parser.add_argument("--baseline")
    report_parser.add_argument("--candidate")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cases = load_cases()
    if args.command == "list":
        for case in cases.values():
            print(
                f"{case.id:26} {case.expected_route:7} {case.expected_outcome:19} "
                f"{case.description}"
            )
        return 0
    if args.command == "prepare":
        if args.case not in cases:
            raise SystemExit(f"unknown case: {args.case}")
        print(prepare_case(cases[args.case], args.results, args.provider))
        return 0
    if args.command == "smoke":
        return smoke(cases, args.results)
    if args.command == "report":
        return report(args.results, args.baseline, args.candidate)
    if args.case not in cases:
        raise SystemExit(f"unknown case: {args.case}")
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1")
    return run_benchmark(
        cases[args.case],
        args.results,
        args.regie_root.resolve(),
        args.provider,
        args.label,
        args.repeat,
        args.timeout_minutes,
    )


if __name__ == "__main__":
    sys.exit(main())
