import assert from "node:assert/strict";
import test from "node:test";
import path from "node:path";
import { pathToFileURL } from "node:url";

const target = process.env.TARGET_REPO;
const domain = await import(pathToFileURL(path.join(target, "src/domain.js")));

const existing = {
  id: "T1",
  title: "Café",
  completed: false,
  createdAt: "2026-08-27T00:00:00Z",
};

test("duplicate comparison normalizes whitespace, case, and Unicode", () => {
  const original = [existing];
  const duplicate = domain.reduceTasks(original, {
    type: "add",
    title: "  CAFE\u0301  ",
    id: "T2",
    createdAt: "2026-08-27T00:00:01Z",
  });
  assert.strictEqual(duplicate, original);
  assert.equal(duplicate[0].title, "Café");
});

test("malformed legacy titles do not crash duplicate detection", () => {
  const original = [
    { id: "broken-1", completed: false },
    { id: "broken-2", title: null, completed: false },
    { id: "broken-3", title: 42, completed: false },
  ];
  const result = domain.reduceTasks(original, {
    type: "add",
    title: "Valid task",
    id: "T3",
    createdAt: "2026-08-27T00:00:02Z",
  });
  assert.equal(result.length, 4);
  assert.equal(result.at(-1).title, "Valid task");
});
