# Reject blank task titles

Taskboard currently accepts a title made only of whitespace. Treat that exactly
like an empty title: submitting it must leave the task list unchanged. Trim
leading and trailing whitespace from valid titles before storing them.

Add focused regression tests. Do not otherwise change the interface or task data
format.
