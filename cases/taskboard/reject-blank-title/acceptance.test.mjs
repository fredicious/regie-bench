import assert from "node:assert/strict";
import test from "node:test";
import path from "node:path";
import { pathToFileURL } from "node:url";

const target = process.env.TARGET_REPO;
const domain = await import(pathToFileURL(path.join(target, "src/domain.js")));

test("blank titles are rejected and meaningful titles are trimmed", () => {
  const original = [];
  assert.strictEqual(domain.reduceTasks(original, { type: "add", title: " \t\n " }), original);
  const tasks = domain.reduceTasks(original, {
    type: "add",
    title: "  Ship the benchmark  ",
    id: "T1",
    createdAt: "2026-08-27T00:00:00Z",
  });
  assert.equal(tasks.length, 1);
  assert.equal(tasks[0].title, "Ship the benchmark");
});
