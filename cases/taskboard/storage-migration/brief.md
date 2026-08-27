# Version Taskboard persistence

Introduce a data migration from Taskboard's legacy raw-array localStorage format
to a versioned envelope: `{ "version": 2, "tasks": [...] }`.

Existing users' raw arrays must load without losing tasks and must be written in
version 2 format on the next save. Version 2 data must round-trip. Malformed data,
non-array `tasks`, and unknown future versions must fail safely to an empty list.
Keep the storage key unchanged and add migration-focused tests. This is a local
data migration only; do not add a backend or dependency.
