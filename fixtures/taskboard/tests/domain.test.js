import assert from "node:assert/strict";
import test from "node:test";

import { loadTasks, reduceTasks, saveTasks, visibleTasks } from "../src/domain.js";

const task = (id, completed = false) => ({ id, title: id, completed, createdAt: "now" });

test("adds, toggles, and removes tasks without mutating prior state", () => {
  const original = [];
  const added = reduceTasks(original, {
    type: "add",
    title: "Ship benchmark",
    id: "T1",
    createdAt: "2026-08-27T00:00:00Z",
  });
  assert.deepEqual(original, []);
  assert.equal(added[0].title, "Ship benchmark");
  const toggled = reduceTasks(added, { type: "toggle", id: "T1" });
  assert.equal(toggled[0].completed, true);
  assert.deepEqual(reduceTasks(toggled, { type: "remove", id: "T1" }), []);
});

test("filters active and completed tasks", () => {
  const tasks = [task("active"), task("done", true)];
  assert.deepEqual(visibleTasks(tasks, "active").map(({ id }) => id), ["active"]);
  assert.deepEqual(visibleTasks(tasks, "completed").map(({ id }) => id), ["done"]);
  assert.equal(visibleTasks(tasks, "all").length, 2);
});

test("round-trips persistence and tolerates corrupt data", () => {
  const tasks = [task("one")];
  assert.deepEqual(loadTasks(saveTasks(tasks)), tasks);
  assert.deepEqual(loadTasks("not-json"), []);
  assert.deepEqual(loadTasks('{"unexpected":true}'), []);
});
