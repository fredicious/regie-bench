import { loadTasks, reduceTasks, saveTasks, visibleTasks } from "./domain.js";
import { renderTaskList } from "./view.js";

const STORAGE_KEY = "regie-bench-taskboard";
const form = document.querySelector("#new-task");
const titleInput = document.querySelector("#task-title");
const list = document.querySelector("#task-list");
const filters = [...document.querySelectorAll("[data-filter]")];

let tasks = loadTasks(localStorage.getItem(STORAGE_KEY));
let activeFilter = "all";

function render() {
  list.innerHTML = renderTaskList(visibleTasks(tasks, activeFilter));
  localStorage.setItem(STORAGE_KEY, saveTasks(tasks));
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  tasks = reduceTasks(tasks, { type: "add", title: titleInput.value });
  titleInput.value = "";
  titleInput.focus();
  render();
});

list.addEventListener("click", (event) => {
  const action = event.target.dataset.action;
  const item = event.target.closest("[data-task-id]");
  if (!action || !item) return;
  tasks = reduceTasks(tasks, { type: action, id: item.dataset.taskId });
  render();
});

for (const filter of filters) {
  filter.addEventListener("click", () => {
    activeFilter = filter.dataset.filter;
    for (const candidate of filters) {
      candidate.setAttribute("aria-pressed", String(candidate === filter));
    }
    render();
  });
}

render();
