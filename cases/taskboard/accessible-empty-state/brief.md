# Make the empty state accessible

When the selected filter contains no tasks, announce that state to assistive
technology without stealing focus. Keep it visually understated and use the copy
“No tasks match this view.” The announcement should work when filtering changes,
not only on initial page load.

Add a focused rendering test. Do not introduce a UI framework or dependency.
