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

async function initializeApp(raw, label) {
  const writes = [];
  const listeners = {};
  const form = {
    addEventListener(type, listener) {
      listeners[`form:${type}`] = listener;
    },
  };
  const titleInput = {
    value: "",
    focus() {},
  };
  const list = {
    innerHTML: "",
    addEventListener(type, listener) {
      listeners[`list:${type}`] = listener;
    },
  };

  globalThis.localStorage = {
    getItem() {
      return raw;
    },
    setItem(key, value) {
      writes.push({ key, value });
    },
  };
  globalThis.document = {
    querySelector(selector) {
      return {
        "#new-task": form,
        "#task-title": titleInput,
        "#task-list": list,
      }[selector];
    },
    querySelectorAll() {
      return [];
    },
  };

  const appUrl = pathToFileURL(path.join(target, "src/app.js"));
  appUrl.searchParams.set("acceptance", label);
  await import(appUrl.href);
  return { listeners, titleInput, writes };
}

test("startup preserves future data until an explicit mutation", async () => {
  const futureRaw = JSON.stringify({ version: 99, tasks });
  const future = await initializeApp(futureRaw, "future");
  assert.deepEqual(future.writes, []);

  future.titleInput.value = "New task";
  future.listeners["form:submit"]({ preventDefault() {} });
  assert.equal(future.writes.length, 1);
  const saved = JSON.parse(future.writes[0].value);
  assert.equal(saved.version, 2);
  assert.deepEqual(saved.tasks.map((task) => task.title), ["New task"]);

  const legacyRaw = JSON.stringify(tasks);
  const legacy = await initializeApp(legacyRaw, "legacy");
  assert.equal(legacy.writes.length, 1);
  assert.deepEqual(JSON.parse(legacy.writes[0].value), { version: 2, tasks });
});
