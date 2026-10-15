
import { api, el, getMe, renderHeader } from "/js/common.js";
import { createComposer } from "/js/composer.js";

const form = document.getElementById("ask-form");
const error = form.querySelector(".form-error");
const composer = createComposer({ label: "Your question", placeholder: "What is the problem, and what have you tried?", rows: 8 });
document.getElementById("ask-composer").append(composer.element);

async function start() {
  renderHeader();
  const [me, data] = await Promise.all([getMe(), api("GET", "/api/questions?limit=1")]);
  if (!me) return location.replace("/login.html?next=/ask.html");
  const topic = new URLSearchParams(location.search).get("topic");
  form.elements.topic.append(...data.topics.map((t) => el("option", { value: t.key, selected: t.key === topic }, t.name)));
  form.elements.title.focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.textContent = "";
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const q = await api("POST", "/api/questions", { title: form.elements.title.value, topic: form.elements.topic.value, ...composer.value() });
    location.href = `/question.html?id=${q.id}`;
  } catch (e) {
    error.textContent = e.message;
    button.disabled = false;
  }
});

start();
