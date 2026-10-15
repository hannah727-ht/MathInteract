
import { api, el, formatDate, formatDateTime, formatSize, getMe, renderHeader } from "/js/common.js";
import { postText } from "/js/math.js";

const main = document.getElementById("admin-main");
const state = { q: "", page: 1, me: null, notice: null };

async function start() {
  renderHeader();
  state.me = await getMe();
  if (!state.me) return location.replace("/login.html?next=/admin.html");
  if (!state.me.is_admin) {
    main.replaceChildren(el("div", { class: "dashed-box dashed-box-left" }, el("h2", {}, "Admins only"),
      el("p", {}, "This page is only for admins.")));
    return;
  }
  main.replaceChildren(
    el("section", { class: "admin-section", id: "overview" }),
    el("section", { class: "admin-section", id: "traffic" }),
    el("section", { class: "admin-section", id: "scrapers" }),
    el("section", { class: "admin-section", id: "users" })
  );
  await Promise.all([loadOverview(), loadTraffic(), loadUsers()]);
}


let pollTimer = null;

async function loadOverview() {
  const data = await api("GET", "/api/admin/overview");
  const c = data.counts;
  const stat = (label, value, hint) => el("div", { class: "stat" }, el("strong", {}, String(value)), el("span", {}, label), hint ? el("small", {}, hint) : null);
  const used = data.disk.files + data.disk.database;
  document.getElementById("overview").replaceChildren(
    el("h2", {}, "Overview"),
    el("div", { class: "stat-grid" },
      stat("Users", c.users, `${c.admins} ${c.admins === 1 ? "admin" : "admins"}`),
      stat("Questions", c.questions),
      stat("Answers", c.answers),
      stat("Comments", c.comments),
      stat("Weekly problems", c.weekly_problems),
      stat("Resources", c.resources),
      stat("Disk used", formatSize(used), "of 2 GB on the server")
    )
  );
  renderScrapers(data.scrapers);
  clearTimeout(pollTimer);
  if (data.scrapers.some((s) => s.status === "running")) pollTimer = setTimeout(loadOverview, 4000);
}

function renderScrapers(scrapers) {
  const lastRun = (s) => {
    if (s.status === "running") return `Syncing now… ${s.added} new so far`;
    if (s.status === "never") return "Not synced yet";
    return `${s.status === "ok" ? "Synced" : "Failed"} ${formatDateTime(s.finished_at)}`;
  };
  const sections = [...new Set(scrapers.map((s) => s.section))];
  document.getElementById("scrapers").replaceChildren(
    el("h2", {}, "Scrapers"),
    el("table", { class: "admin-table" },
      el("thead", {}, el("tr", {}, ["Source", "Section", "Last run", "Papers", "Notes"].map((h) => el("th", {}, h)))),
      el("tbody", {}, scrapers.map((s) =>
        el("tr", {},
          el("td", {}, el("strong", {}, s.name)),
          el("td", {}, s.section === "us" ? "US" : "Canada"),
          el("td", { class: `sync-${s.status}` }, lastRun(s)),
          el("td", {}, String(s.found)),
          el("td", { class: "muted" }, s.message || "")
        )
      ))
    ),
    el("div", { class: "form-actions" },
      sections.map((section) =>
        el("button", {
          class: "btn btn-sm", type: "button", disabled: scrapers.some((s) => s.section === section && s.status === "running"),
          onclick: async () => { await api("POST", `/api/sync/${section}`); loadOverview(); },
        }, `Refresh ${section === "us" ? "US" : "Canada"} now`)
      )
    )
  );
}


const SVG = "http://www.w3.org/2000/svg";
let trafficDays = 30;

function svg(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

function dayLabel(iso, options = { month: "short", day: "numeric" }) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", options);
}

function niceMax(value) {
  if (value <= 5) return 5;
  const step = 10 ** Math.floor(Math.log10(value));
  return [1, 2, 5, 10].map((m) => m * step).find((n) => n >= value);
}

async function loadTraffic() {
  const section = document.getElementById("traffic");
  section.classList.add("is-loading");
  const data = await api("GET", `/api/admin/traffic?days=${trafficDays}`);
  section.classList.remove("is-loading");
  const t = data.totals;
  const tile = (label, value) => el("div", { class: "stat" }, el("strong", {}, value), el("span", {}, label));
  section.replaceChildren(
    el("div", { class: "traffic-head" },
      el("h2", {}, "Traffic"),
      el("div", { class: "kind-filter", role: "group", "aria-label": "Time range" },
        [7, 30, 90].map((n) => el("button", {
          type: "button", class: "filter-chip", "aria-pressed": String(n === trafficDays),
          onclick: () => { trafficDays = n; loadTraffic(); },
        }, `Last ${n} days`))
      )
    ),
    el("p", { class: "muted traffic-note" }, "Counted on our own server. Admins’ visits and bots aren’t counted, and no IP addresses are stored."),
    el("div", { class: "stat-grid stat-grid-4" },
      tile(`Page views (${trafficDays} days)`, t.views.toLocaleString("en-US")),
      tile("Visitors per day (average)", String(t.average_visitors)),
      tile(`Logged-in users (${trafficDays} days)`, String(t.logged_in_users)),
      tile("Page views today", String(t.today_views))
    ),
    el("div", { class: "card chart-card" },
      el("h3", { class: "chart-title" }, "Page views per day"),
      viewsChart(data.days),
      trafficTable(data.days)
    ),
    el("div", { class: "top-grid" },
      topList("Top pages", data.top_pages, (p) => [p.name, p.views]),
      topList("Most opened resources", data.top_resources, (r) => [el("a", { href: `/api/resources/${r.id}/open`, target: "_blank", rel: "noopener" }, r.title), r.opens, r.where]),
      topList("Most viewed questions", data.top_questions, (q) => [el("a", { href: `/question.html?id=${q.id}` }, postText(q.title, "q-title-text")), q.views]),
      topList("Most viewed weekly problems", data.top_weekly, (w) => [el("a", { href: `/weekly.html?id=${w.id}` }, postText(w.title, "q-title-text")), w.views])
    )
  );
}

function viewsChart(days) {
  const width = 1052, height = 220, left = 40, right = 8, top = 22, bottom = 26;
  const plotW = width - left - right, plotH = height - top - bottom;
  const max = niceMax(Math.max(...days.map((d) => d.views)));
  const slot = plotW / days.length;
  const barW = Math.min(24, Math.max(2, slot - 2));
  const y = (v) => top + plotH - (v / max) * plotH;

  const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, class: "views-chart", role: "img",
    "aria-label": `Page views per day for the last ${days.length} days. The table below lists every day.` });
  for (const tick of [0, max / 2, max]) {
    chart.append(svg("line", { x1: left, x2: width - right, y1: y(tick), y2: y(tick), class: "chart-grid" }));
    chart.append(svg("text", { x: left - 8, y: y(tick) + 4, class: "chart-axis", "text-anchor": "end" }, String(tick)));
  }
  const labelEvery = days.length <= 7 ? 1 : 7;
  const peak = days.reduce((best, d) => (d.views > best.views ? d : best), days[0]);
  const tip = el("div", { class: "chart-tip", hidden: true });

  days.forEach((d, i) => {
    const cx = left + slot * i + slot / 2;
    if (d.views > 0) {
      const h = Math.max(2, plotH - (y(d.views) - top));
      const r = Math.min(4, barW / 2, h);
      const x0 = cx - barW / 2, x1 = cx + barW / 2, yTop = top + plotH - h, yBase = top + plotH;
      chart.append(svg("path", { class: "chart-bar", d:
        `M${x0},${yBase} V${yTop + r} Q${x0},${yTop} ${x0 + r},${yTop} H${x1 - r} Q${x1},${yTop} ${x1},${yTop + r} V${yBase} Z` }));
    }
    if ((days.length - 1 - i) % labelEvery === 0) {
      const last = i === days.length - 1, first = i === 0;
      chart.append(svg("text", { x: last ? width - right : first ? left : cx, y: height - 6, class: "chart-axis",
        "text-anchor": last ? "end" : first ? "start" : "middle" }, dayLabel(d.day)));
    }
    const hit = svg("rect", { x: left + slot * i, y: top, width: slot, height: plotH, class: "chart-hit", tabindex: "0",
      "aria-label": `${dayLabel(d.day)}: ${d.views} views, ${d.visitors} visitors, ${d.active_users} logged-in users` });
    const show = () => {
      tip.replaceChildren(
        el("strong", {}, `${d.views} ${d.views === 1 ? "view" : "views"}`),
        el("span", {}, `${d.visitors} ${d.visitors === 1 ? "visitor" : "visitors"} · ${d.active_users} logged in`),
        el("span", { class: "muted" }, dayLabel(d.day, { weekday: "short", month: "short", day: "numeric" }))
      );
      const share = cx / width;
      tip.style.left = `${share * 100}%`;
      tip.style.transform = share > 0.85 ? "translateX(-100%)" : share < 0.15 ? "translateX(0)" : "translateX(-50%)";
      tip.hidden = false;
      hit.classList.add("is-active");
    };
    const hide = () => { tip.hidden = true; hit.classList.remove("is-active"); };
    hit.addEventListener("pointerenter", show);
    hit.addEventListener("pointerleave", hide);
    hit.addEventListener("focus", show);
    hit.addEventListener("blur", hide);
    chart.append(hit);
  });

  if (peak.views > 0) {
    const i = days.indexOf(peak);
    chart.append(svg("text", { x: left + slot * i + slot / 2, y: y(peak.views) - 6, class: "chart-label", "text-anchor": "middle" }, String(peak.views)));
  }
  const wrap = el("div", { class: "chart-wrap" }, chart, tip);
  if (peak.views === 0) wrap.append(el("p", { class: "chart-empty muted" }, "No visits in this period yet."));
  return wrap;
}

function trafficTable(days) {
  return el("details", { class: "chart-table" },
    el("summary", {}, "Show as table"),
    el("table", { class: "admin-table" },
      el("thead", {}, el("tr", {}, ["Day", "Page views", "Visitors", "Logged-in users"].map((h) => el("th", {}, h)))),
      el("tbody", {}, [...days].reverse().map((d) =>
        el("tr", {}, el("td", {}, dayLabel(d.day, { weekday: "short", month: "short", day: "numeric" })),
          el("td", {}, String(d.views)), el("td", {}, String(d.visitors)), el("td", {}, String(d.active_users)))))
    )
  );
}

function topList(title, rows, cells) {
  return el("div", { class: "card top-card" },
    el("h3", {}, title),
    rows.length
      ? el("ol", { class: "top-list" }, rows.map((row) => {
          const [name, count, sub] = cells(row);
          return el("li", {}, el("span", { class: "top-name" }, name, sub ? el("small", {}, sub) : null), el("span", { class: "top-count" }, String(count)));
        }))
      : el("p", { class: "muted" }, "Nothing yet.")
  );
}


let searchTimer = null;
let latestRequest = 0;

async function loadUsers() {
  const query = new URLSearchParams({ page: state.page });
  if (state.q) query.set("q", state.q);
  const request = ++latestRequest;
  const data = await api("GET", `/api/admin/users?${query}`);
  if (request !== latestRequest) return;
  renderUsers(data);
}

function renderUsers(data) {
  const section = document.getElementById("users");
  let search = section.querySelector("#user-search");
  if (!search) {
    search = el("input", { id: "user-search", type: "search", placeholder: "Search usernames…", autocomplete: "off" });
    search.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { state.q = search.value.trim(); state.page = 1; loadUsers(); }, 300);
    });
    section.append(
      el("div", { class: "admin-users-head" }, el("h2", {}, "Users"), el("label", { class: "visually-hidden", for: "user-search" }, "Search usernames"), search),
      el("div", { id: "user-notice" }),
      el("div", { id: "user-table" })
    );
  }
  renderNotice();
  const table = section.querySelector("#user-table");
  if (!data.users.length) return table.replaceChildren(el("p", { class: "muted" }, "No users match."));
  table.replaceChildren(
    el("table", { class: "admin-table" },
      el("thead", {}, el("tr", {}, ["Username", "Joined", "Role", "Posts", ""].map((h) => el("th", {}, h)))),
      el("tbody", {}, data.users.map(userRow))
    )
  );
  if (data.pages > 1) {
    table.append(
      el("nav", { class: "pager pager-tight", "aria-label": "Pages" },
        el("button", { class: "btn btn-sm", type: "button", disabled: data.page <= 1, onclick: () => { state.page--; loadUsers(); } }, "← Newer"),
        el("span", {}, `Page ${data.page} of ${data.pages} · ${data.total} users`),
        el("button", { class: "btn btn-sm", type: "button", disabled: data.page >= data.pages, onclick: () => { state.page++; loadUsers(); } }, "Older →"))
    );
  }
}

function userRow(u) {
  const isMe = u.id === state.me.id;
  return el("tr", {},
    el("td", {}, el("strong", {}, u.username), isMe ? el("span", { class: "muted" }, " (you)") : null),
    el("td", {}, formatDate(u.created_at)),
    el("td", {}, u.is_admin ? el("span", { class: "chip chip-accent" }, "Admin") : el("span", { class: "chip" }, "User")),
    el("td", {}, String(u.posts)),
    el("td", { class: "row-actions" },
      el("button", { class: "btn btn-sm", type: "button", onclick: () => toggleAdmin(u) }, u.is_admin ? "Remove admin" : "Make admin"),
      el("button", { class: "btn btn-sm", type: "button", onclick: () => resetPassword(u) }, "Reset password")
    )
  );
}

async function toggleAdmin(u) {
  const question = u.is_admin
    ? `Remove admin rights from ${u.username}?${u.id === state.me.id ? " You will lose access to this page." : ""}`
    : `Make ${u.username} an admin? Admins can upload and delete files, post weekly problems, delete posts, and manage users.`;
  if (!confirm(question)) return;
  try {
    await api("POST", `/api/admin/users/${u.id}/admin`, { is_admin: !u.is_admin });
    if (u.id === state.me.id) return location.replace("/");
    await Promise.all([loadUsers(), loadOverview()]);
  } catch (e) {
    alert(e.message);
  }
}

async function resetPassword(u) {
  if (!confirm(`Reset ${u.username}’s password? Their old password will stop working.`)) return;
  try {
    state.notice = await api("POST", `/api/admin/users/${u.id}/reset-password`);
    renderNotice();
  } catch (e) {
    alert(e.message);
  }
}

function renderNotice() {
  const box = document.getElementById("user-notice");
  if (!box) return;
  if (!state.notice) return box.replaceChildren();
  const { username, temporary_password: password } = state.notice;
  box.replaceChildren(
    el("div", { class: "notice-box", role: "status" },
      el("p", {}, "New temporary password for ", el("strong", {}, username), ":"),
      el("code", { class: "temp-password" }, password),
      el("p", { class: "muted" }, "Give it to them privately (not in a public post). They should log in and change it on their Account page. It won’t be shown again."),
      el("div", { class: "form-actions" },
        el("button", { class: "btn btn-sm", type: "button", onclick: () => {
          if (navigator.clipboard) navigator.clipboard.writeText(password);
        } }, "Copy"),
        el("button", { class: "btn btn-sm", type: "button", onclick: () => { state.notice = null; renderNotice(); } }, "Done"))
    )
  );
}

start();
