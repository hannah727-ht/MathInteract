
import { api, el, formatDateTime, getMe, icon, loginPrompt, renderHeader } from "/js/common.js";
import { createComposer } from "/js/composer.js";
import { postBody, postText } from "/js/math.js";

const main = document.getElementById("question-main");
const id = new URLSearchParams(location.search).get("id");
const state = { me: null, q: null, topics: [], editing: null };

async function start() {
  renderHeader();
  const [me, list] = await Promise.all([getMe(), api("GET", "/api/questions?limit=1")]);
  state.me = me;
  state.topics = list.topics;
  await load();
}

async function load() {
  try {
    state.q = await api("GET", `/api/questions/${id}`);
  } catch (e) {
    if (e.status !== 404) throw e;
    main.replaceChildren(el("div", { class: "dashed-box dashed-box-left" }, el("h2", {}, "Question not found"),
      el("p", {}, "It may have been deleted.")));
    return;
  }
  document.title = `${state.q.title} · MathInteract`;
  render();
}

function topicName(key) {
  const topic = state.topics.find((t) => t.key === key);
  if (topic) return topic.name;
  return key;
}

function isAsker() {
  return state.me && state.me.id === state.q.user.id;
}

function render() {
  const q = state.q;
  main.replaceChildren(
    state.editing === "question" ? editQuestionForm(q) : questionCard(q),
    el("section", { class: "answers" },
      el("h2", {}, `${q.answer_count} ${q.answer_count === 1 ? "answer" : "answers"}`),
      q.answers.length ? el("ul", { class: "answer-list" }, q.answers.map(answerItem)) : el("p", { class: "muted" }, "No answers yet."),
      state.me ? answerForm(q) : loginPrompt("answer this question")
    )
  );
}

function byline(post, verb) {
  return el("div", { class: "comment-head" },
    el("strong", {}, post.user.username),
    post.user.is_admin ? el("span", { class: "chip chip-accent chip-sm" }, "Admin") : null,
    el("span", { class: "comment-time" }, `${verb} ${formatDateTime(post.created_at)}`, post.edited ? " · edited" : "")
  );
}


function questionCard(q) {
  const mine = state.me && state.me.id === q.user.id;
  return el("article", { class: "card question-card" },
    el("div", { class: "problem-meta" },
      el("span", { class: "chip" }, topicName(q.topic)),
      q.solved ? el("span", { class: "chip chip-solved" }, "Solved") : null
    ),
    el("h1", { class: "question-title" }, postText(q.title, "q-title-text")),
    byline(q, "asked"),
    postBody(q.body, q.images),
    mine || (state.me && state.me.is_admin)
      ? el("div", { class: "card-actions" },
          mine ? el("button", { class: "btn btn-sm", type: "button", onclick: () => { state.editing = "question"; render(); } }, "Edit question") : null,
          state.me && state.me.is_admin ? el("button", { class: "btn btn-sm btn-danger", type: "button", onclick: deleteQuestion }, "Delete question") : null)
      : null
  );
}

function editQuestionForm(q) {
  const title = el("input", { id: "eq-title", maxlength: 200 });
  title.value = q.title;
  const topic = el("select", { id: "eq-topic" }, state.topics.map((t) => el("option", { value: t.key, selected: t.key === q.topic }, t.name)));
  const composer = createComposer({ label: "Your question", text: q.body, images: q.images, rows: 8 });
  const error = el("p", { class: "form-error", role: "alert" });
  return el("form", {
    class: "card ask-form",
    onsubmit: async (event) => {
      event.preventDefault();
      error.textContent = "";
      try {
        state.q = await api("PUT", `/api/questions/${q.id}`, { title: title.value, topic: topic.value, ...composer.value() });
        state.editing = null;
        render();
      } catch (e) {
        error.textContent = e.message;
      }
    },
  },
    el("h2", {}, "Edit question"),
    el("div", { class: "field" }, el("label", { for: "eq-title" }, "Title"), title),
    el("div", { class: "field field-narrow" }, el("label", { for: "eq-topic" }, "Topic"), topic),
    composer.element,
    el("div", { class: "form-actions" },
      el("button", { class: "btn btn-primary", type: "submit" }, "Save"),
      el("button", { class: "btn", type: "button", onclick: () => { state.editing = null; render(); } }, "Cancel")),
    error
  );
}

async function deleteQuestion() {
  if (!confirm("Delete this question and all its answers? This can’t be undone.")) return;
  try {
    await api("DELETE", `/api/questions/${state.q.id}`);
    location.href = "/qa.html";
  } catch (e) {
    alert(e.message);
  }
}


function answerItem(a) {
  if (state.editing === a.id) return editAnswerForm(a);
  const mine = state.me && state.me.id === a.user.id;
  return el("li", { class: `comment answer ${a.accepted ? "is-accepted" : ""}` },
    a.accepted ? el("div", { class: "accepted-badge" }, "✓ Accepted answer") : null,
    byline(a, "answered"),
    postBody(a.body, a.images),
    el("div", { class: "answer-actions" },
      isAsker()
        ? el("button", { class: `btn btn-sm ${a.accepted ? "" : "btn-accept"}`, type: "button", onclick: () => accept(a.accepted ? null : a.id) },
            a.accepted ? "Undo accept" : "✓ Accept this answer")
        : null,
      mine ? el("button", { class: "link-btn", type: "button", onclick: () => { state.editing = a.id; render(); } }, "Edit") : null,
      state.me && state.me.is_admin ? el("button", { class: "link-btn danger", type: "button", onclick: () => deleteAnswer(a) }, "Delete") : null
    )
  );
}

function answerForm(q) {
  const composer = createComposer({ label: "Your answer", placeholder: "Explain your steps…", rows: 6 });
  const button = el("button", { class: "btn btn-primary", type: "submit" }, "Post answer");
  return el("form", {
    class: "comment-form",
    onsubmit: async (event) => {
      event.preventDefault();
      button.disabled = true;
      try {
        await api("POST", `/api/questions/${q.id}/answers`, composer.value());
        await load();
      } catch (e) {
        composer.setError(e.message);
        button.disabled = false;
      }
    },
  }, composer.element, el("div", { class: "form-actions" }, button));
}

function editAnswerForm(a) {
  const composer = createComposer({ text: a.body, images: a.images, rows: 6 });
  return el("li", { class: "comment comment-editing" },
    el("form", {
      onsubmit: async (event) => {
        event.preventDefault();
        try {
          await api("PUT", `/api/answers/${a.id}`, composer.value());
          state.editing = null;
          await load();
        } catch (e) {
          composer.setError(e.message);
        }
      },
    },
      composer.element,
      el("div", { class: "form-actions" },
        el("button", { class: "btn btn-primary btn-sm", type: "submit" }, "Save"),
        el("button", { class: "btn btn-sm", type: "button", onclick: () => { state.editing = null; render(); } }, "Cancel"))
    )
  );
}

async function accept(answerId) {
  try {
    state.q = await api("POST", `/api/questions/${state.q.id}/accept`, { answer_id: answerId });
    render();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteAnswer(a) {
  if (!confirm(`Delete ${a.user.username}’s answer? This can’t be undone.`)) return;
  try {
    await api("DELETE", `/api/answers/${a.id}`);
    await load();
  } catch (e) {
    alert(e.message);
  }
}

start();
