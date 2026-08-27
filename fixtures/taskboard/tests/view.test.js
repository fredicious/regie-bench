import assert from "node:assert/strict";
import test from "node:test";

import { renderTaskList } from "../src/view.js";

test("renders tasks and escapes user-authored titles", () => {
  const html = renderTaskList([
    { id: "T1", title: "<script>alert(1)</script>", completed: false },
  ]);
  assert.match(html, /data-task-id="T1"/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});

test("renders a stable empty state", () => {
  assert.match(renderTaskList([]), /No tasks here\./);
});
