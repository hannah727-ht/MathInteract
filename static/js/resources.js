
import { api, el, formatDate, formatSize, getMe, icon, renderHeader } from "/js/common.js";

const header = document.getElementById("site-header");
const params = new URLSearchParams(location.search);
const state = {
  section: params.get("section"),
  contest: params.get("contest"),
  kind: params.get("kind"),
  catalog: null,
  resources: [],
  me: null,
};


async function start() {
  const [catalog, me] = await Promise.all([api("GET", "/api/catalog"), getMe()]);
  state.catalog = catalog;
  state.me = me;
  if (!catalog.sections[state.section]) state.section = "us";
  header.dataset.page = `section-${state.section}`;
  renderHeader();

  const section = currentSection();
  document.title = `${section.name} · MathInteract`;
  document.getElementById("section-title").textContent = section.name;
  document.getElementById("section-blurb").textContent = section.blurb;
  document.getElementById("source-note").textContent = section.source_note;
  document.getElementById("official-links").append(
    ...section.links.map((link) =>
      el("li", {}, el("a", { href: link.url, target: "_blank", rel: "noopener" }, link.label, icon("external", "icon icon-sm")))
    )
  );
  if (me && me.is_admin) setUpUploadForm();

  await loadResources();
  await loadSyncStatus();
}

async function loadResources() {
  state.resources = await api("GET", `/api/resources?section=${state.section}`);
  render();
}

function currentSection() {
  return state.catalog.sections[state.section];
}


function select(changes) {
  Object.assign(state, changes);
  const query = new URLSearchParams({ section: state.section, contest: state.contest });
  if (state.kind) query.set("kind", state.kind);
  history.pushState(null, "", `?${query}`);
  document.getElementById("page-note").textContent = "";
  render();
}

window.addEventListener("popstate", () => {
  const p = new URLSearchParams(location.search);
  if (p.get("section") !== state.section) return location.reload();
  state.contest = p.get("contest");
  state.kind = p.get("kind");
  render();
});


function render() {
  const contests = currentSection().contests;
  if (!contests.some((c) => c.key === state.contest)) state.contest = contests[0].key;
  const inContest = state.resources.filter((r) => r.contest === state.contest);
  const kinds = state.catalog.kinds.filter((k) => inContest.some((r) => r.kind === k.key));
  if (!kinds.some((k) => k.key === state.kind)) state.kind = null;

  renderTabs(contests);
  renderKindFilter(kinds);
  document.querySelector(".toolbar").hidden = kinds.length < 2 && !(state.me && state.me.is_admin);
  renderList(inContest.filter((r) => !state.kind || r.kind === state.kind));
}

function renderTabs(contests) {
  const tabs = document.getElementById("contest-tabs");
  tabs.replaceChildren(
    ...contests.map((c) => {
      const count = state.resources.filter((r) => r.contest === c.key).length;
      return el("a", {
        class: "contest-tab",
        href: `?section=${state.section}&contest=${c.key}`,
        "aria-current": c.key === state.contest ? "page" : null,
        onclick: (event) => { event.preventDefault(); select({ contest: c.key, kind: null }); },
      }, c.name, el("span", { class: "count" }, String(count)));
    })
  );
}

function renderKindFilter(kinds) {
  const box = document.getElementById("kind-filter");
  if (kinds.length < 2) return box.replaceChildren();
  const chip = (key, name) =>
    el("button", {
      type: "button",
      class: "filter-chip",
      "aria-pressed": String(state.kind === key),
      onclick: () => select({ kind: key }),
    }, name);
  box.replaceChildren(chip(null, "All types"), ...kinds.map((k) => chip(k.key, k.name)));
}

function renderList(items) {
  const list = document.getElementById("resource-list");
  if (items.length === 0) {
    const contest = currentSection().contests.find((c) => c.key === state.contest);
    list.replaceChildren(
      el("div", { class: "dashed-box dashed-box-left" },
        icon("file"),
        el("h2", {}, `No resources for ${contest.name} yet`),
        el("p", {}, state.me && state.me.is_admin ? "Use the Upload button to add the first one." : "Check back soon.")
      )
    );
    return;
  }

  const groups = new Map();
  for (const r of items) {
    const label = r.year ? String(r.year) : "No year";
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(r);
  }
  list.replaceChildren(
    ...[...groups].map(([label, rows]) =>
      el("section", { class: "year-group" },
        el("h2", {}, label),
        el("ul", { class: "res-list" }, rows.map(resourceRow))
      )
    )
  );
}

function resourceRow(r) {
  const kind = state.catalog.kinds.find((k) => k.key === r.kind);
  const kindName = kind ? kind.name : r.kind;
  const sourceName = state.catalog.sources[r.source] || r.source;
  const meta = [sourceName, formatSize(r.size)].filter(Boolean).join(" · ");
  const external = r.file_type === "Link";
  const canDelete = state.me && state.me.is_admin && r.source === "upload";
  return el("li", { class: "res-row" },
    el("span", { class: `file-badge ${r.file_type === "Link" ? "is-link" : ""}` },
      r.file_type === "Link" ? icon("link", "icon icon-sm") : r.file_type),
    el("a", { class: "res-title", href: r.open_url, target: "_blank", rel: "noopener", title: external ? "Opens on the official site" : null },
      r.title, external ? icon("external", "icon icon-sm res-ext") : null),
    el("span", { class: "chip" }, kindName),
    el("span", { class: "res-meta" }, meta),
    canDelete
      ? el("button", { class: "icon-btn", type: "button", title: "Delete", "aria-label": `Delete ${r.title}`, onclick: () => remove(r) }, icon("trash"))
      : null
  );
}


let pollTimer = null;

async function loadSyncStatus() {
  const { sources } = await api("GET", `/api/sync/${state.section}`);
  const box = document.getElementById("sync-box");
  if (sources.length === 0) return;
  box.hidden = false;
  document.getElementById("sync-list").replaceChildren(...sources.map(syncLine));

  const running = sources.some((s) => s.status === "running");
  const button = document.getElementById("sync-now");
  if (state.me && state.me.is_admin) {
    button.hidden = false;
    button.disabled = running;
    button.textContent = running ? "Syncing…" : "Refresh now";
    button.onclick = refreshNow;
  }
  clearTimeout(pollTimer);
  if (running) {
    pollTimer = setTimeout(async () => { await loadResources(); await loadSyncStatus(); }, 4000);
  }
}

function syncLine(s) {
  const when = (iso) => `${formatDate(iso)}, ${new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;
  let text;
  if (s.status === "running") text = `Syncing now… ${s.added} new so far`;
  else if (s.status === "ok") text = `Last synced ${when(s.finished_at)} · ${s.found} papers`;
  else if (s.status === "error") text = `Last try failed (${when(s.finished_at)}). It will retry automatically.`;
  else text = "Not synced yet";
  return el("li", { class: `sync-line sync-${s.status}` },
    el("strong", {}, s.name), el("span", {}, text),
    s.message && s.status !== "running" && state.me && state.me.is_admin ? el("span", { class: "sync-message" }, s.message) : null
  );
}

async function refreshNow() {
  const error = document.getElementById("sync-error");
  error.textContent = "";
  try {
    await api("POST", `/api/sync/${state.section}`);
    await loadSyncStatus();
  } catch (e) {
    error.textContent = e.message;
  }
}


function setUpUploadForm() {
  const form = document.getElementById("upload-form");
  const toggle = document.getElementById("upload-toggle");
  const contestSelect = form.elements.contest;
  toggle.hidden = false;

  contestSelect.append(...currentSection().contests.map((c) => el("option", { value: c.key }, c.name)));
  form.elements.kind.append(...state.catalog.kinds.map((k) => el("option", { value: k.key }, k.name)));
  document.getElementById("up-hint").textContent =
    `PDF, images (PNG, JPG, WEBP), or Word (DOC, DOCX), up to ${state.catalog.max_upload_mb} MB.`;

  const close = () => { form.hidden = true; toggle.hidden = false; form.reset(); form.querySelector(".form-error").textContent = ""; };
  toggle.onclick = () => {
    contestSelect.value = state.contest;
    form.hidden = false;
    toggle.hidden = true;
    contestSelect.focus();
  };
  document.getElementById("upload-cancel").onclick = close;

  form.onsubmit = async (event) => {
    event.preventDefault();
    const error = form.querySelector(".form-error");
    const button = form.querySelector('button[type="submit"]');
    error.textContent = "";
    if (!form.elements.file.files.length) {
      error.textContent = "Please choose a file.";
      return;
    }
    const data = new FormData(form);
    data.set("section", state.section);
    button.disabled = true;
    button.textContent = "Uploading…";
    try {
      const item = await api("POST", "/api/resources", data);
      close();
      state.resources = await api("GET", `/api/resources?section=${state.section}`);
      select({ contest: item.contest, kind: null });
      document.getElementById("page-note").textContent = `Uploaded “${item.title}”.`;
    } catch (e) {
      error.textContent = e.message;
    } finally {
      button.disabled = false;
      button.textContent = "Upload";
    }
  };
}

async function remove(r) {
  if (!confirm(`Delete “${r.title}”? This can’t be undone.`)) return;
  try {
    await api("DELETE", `/api/resources/${r.id}`);
    await loadResources();
    document.getElementById("page-note").textContent = `Deleted “${r.title}”.`;
  } catch (e) {
    alert(e.message);
  }
}

start();
