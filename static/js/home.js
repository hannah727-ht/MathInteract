
import { SECTIONS, api, el, formatDate, icon, renderHeader } from "/js/common.js";
import { postText } from "/js/math.js";
import { questionRow } from "/js/questions.js";

renderHeader();

const ENTRIES = [
  ...Object.entries(SECTIONS).map(([key, s]) => ({
    href: `/resources.html?section=${key}`, title: s.name, text: s.blurb, icon: s.icon, go: "Browse papers",
  })),
  { href: "/weekly.html", title: "Weekly Problem", text: "A new problem every Monday. Share your ideas and see the solution next week.", icon: "calendar", go: "Try this week’s problem" },
  { href: "/qa.html", title: "Q&A", text: "Stuck on a problem? Ask a question and help others with theirs.", icon: "help", go: "Ask or answer" },
];

document.getElementById("entry-grid").append(
  ...ENTRIES.map((e) =>
    el("a", { class: "entry-card", href: e.href },
      el("span", { class: "entry-icon" }, icon(e.icon)),
      el("h2", {}, e.title),
      el("p", {}, e.text),
      el("span", { class: "go" }, e.go, icon("arrow"))
    )
  )
);

async function showRecent() {
  const items = await api("GET", "/api/resources/recent?limit=6").catch(() => []);
  if (items.length === 0) return;
  document.getElementById("recent-list").append(
    ...items.map((r) =>
      el("li", { class: "recent-row" },
        el("a", { class: "res-title", href: r.open_url, target: "_blank", rel: "noopener" }, r.title),
        el("a", { class: "recent-where", href: `/resources.html?section=${r.section}&contest=${r.contest}` },
          `${r.contest_name} · ${r.section_name}`),
        el("span", { class: "res-meta" }, formatDate(r.created_at))
      )
    )
  );
  document.getElementById("recent-block").hidden = false;
}

showRecent();

async function showWeekly() {
  const { problem } = await api("GET", "/api/weekly/current").catch(() => ({ problem: null }));
  if (!problem) return;
  const count = problem.comment_count;
  document.getElementById("weekly-preview").append(
    el("span", { class: "weekly-preview-title" }, problem.title),
    el("div", { class: "weekly-preview-body" }, postText(problem.body)),
    el("span", { class: "go" }, `Try it and join the discussion (${count} ${count === 1 ? "comment" : "comments"})`, icon("arrow"))
  );
  document.getElementById("weekly-block").hidden = false;
}

showWeekly();

async function showQuestions() {
  const data = await api("GET", "/api/questions?limit=5").catch(() => null);
  if (!data || !data.questions.length) return;
  const topicName = (key) => {
    const topic = data.topics.find((t) => t.key === key);
    if (topic) return topic.name;
    return key;
  };
  document.getElementById("latest-questions").append(...data.questions.map((q) => questionRow(q, topicName(q.topic))));
  document.getElementById("questions-block").hidden = false;
}

showQuestions();
