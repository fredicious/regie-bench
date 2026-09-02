# Version Taskboard persistence

Introduce a data migration from Taskboard's legacy raw-array localStorage format
to a versioned envelope: `{ "version": 2, "tasks": [...] }`.

Existing users' raw arrays must load without losing tasks and must be written in
version 2 format on the next save. Version 2 data must round-trip. Malformed data,
non-array `tasks`, and unknown future versions must fail safely to an empty list.
Keep the storage key unchanged and add migration-focused tests. This is a local
data migration only; do not add a backend or dependency.

“Fail safely” includes persistence behavior: initialization may display an empty
list for malformed or unknown-future data, but it must not overwrite that raw
value merely by rendering. After an explicit user mutation, normal persistence
may replace it with a valid version 2 envelope containing the user's new state.
Legacy arrays should still be rewritten to version 2 during the existing startup
save path.

Compatibility with an older application bundle after version 2 has been written
is outside this change; do not add backup keys, dual-write formats, deployment
machinery, or a generalized migration framework. `saveTasks` is called with task
arrays—validation of arbitrary programmatic non-array arguments is also outside
scope.
