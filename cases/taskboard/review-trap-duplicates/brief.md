# Prevent duplicate task titles

Do not add a task when its title duplicates an existing task after trimming,
case-insensitive comparison, and Unicode normalization. Preserve the trimmed
spelling of the first task rather than replacing it. A rejected duplicate must
return the original list unchanged.

Old localStorage data can contain malformed entries whose title is absent or not
a string. Those entries must not make adding a new task crash. Add focused tests
covering the matching rules and malformed legacy data. Do not change persistence
format or add a dependency.

