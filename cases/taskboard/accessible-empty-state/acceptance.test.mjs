import assert from "node:assert/strict";
import test from "node:test";
import path from "node:path";
import { pathToFileURL } from "node:url";

const target = process.env.TARGET_REPO;
const view = await import(pathToFileURL(path.join(target, "src/view.js")));

test("empty output is a polite status without focus manipulation", () => {
  const html = view.renderTaskList([]);
  assert.match(html, /No tasks match this view\./);
  assert.match(html, /role=["']status["']/);
  assert.match(html, /aria-live=["']polite["']/);
  assert.doesNotMatch(html, /tabindex/i);
  assert.doesNotMatch(html, /autofocus/i);
});
