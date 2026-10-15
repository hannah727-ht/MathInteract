
import { api, el, getMe, renderHeader } from "/js/common.js";
import { questionRow } from "/js/questions.js";

const params = new URLSearchParams(location.search);
const state = { topic: params.get("topic"), q: params.get("q") || "", page: Number(params.get("page")) || 1, topics: [] };
const searchInput = document.getElementById("search");

async function start() {
  renderHeader();
  searchInput.value = state.q;
  const me = await getMe();
  if (!me) document.getElementById("ask-button").href = "/login.html?next=/ask.html";
  await load();
}

function setUrl() {
  const query = new URLSearchParams();
  if (state.topic) query.set("topic", state.topic);
  if (state.q) query.set("q", state.q);
  if (state.page > 1) query.set("page", state.page);
  history.replaceState(null, "", query.size ? `?${query}` : location.pathname);
}

let latestRequest = 0;

async function load() {
  setUrl();
  const query = new URLSearchParams({ page: state.page });
  if (state.topic) query.set("topic", state.topic);
  if (state.q) query.set("q", state.q);
  const request = ++latestRequest;
  const data = await api("GET", `/api/questions?${query}`);
  if (request !== latestRequest) return;
  state.topics = data.topics;
  renderTopics();
  renderList(data);
  renderPager(data);
}

function renderTopics() {
  const chip = (key, name) =>
    el("button", {
      type: "button", class: "filter-chip", "aria-pressed": String(state.topic === key),
      onclick: () => { state.topic = key; state.page = 1; load(); },
    }, name);
  document.getElementById("topic-filter").replaceChildren(chip(null, "All topics"), ...state.topics.map((t) => chip(t.key, t.name)));
}

function topicName(key) {
  const topic = state.topics.find((t) => t.key === key);
  if (topic) return topic.name;
  return key;
}

function renderList(data) {
  const list = document.getElementById("question-list");
  if (!data.questions.length) {
    list.replaceChildren(
      el("div", { class: "dashed-box dashed-box-left" },
        el("h2", {}, state.q || state.topic ? "No questions match" : "No questions yet"),
        el("p", {}, state.q || state.topic ? "Try other words or another topic." : "Be the first to ask one!")
      )
    );
    return;
  }
  list.replaceChildren(
    el("p", { class: "result-count" }, `${data.total} ${data.total === 1 ? "question" : "questions"}`),
    el("ul", { class: "q-list" }, data.questions.map((q) => questionRow(q, topicName(q.topic))))
  );
}

function renderPager(data) {
  const pager = document.getElementById("pager");
  if (data.pages <= 1) return pager.replaceChildren();
  const go = (page) => { state.page = page; load(); window.scrollTo(0, 0); };
  pager.replaceChildren(
    el("button", { class: "btn btn-sm", type: "button", disabled: data.page <= 1, onclick: () => go(data.page - 1) }, "← Newer"),
    el("span", {}, `Page ${data.page} of ${data.pages}`),
    el("button", { class: "btn btn-sm", type: "button", disabled: data.page >= data.pages, onclick: () => go(data.page + 1) }, "Older →")
  );
}

let timer = null;
document.getElementById("search-form").addEventListener("submit", (event) => { event.preventDefault(); clearTimeout(timer); search(); });
searchInput.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(search, 350); });
function search() {
  state.q = searchInput.value.trim();
  state.page = 1;
  load();
}

start();
