import { readdir } from "node:fs/promises";
import { spawnSync } from "node:child_process";

const directories = ["src", "tests", "scripts"];
const files = [];
for (const directory of directories) {
  for (const name of await readdir(directory)) {
    if (name.endsWith(".js") || name.endsWith(".mjs")) files.push(`${directory}/${name}`);
  }
}
const result = spawnSync(process.execPath, ["--check", ...files], { stdio: "inherit" });
process.exitCode = result.status ?? 1;
