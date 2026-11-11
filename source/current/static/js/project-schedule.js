function newTaskId() {
  return typeof crypto?.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function taskRows(form) {
  return [...form.querySelectorAll("[data-task]")];
}

function projectTemplate(form) {
  try {
    return JSON.parse(form.dataset.scheduleTemplates || "[]");
  } catch {
    return [];
  }
}

function setStatus(form, message) {
  const target = form.querySelector("[data-schedule-status]");
  if (target) target.textContent = message;
}

function updateMeta(form) {
  const meta = form.querySelector("[data-schedule-meta]");
  if (!meta) return;
  const total = taskRows(form).length;
  const done = taskRows(form).filter((row) => row.querySelector('[data-task-field="done"]')?.checked).length;
  const dates = [...form.querySelectorAll("[data-schedule-field]")].filter((input) => input.value).length;
  meta.textContent = `${done}/${total} tarefas · ${dates ? `${dates} ${dates === 1 ? "data definida" : "datas definidas"}` : "sem datas definidas"}`;
}

function removeEmptyMessage(form) {
  form.querySelector("[data-empty-task-list]")?.remove();
}

function showEmptyMessage(form) {
  const list = form.querySelector("[data-task-list]");
  if (list && !taskRows(form).length && !list.querySelector("[data-empty-task-list]")) {
    const message = document.createElement("p");
    message.className = "field-hint";
    message.dataset.emptyTaskList = "";
    message.textContent = "Ainda não há tarefas. Use o roteiro sugerido ou adicione uma tarefa própria.";
    list.append(message);
  }
}

function input(type, value, attributes = {}) {
  const element = document.createElement("input");
  element.type = type;
  if (type === "checkbox") element.checked = Boolean(value);
  else element.value = value || "";
  Object.entries(attributes).forEach(([key, attributeValue]) => {
    if (attributeValue !== undefined && attributeValue !== null) element.setAttribute(key, attributeValue);
  });
  return element;
}

function createTaskRow(form, task, index) {
  removeEmptyMessage(form);
  const row = document.createElement("div");
  row.className = "task-row";
  row.dataset.task = "";
  row.dataset.taskId = task.id || newTaskId();
  row.dataset.taskTemplateKey = task.template_key || "";
  row.dataset.taskStage = Number.isInteger(task.stage) ? String(task.stage) : "";

  const doneLabel = document.createElement("label");
  doneLabel.className = "task-row-done";
  doneLabel.title = "Marcar tarefa como concluída";
  doneLabel.append(input("checkbox", task.done, {
    "data-task-field": "done",
    "aria-label": `Concluir tarefa ${index + 1}`,
  }));
  const title = input("text", task.title, {
    class: "task-row-title",
    maxlength: "180",
    "data-task-field": "title",
    placeholder: "Tarefa",
    "aria-label": `Nome da tarefa ${index + 1}`,
  });
  const dateLabel = document.createElement("label");
  dateLabel.className = "task-row-date";
  dateLabel.append(input("date", task.date, {
    "data-task-field": "date",
    "aria-label": `Data da tarefa ${index + 1}`,
  }));
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "text-button danger";
  remove.dataset.removeTask = "";
  remove.textContent = "Remover";

  row.append(doneLabel, title, dateLabel, remove);
  form.querySelector("[data-task-list]")?.append(row);
  return row;
}

export function collectSchedule(form) {
  const schedule = Object.fromEntries(
    [...form.querySelectorAll("[data-schedule-field]")].map((element) => [element.dataset.scheduleField, element.value]),
  );
  schedule.tasks = taskRows(form).map((task) => ({
    id: task.dataset.taskId || newTaskId(),
    title: task.querySelector('[data-task-field="title"]')?.value || "",
    date: task.querySelector('[data-task-field="date"]')?.value || "",
    done: Boolean(task.querySelector('[data-task-field="done"]')?.checked),
    stage: task.dataset.taskStage === "" ? null : Number(task.dataset.taskStage),
    template_key: task.dataset.taskTemplateKey || "",
  }));
  return schedule;
}

export function initScheduleEditor(form, onStructuralChange) {
  if (!form) return;
  updateMeta(form);
  form.addEventListener("input", (event) => {
    if (event.target.matches("[data-schedule-field], [data-task-field]")) updateMeta(form);
  });
  form.addEventListener("change", (event) => {
    if (event.target.matches("[data-schedule-field], [data-task-field]")) updateMeta(form);
  });
  form.addEventListener("click", (event) => {
    if (event.target.closest("[data-add-task]")) {
      createTaskRow(form, { id: newTaskId(), title: "", date: "", done: false }, taskRows(form).length);
      setStatus(form, "Tarefa adicionada.");
      updateMeta(form);
      onStructuralChange();
      form.querySelector("[data-task]:last-of-type [data-task-field=title]")?.focus();
      return;
    }
    if (event.target.closest("[data-add-suggested-tasks]")) {
      const existingKeys = new Set(taskRows(form).map((row) => row.dataset.taskTemplateKey).filter(Boolean));
      const existingTitles = new Set(taskRows(form).map((row) => row.querySelector('[data-task-field="title"]')?.value.trim()).filter(Boolean));
      const template = projectTemplate(form);
      let added = 0;
      template.forEach(([key, title], stage) => {
        if (existingKeys.has(key) || existingTitles.has(title)) return;
        createTaskRow(form, { id: newTaskId(), title, date: "", done: false, stage, template_key: key }, taskRows(form).length);
        added += 1;
      });
      setStatus(form, added ? `${added} tarefas do roteiro foram adicionadas.` : "O roteiro já está adicionado.");
      updateMeta(form);
      if (added) onStructuralChange();
      return;
    }
    if (event.target.closest("[data-remove-task]")) {
      event.target.closest("[data-task]")?.remove();
      showEmptyMessage(form);
      setStatus(form, "Tarefa removida.");
      updateMeta(form);
      onStructuralChange();
    }
  });
}
