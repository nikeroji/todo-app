"use strict";

const API_URL = "/api/tasks";
const byId = (id) => document.getElementById(id);

const form = byId("task-form");
const taskList = byId("task-list");
const taskTemplate = byId("task-template");

let tasks = [];
let busy = false;
let loaded = false;


// Сообщения и блокировка повторных действий во время запроса.
function showMessage(text, type = "success") {
  const message = byId("status-message");
  message.textContent = text;
  message.className = `alert alert-${type}`;
  message.hidden = !text;
}

function setBusy(value) {
  busy = value;

  document.querySelectorAll(
    "#task-form input, #task-form textarea, #task-form button, " +
    "#task-list button, #refresh-tasks"
  ).forEach((element) => {
    element.disabled = value;
  });
}

async function runAction(action) {
  if (busy) return;

  setBusy(true);
  showMessage("");

  try {
    await action();
  } catch (error) {
    console.error(error);
    showMessage(error.message, "danger");

    if (!loaded) {
      taskList.textContent = "Не удалось загрузить список задач.";
    }
  } finally {
    setBusy(false);
  }
}


// Отправка HTTP-запросов и обработка ответов API.
async function apiRequest(path = "", method = "GET", data) {
  const options = {
    method,
    headers: { Accept: "application/json" },
  };

  if (data !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(data);
  }

  let response;

  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error(
      "Не удалось связаться с сервером. Повторите попытку позже."
    );
  }

  if (response.status === 204) {
    return null;
  }

  const result = await response.json();

  if (!response.ok) {
    const detail = result.detail;

    if (Array.isArray(detail)) {
      throw new Error(
        detail.map((item) => item.msg).join("; ")
      );
    }

    throw new Error(
      typeof detail === "string"
        ? detail
        : "Не удалось выполнить операцию."
    );
  }

  return result;
}


// Подготовка дат для отображения.
const dateTimeFormatter = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "Europe/Moscow",
});

function formatCreatedAt(value) {
  if (!value) return "Дата не сохранена";

  return `${dateTimeFormatter.format(new Date(value))} МСК`;
}

function formatDueDate(value) {
  return value ? value.split("-").reverse().join(".") : "Не указан";
}


// Формирование карточек и обновление счётчиков.
function renderTasks() {
  const completed = tasks.filter((task) => task.is_completed).length;

  byId("total-count").textContent = tasks.length;
  byId("active-count").textContent = tasks.length - completed;
  byId("completed-count").textContent = completed;
  byId("empty-state").hidden = tasks.length !== 0;

  const fragment = document.createDocumentFragment();

  for (const task of tasks) {
    const card = taskTemplate.content.firstElementChild.cloneNode(true);
    const field = (name) => card.querySelector(`[data-field="${name}"]`);

    card.dataset.id = task.id;

    field("id").textContent = `#${task.id}`;
    field("title").textContent = task.title;
    field("description").textContent = task.description ?? "";
    field("description").hidden = !task.description;

    field("title").classList.toggle(
      "text-decoration-line-through",
      task.is_completed
    );

    field("status").textContent = task.is_completed
      ? "Выполнена"
      : "В работе";

    field("status").className = task.is_completed
      ? "badge bg-green-lt text-green"
      : "badge bg-blue-lt text-blue";

    field("created-at").textContent = formatCreatedAt(task.created_at);
    field("due-date").textContent = formatDueDate(task.due_date);

    const toggleButton = card.querySelector('[data-action="toggle"]');

    toggleButton.textContent = task.is_completed
      ? "Вернуть в работу"
      : "Завершить";

    fragment.append(card);
  }

  taskList.replaceChildren(fragment);
}


// Переключение формы между созданием и редактированием.
function resetForm() {
  form.reset();
  byId("task-id").value = "";
  byId("form-title").textContent = "Новая задача";
  byId("save-task").textContent = "Добавить задачу";
  byId("cancel-edit").hidden = true;
}

function editTask(task) {
  byId("task-id").value = task.id;
  byId("title").value = task.title;
  byId("description").value = task.description ?? "";
  byId("due-date").value = task.due_date ?? "";

  byId("form-title").textContent = `Редактирование задачи #${task.id}`;
  byId("save-task").textContent = "Сохранить изменения";
  byId("cancel-edit").hidden = false;
  byId("title").focus();
}


// Загрузка актуального списка из PostgreSQL через API.
async function loadTasks() {
  const result = await apiRequest();

  if (!Array.isArray(result)) {
    throw new Error("Получен некорректный список задач.");
  }

  tasks = result;
  loaded = true;

  const editingId = byId("task-id").value;

  if (editingId && !tasks.some((task) => String(task.id) === editingId)) {
    resetForm();
  }

  renderTasks();
}


// Создание или сохранение отредактированной задачи.
form.addEventListener("submit", (event) => {
  event.preventDefault();

  runAction(async () => {
    const id = byId("task-id").value;
    const title = byId("title").value.trim();

    if (!title) {
      throw new Error("Введите название задачи.");
    }

    const data = {
      title,
      description: byId("description").value.trim() || null,
      due_date: byId("due-date").value || null,
    };

    if (id) {
      const current = tasks.find((task) => String(task.id) === id);

      if (!current) {
        throw new Error("Задача не найдена. Обновите список.");
      }

      data.is_completed = current.is_completed;
    }

    const saved = await apiRequest(
      id ? `/${id}` : "",
      id ? "PUT" : "POST",
      data
    );

    tasks = id
      ? tasks.map((task) => task.id === saved.id ? saved : task)
      : [saved, ...tasks];

    renderTasks();
    resetForm();

    showMessage(id ? "Изменения сохранены." : "Задача добавлена.");
  });
});


// Обработка кнопок в карточках задач.
taskList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");

  if (!button || busy) return;

  const id = Number(button.closest("article").dataset.id);
  const task = tasks.find((item) => item.id === id);

  if (!task) return;

  const action = button.dataset.action;

  if (action === "edit") {
    showMessage("");
    editTask(task);
    return;
  }

  runAction(async () => {
    if (action === "toggle") {
      const updated = await apiRequest(`/${id}`, "PATCH", {
        is_completed: !task.is_completed,
      });

      tasks = tasks.map((item) => item.id === id ? updated : item);
      renderTasks();
      showMessage("Статус задачи изменён.");
    }

    if (action === "delete") {
      await apiRequest(`/${id}`, "DELETE");

      tasks = tasks.filter((item) => item.id !== id);

      if (byId("task-id").value === String(id)) {
        resetForm();
      }

      renderTasks();
      showMessage("Задача удалена.");
    }
  });
});


// Дополнительные кнопки и первоначальная загрузка.
byId("cancel-edit").addEventListener("click", () => {
  resetForm();
  showMessage("");
});

byId("refresh-tasks").addEventListener("click", () => {
  runAction(loadTasks);
});

runAction(loadTasks);