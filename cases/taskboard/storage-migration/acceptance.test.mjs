import assert from "node:assert/strict";
import test from "node:test";
import path from "node:path";
import { pathToFileURL } from "node:url";

const target = process.env.TARGET_REPO;
const domain = await import(pathToFileURL(path.join(target, "src/domain.js")));
const tasks = [{ id: "T1", title: "Keep me", completed: false, createdAt: "now" }];

test("legacy and version 2 data load while invalid versions fail closed", () => {
  assert.deepEqual(domain.loadTasks(JSON.stringify(tasks)), tasks);
  assert.deepEqual(domain.loadTasks(JSON.stringify({ version: 2, tasks })), tasks);
  assert.deepEqual(domain.loadTasks(JSON.stringify({ version: 2, tasks: {} })), []);
  assert.deepEqual(domain.loadTasks(JSON.stringify({ version: 99, tasks })), []);
  assert.deepEqual(JSON.parse(domain.saveTasks(tasks)), { version: 2, tasks });
});
