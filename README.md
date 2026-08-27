# Régie Bench

Régie Bench is a controlled product-engineering benchmark for
[Régie](https://github.com/fredicious/regie). It measures whether orchestration
changes improve outcomes across repeatable briefs without creating real pull
requests.

The first fixture is **Taskboard**, a deliberately small browser TODO app with a
pure JavaScript domain layer, accessible HTML, public tests, deterministic build
and lint commands, and no runtime dependencies. Its cases exercise different
orchestration decisions rather than six variations of the same coding task:

- a bounded bug fix;
- a small product feature;
- an accessible UI change;
- a deliberately ambiguous request that should ask a question;
- a persistence migration that should earn planning;
- a duplicate-title edge case designed to test whether review catches a subtle
  Unicode and malformed-data defect;
- an unavailable setup command that should halt before spending model tokens.

## Quick start

Requirements: macOS/Linux, Python 3.12+, `uv`, Node.js, Git, and a working Régie
provider.

```bash
uv sync
uv run regie-bench list
uv run regie-bench smoke
uv run regie-bench run reject-blank-title --regie-root ../regie \
  --provider codex --label baseline
```

Run a case at least three times when comparing orchestration behavior:

```bash
uv run regie-bench run reject-blank-title --regie-root ../regie \
  --provider codex --label before --repeat 3
# change Régie
uv run regie-bench run reject-blank-title --regie-root ../regie \
  --provider codex --label after --repeat 3
uv run regie-bench report --baseline before --candidate after
```

Trials are written under `results/` and ignored by Git. Every trial contains the
clean target repository, a local bare origin, an isolated `REGIE_HOME`, Régie's
combined log, hidden-acceptance output when applicable, and a machine-readable
`result.json`. Results include a stage breakdown for each agent call, setup, and
mechanical gate so orchestration overhead can be attributed instead of guessed.

Régie's target config sets `workflow.submit_pr = false`. This still performs
implementation, mechanical gates, review, and finalization, but finishes locally
without pushing a benchmark branch or opening a PR.

## What counts as a pass

A completed case must finish at `done`, choose the expected direct/planned route,
and pass its hidden acceptance test. Clarification cases must halt with a concrete
agent question. Infrastructure cases must halt before an agent attempt. Reports
also retain elapsed time, attempts, provider/model, fresh and cached tokens, cost,
changed files, and halt details.

The public fixture tests are visible to agents. Acceptance evaluators live beside
the briefs and are invoked by the harness from outside the target worktree; they
are not included in the agent's repository or task packet.

## Guarding against benchmark overfitting

Taskboard is the fast regression track, not the definition of success. New Régie
behavior should not be accepted solely because this fixture improves. Planned
next fixtures are a Python CLI and a small HTTP API. Some future cases should be
held back from day-to-day tuning, and briefs should periodically gain paraphrased
variants. Record the Régie commit, model/provider, and repeated runs whenever
publishing a comparison.

See [Methodology](docs/METHODOLOGY.md) for the experiment protocol and the limits
on what a benchmark result can establish.
