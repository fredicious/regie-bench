export function reduceTasks(tasks, action) {
  switch (action.type) {
    case "add": {
      if (!action.title) return tasks;
      return [
        ...tasks,
        {
          id: action.id ?? crypto.randomUUID(),
          title: action.title,
          completed: false,
          createdAt: action.createdAt ?? new Date().toISOString(),
        },
      ];
    }
    case "toggle":
      return tasks.map((task) =>
        task.id === action.id ? { ...task, completed: !task.completed } : task,
      );
    case "remove":
      return tasks.filter((task) => task.id !== action.id);
    default:
      return tasks;
  }
}

export function visibleTasks(tasks, filter) {
  if (filter === "active") return tasks.filter((task) => !task.completed);
  if (filter === "completed") return tasks.filter((task) => task.completed);
  return tasks;
}

export function loadTasks(raw) {
  if (!raw) return [];
  try {
    const value = JSON.parse(raw);
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function saveTasks(tasks) {
  return JSON.stringify(tasks);
}
