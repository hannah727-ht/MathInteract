
import { api, el, getMe, icon, renderHeader } from "/js/common.js";
import { createComposer } from "/js/composer.js";
import { postBody } from "/js/math.js";

const main = document.getElementById("weekly-main");
const aside = document.getElementById("weekly-archive");
const state = {
  id: new URLSearchParams(location.search).get("id"),
  me: null,
  problem: null,
  archive: null,
  showDiscussion: false,
  editingComment: null,
};


function day(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}
const fmt = (iso, options) => day(iso).toLocaleDateString("en-US", options);
const short = (iso) => fmt(iso, { month: "short", day: "numeric" });
const weekLabel = (p) => `Week of ${short(p.week_start)} – ${short(p.week_end)}, ${day(p.week_end).getFullYear()}`;
const when = (isoTime) => new Date(isoTime).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });


async function start() {
  renderHeader();
  state.me = await getMe();
  await load();
}

async function load() {
  try {
    const [archive, problem] = await Promise.all([
      api("GET", "/api/weekly"),
      state.id ? api("GET", `/api/weekly/${state.id}`) : api("GET", "/api/weekly/current").then((d) => d.problem),
    ]);
    state.archive = archive;
    state.problem = problem;
  } catch (e) {
    state.problem = null;
    if (e.status !== 404) throw e;
    if (state.archive === null) {
      state.archive = await api("GET", "/api/weekly");
    }
  }
  render();
}

function render() {
  renderArchive();
  if (state.problem) {
    main.replaceChildren(problemCard(state.problem), solutionCard(state.problem), discussion(state.problem));
  } else {
    main.replaceChildren(
      el("div", { class: "dashed-box dashed-box-left" },
        icon("calendar"),
        el("h2", {}, state.id ? "Problem not found" : "No problem this week yet"),
        el("p", {}, "Try a problem from an earlier week in the list on the right.")
      )
    );
  }
}


function statusChip(status) {
  if (status === "current") return el("span", { class: "chip chip-accent" }, "This week");
  if (status === "scheduled") return el("span", { class: "chip chip-scheduled" }, "Scheduled");
  return null;
}

function problemCard(p) {
  return el("article", { class: "card problem-card" },
    el("div", { class: "problem-meta" }, statusChip(p.status), el("span", {}, weekLabel(p))),
    el("h2", { class: "problem-title" }, p.title),
    postBody(p.body, p.images),
    state.me && state.me.is_admin
      ? el("div", { class: "card-actions" },
          el("button", { class: "btn btn-sm", type: "button", onclick: () => showProblemForm(p) }, "Edit problem"))
      : null
  );
}

function solutionCard(p) {
  const card = el("section", { class: "card solution-card" }, el("h2", {}, "Solution"));
  const releaseDay = fmt(p.solution_release, { weekday: "long", month: "long", day: "numeric" });
  if (p.solution_released) {
    card.append(p.solution ? postBody(p.solution, p.solution_images) : el("p", { class: "muted" }, "No official solution was posted for this problem."));
  } else if (p.solution !== null) {
    card.append(
      el("p", { class: "admin-note" }, icon("eye", "icon icon-sm"), `Only admins can see this until ${releaseDay}.`),
      p.solution ? postBody(p.solution, p.solution_images) : el("p", { class: "muted" }, "No solution written yet.")
    );
  } else {
    card.append(el("p", { class: "muted" }, `The solution will appear on ${releaseDay}.`));
  }
  return card;
}


function discussion(p) {
  const section = el("section", { class: "discussion" },
    el("h2", {}, "Discussion ", el("span", { class: "count" }, String(p.comment_count)))
  );

  const folded = p.status === "current" && p.comment_count > 0 && !state.showDiscussion;
  if (folded) {
    section.append(
      el("div", { class: "spoiler-box" },
        el("p", {}, "This week’s discussion is hidden so it doesn’t spoil the problem. Try it first!"),
        el("button", { class: "btn btn-sm", type: "button", onclick: () => { state.showDiscussion = true; render(); } },
          icon("eye", "icon icon-sm"), `Show discussion (${p.comment_count} ${p.comment_count === 1 ? "comment" : "comments"})`)
      )
    );
  } else if (p.comments.length) {
    section.append(el("ul", { class: "comment-list" }, p.comments.map(comment)));
  } else if (p.status !== "scheduled") {
    section.append(el("p", { class: "muted" }, "No comments yet. Be the first to share an idea!"));
  }

  if (p.status === "scheduled") {
    section.append(el("p", { class: "muted" }, "Comments open when this week starts."));
  } else if (state.me) {
    section.append(newCommentForm(p));
  } else {
    const next = encodeURIComponent(location.pathname + location.search);
    section.append(el("p", { class: "login-prompt" },
      el("a", { href: `/login.html?next=${next}` }, "Log in"), " or ", el("a", { href: `/signup.html?next=${next}` }, "sign up"), " to join the discussion."));
  }
  return section;
}

function comment(c) {
  const mine = state.me && state.me.id === c.user.id;
  if (state.editingComment === c.id) return editCommentForm(c);
  return el("li", { class: "comment" },
    el("div", { class: "comment-head" },
      el("strong", {}, c.user.username),
      c.user.is_admin ? el("span", { class: "chip chip-accent chip-sm" }, "Admin") : null,
      el("span", { class: "comment-time" }, when(c.created_at), c.edited ? " · edited" : ""),
      el("span", { class: "comment-actions" },
        mine ? el("button", { class: "link-btn", type: "button", onclick: () => { state.editingComment = c.id; render(); } }, "Edit") : null,
        state.me && state.me.is_admin ? el("button", { class: "link-btn danger", type: "button", onclick: () => deleteComment(c) }, "Delete") : null
      )
    ),
    postBody(c.body, c.images)
  );
}

function newCommentForm(p) {
  const composer = createComposer({ label: "Your comment", placeholder: "Share an idea, a hint, or your answer…", rows: 4 });
  const button = el("button", { class: "btn btn-primary", type: "submit" }, "Post comment");
  return el("form", {
    class: "comment-form",
    onsubmit: async (event) => {
      event.preventDefault();
      button.disabled = true;
      try {
        await api("POST", `/api/weekly/${p.id}/comments`, composer.value());
        state.showDiscussion = true;
        await load();
      } catch (e) {
        composer.setError(e.message);
        button.disabled = false;
      }
    },
  }, composer.element, el("div", { class: "form-actions" }, button));
}

function editCommentForm(c) {
  const composer = createComposer({ text: c.body, images: c.images, rows: 4 });
  return el("li", { class: "comment comment-editing" },
    el("form", {
      onsubmit: async (event) => {
        event.preventDefault();
        try {
          await api("PUT", `/api/comments/${c.id}`, composer.value());
          state.editingComment = null;
          await load();
        } catch (e) {
          composer.setError(e.message);
        }
      },
    },
      composer.element,
      el("div", { class: "form-actions" },
        el("button", { class: "btn btn-primary btn-sm", type: "submit" }, "Save"),
        el("button", { class: "btn btn-sm", type: "button", onclick: () => { state.editingComment = null; render(); } }, "Cancel")
      )
    )
  );
}

async function deleteComment(c) {
  if (!confirm(`Delete ${c.user.username}’s comment? This can’t be undone.`)) return;
  try {
    await api("DELETE", `/api/comments/${c.id}`);
    await load();
  } catch (e) {
    alert(e.message);
  }
}


function renderArchive() {
  const problems = state.archive.problems;
  const shownId = state.problem ? state.problem.id : null;
  aside.replaceChildren(
    el("div", { class: "archive-head" },
      el("h2", {}, "All weeks"),
      state.me && state.me.is_admin ? el("button", { class: "btn btn-primary btn-sm", type: "button", onclick: () => showProblemForm(null) }, "New problem") : null
    ),
    problems.length
      ? el("ul", { class: "week-list" },
          problems.map((p) =>
            el("li", {},
              el("a", { href: `/weekly.html?id=${p.id}`, "aria-current": p.id === shownId ? "page" : null },
                el("span", { class: "week-date" }, short(p.week_start), statusChip(p.status)),
                el("span", { class: "week-title" }, p.title),
                el("span", { class: "week-count" }, `${p.comment_count} ${p.comment_count === 1 ? "comment" : "comments"}`)
              )
            )
          )
        )
      : el("p", { class: "muted" }, "No problems yet.")
  );
}


function mondays(fromIso, count) {
  const list = [];
  const d = day(fromIso);
  for (let i = 0; i < count; i++) {
    list.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`);
    d.setDate(d.getDate() + 7);
  }
  return list;
}

function showProblemForm(p) {
  const taken = new Set(state.archive.problems.map((x) => x.week_start));
  const started = p && p.status !== "scheduled";
  const weekSelect = el("select", { id: "pf-week", disabled: started });
  const problemWeek = p ? p.week_start : null;
  const choices = started ? [p.week_start] : mondays(state.archive.current_week, 13).filter((w) => !taken.has(w) || w === problemWeek);
  weekSelect.append(...choices.map((w) => el("option", { value: w }, `Week of ${fmt(w, { month: "long", day: "numeric", year: "numeric" })}`)));
  if (p) weekSelect.value = p.week_start;

  const title = el("input", { id: "pf-title", maxlength: 200, required: true });
  title.value = p ? p.title : "";
  const body = createComposer({ label: "Problem", text: p ? p.body : "", images: p ? p.images : [], rows: 6 });
  const solution = createComposer({ label: "Solution (hidden until the next week begins)", text: p ? p.solution : "", images: p ? p.solution_images : [], rows: 6 });
  const error = el("p", { class: "form-error", role: "alert" });
  const save = el("button", { class: "btn btn-primary", type: "submit" }, p ? "Save changes" : "Publish problem");

  const form = el("form", {
    class: "card problem-form",
    onsubmit: async (event) => {
      event.preventDefault();
      error.textContent = "";
      save.disabled = true;
      const data = {
        week_start: weekSelect.value, title: title.value,
        body: body.value().body, image_ids: body.value().image_ids,
        solution: solution.value().body, solution_image_ids: solution.value().image_ids,
      };
      try {
        const saved = await api(p ? "PUT" : "POST", p ? `/api/weekly/${p.id}` : "/api/weekly", data);
        location.href = `/weekly.html?id=${saved.id}`;
      } catch (e) {
        error.textContent = e.message;
        save.disabled = false;
      }
    },
  },
    el("h2", {}, p ? "Edit problem" : "New problem"),
    el("div", { class: "field" }, el("label", { for: "pf-week" }, "Week"), weekSelect,
      started ? el("span", { class: "hint" }, "This week has started, so it can’t change.") : null),
    el("div", { class: "field" }, el("label", { for: "pf-title" }, "Title"), title),
    body.element,
    solution.element,
    el("div", { class: "form-actions" },
      save,
      el("button", { class: "btn", type: "button", onclick: () => render() }, "Cancel"),
      p && p.status === "scheduled"
        ? el("button", { class: "btn btn-danger", type: "button", onclick: () => deleteProblem(p) }, "Delete problem")
        : null
    ),
    error
  );
  if (!choices.length) error.textContent = "The next 13 weeks already have problems.";
  main.replaceChildren(form);
  title.focus();
}

async function deleteProblem(p) {
  if (!confirm(`Delete “${p.title}”? This can’t be undone.`)) return;
  try {
    await api("DELETE", `/api/weekly/${p.id}`);
    location.href = "/weekly.html";
  } catch (e) {
    alert(e.message);
  }
}

start();
