# Add task priority

Let people choose **Normal** or **High** priority when adding a task. Normal is
the default. The chosen value must be stored on the task as `priority`, survive
the existing save/load round trip, and be visible in the task list. High priority
must have an explicit text label rather than relying on color alone.

Existing saved tasks without a priority must continue to render as Normal. Add
focused tests for the domain behavior and rendered output.
