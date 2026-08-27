function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function renderTaskList(tasks) {
  if (tasks.length === 0) {
    return '<p class="empty-state">No tasks here.</p>';
  }
  return `<ul class="task-list">${tasks
    .map(
      (task) => `<li data-task-id="${escapeHtml(task.id)}">
        <label>
          <input type="checkbox" data-action="toggle" ${task.completed ? "checked" : ""}>
          <span>${escapeHtml(task.title)}</span>
        </label>
        <button type="button" data-action="remove" aria-label="Remove ${escapeHtml(task.title)}">
          Remove
        </button>
      </li>`,
    )
    .join("")}</ul>`;
}
