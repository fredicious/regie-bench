# Benchmark methodology

## Purpose

Régie Bench detects orchestration improvements and regressions under controlled
conditions. It is not a leaderboard for foundation models and it does not prove
that a workflow generalizes to an arbitrary production repository.

## Experimental unit

One trial is one immutable fixture commit, one brief, one Régie revision, and one
provider configuration. The harness creates a fresh repository, local bare
origin, worktree namespace, and `REGIE_HOME` for every trial. No state is shared
between repetitions.

Record these variables whenever comparing results:

- benchmark revision and case identifier;
- Régie revision, including whether its worktree was dirty;
- provider and every model actually attempted;
- elapsed time, attempts, fresh/cached tokens, and cost;
- final stage, route, halt reason, changed files, and acceptance result.

## Comparison protocol

1. Run the model-free smoke suite.
2. Choose cases before inspecting candidate results.
3. Run the baseline and candidate at least three times per case.
4. Keep provider settings unchanged across both labels.
5. Compare pass rate and route accuracy before efficiency metrics.
6. Treat token or latency improvements as wins only when quality does not fall.
7. Inspect individual trial artifacts; an aggregate can hide repeated failure on
   one task class.

Provider services and model aliases can change independently of Régie. A result
from different dates is weaker evidence than an interleaved A/B run using pinned
model identifiers.

## Benchmark matrix

| Case | Stack | Track | Route | Expected outcome | Primary signal |
| --- | --- | --- | --- | --- | --- |
| `reject-blank-title` | Browser JS | development | direct | completed | narrow bug-fix cost |
| `add-priority` | Browser JS | development | direct | completed | cross-layer feature |
| `accessible-empty-state` | Browser JS | development | direct | completed | semantic UI behavior |
| `clarify-multiselect` | Browser JS | development | direct | clarification | intake ambiguity |
| `storage-migration` | Browser JS | development | planned | completed | risk planning and review convergence |
| `review-trap-duplicates` | Browser JS | development | direct | completed | adversarial review value |
| `setup-unavailable` | Browser JS | development | direct | infrastructure halt | zero-token preflight |
| `strict-quantity` | Python CLI | holdout | direct | completed | cross-language type boundary |

The matrix is intentionally asymmetric: Taskboard is the daily development
track, while `strict-quantity` is evaluated only after a candidate policy is
chosen. A holdout failure invalidates the candidate claim; it does not authorize
tuning that candidate against the holdout in the same comparison cycle.

## Acceptance layers

Public tests express established repository behavior and are available to the
agent. Case acceptance evaluators are outside the target worktree and verify the
new behavior after Régie stops. A completed case passes only when Régie reaches
`done`, selects the expected route, and passes hidden acceptance.

Clarification and infrastructure cases intentionally do not require a code patch.
They pass only when Régie stops for the correct reason. This prevents “eventually
wrote some code” from being mistaken for sound orchestration.

## Anti-overfitting policy

- Taskboard is a smoke track, not the global score.
- Do not weaken an evaluator because a particular run chose a different patch.
  Change it only when the product brief was genuinely ambiguous or incorrect.
- Keep future cases out of the daily tuning loop as holdouts.
- Add paraphrases and behavioral mutations rather than cloning existing cases.
- Require representative gains across UI, CLI, and API fixtures before claiming a
  general Régie improvement.
- Periodically validate against an unfamiliar real repository.
