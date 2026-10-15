
const ICON_PATHS = {
  award: "M12 15a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM8.5 13.5 7 22l5-3 5 3-1.5-8.5",
  leaf: "M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10zM2 21c0-3 1.9-5.4 5.1-6C9.5 14.5 12 13 13 12",
  book: "M4 5.5A1.5 1.5 0 0 1 5.5 4H11v15H5.5A1.5 1.5 0 0 0 4 20.5zM20 5.5A1.5 1.5 0 0 0 18.5 4H13v15h5.5a1.5 1.5 0 0 1 1.5 1.5z",
  cap: "M22 10 12 5 2 10l10 5 10-5zM6 12v5c3 3 9 3 12 0v-5",
  calendar: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
  help: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01",
  arrow: "M5 12h14M13 6l6 6-6 6",
  image: "M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM4 16l5-5 5 5M13 14l2-2 5 5M15.5 8.5h.01",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  file: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h4",
  link: "M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1",
  upload: "M12 15V4M7.5 8.5 12 4l4.5 4.5M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13M9 7V4h6v3",
  external: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  tool: "M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z",
};

export function icon(name, className = "icon") {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("class", className);
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", ICON_PATHS[name]);
  svg.append(path);
  return svg;
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

export const SECTIONS = {
  us: { name: "US Competitions", tab: "US", icon: "award", blurb: "AMC 8/10/12, AIME, USAJMO, and USAMO past papers." },
  canada: { name: "Canada Competitions", tab: "Canada", icon: "leaf", blurb: "CEMC contests (Gauss, Euclid…), COMC, CJMO, and CMO." },
  ib: { name: "IB Math", tab: "IB", icon: "book", blurb: "Math AA and AI, SL and HL, plus IA resources." },
  ossd: { name: "OSSD Math", tab: "OSSD", icon: "cap", blurb: "Ontario high school math, from MTH1W to MCV4U." },
};

const NAV = [
  { href: "/", label: "Home", page: "home" },
  ...Object.entries(SECTIONS).map(([key, s]) => ({ href: `/resources.html?section=${key}`, label: s.tab, page: `section-${key}` })),
  { href: "/weekly.html", label: "Weekly Problem", page: "weekly" },
  { href: "/qa.html", label: "Q&A", page: "qa" },
];

export async function api(method, url, body) {
  const options = { method, headers: {} };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return data;
}

let mePromise = null;
export function getMe() {
  if (mePromise === null) {
    mePromise = api("GET", "/api/auth/me").then((d) => d.user).catch(() => null);
  }
  return mePromise;
}

export function formatSize(bytes) {
  if (bytes == null) return "";
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function formatDateTime(iso) {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

export function loginPrompt(action) {
  const next = encodeURIComponent(location.pathname + location.search);
  return el("p", { class: "login-prompt" },
    el("a", { href: `/login.html?next=${next}` }, "Log in"), " or ", el("a", { href: `/signup.html?next=${next}` }, "sign up"), ` to ${action}.`);
}

export function nextPage() {
  const next = new URLSearchParams(location.search).get("next");
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

function loginHref(page) {
  const here = location.pathname + location.search;
  return here === "/" ? page : `${page}?next=${encodeURIComponent(here)}`;
}

export async function renderHeader() {
  const header = document.getElementById("site-header");
  const current = header.dataset.page;
  const account = el("div", { class: "account" });
  header.className = "site-header";
  header.append(
    el("div", { class: "container" },
      el("a", { class: "logo", href: "/" }, el("span", { class: "logo-mark", "aria-hidden": "true" }, "Σ"), "MathInteract"),
      el("nav", { class: "nav", "aria-label": "Main" },
        NAV.map((item) =>
          el("a", { href: item.href, "aria-current": item.page === current ? "page" : null }, item.label)
        )
      ),
      account
    )
  );

  const me = await getMe();
  if (me) {
    account.append(el("a", { class: "username", href: "/account.html", title: "Your account" }, me.username));
    if (me.is_admin) {
      account.append(el("a", { class: "chip chip-accent chip-link", href: "/admin.html", title: "Admin page",
        "aria-current": current === "admin" ? "page" : null }, "Admin"));
    }
    account.append(el("button", { class: "btn btn-sm", type: "button", onclick: logOut }, "Log out"));
  } else if (current !== "login" && current !== "signup") {
    account.append(
      el("a", { href: loginHref("/login.html") }, "Log in"),
      el("a", { class: "btn btn-primary btn-sm", href: loginHref("/signup.html") }, "Sign up")
    );
  }
}

async function logOut() {
  await api("POST", "/api/auth/logout");
  location.reload();
}
