import assert from "node:assert/strict";
import test from "node:test";
import path from "node:path";
import { pathToFileURL } from "node:url";

const target = process.env.TARGET_REPO;
const domain = await import(pathToFileURL(path.join(target, "src/domain.js")));
const view = await import(pathToFileURL(path.join(target, "src/view.js")));

test("priority is created, persisted, and exposed as text", () => {
  const normal = domain.reduceTasks([], {
    type: "add",
    title: "Normal task",
    id: "N",
    createdAt: "now",
  })[0];
  const high = domain.reduceTasks([], {
    type: "add",
    title: "Urgent task",
    priority: "high",
    id: "H",
    createdAt: "now",
  })[0];
  assert.equal(normal.priority, "normal");
  assert.equal(high.priority, "high");
  assert.deepEqual(domain.loadTasks(domain.saveTasks([high])), [high]);
  assert.match(view.renderTaskList([high]), /high priority/i);
  assert.match(view.renderTaskList([{ ...normal, priority: undefined }]), /normal/i);
});
