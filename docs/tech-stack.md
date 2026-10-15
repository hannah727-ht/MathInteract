# Tech Stack & Architecture

## 1. Overview

```
Browser (HTML + JS + CSS)
   │  fetch()  (session cookie)
   ▼
FastAPI server (Python)  ──►  SQLite database (data/mathinteract.db)
   │                     ──►  Uploaded files (data/uploads/)
   └──► Scrapers (daily task + "Refresh now") ──► AoPS Wiki API, CEMC, CMS
                                                  (CEMC PDFs saved to data/uploads/resources/)
```

The FastAPI server serves the web pages as static files (`static/` mounted at `/`, mounted last so `/api` wins) and answers the JSON API. There is no frontend build step. Page state lives in the URL (e.g. `/resources.html?section=us&contest=amc10`), so links can be shared and Back works.

## 2. Choices

| Area | Choice | Why |
|---|---|---|
| Language (backend) | Python 3.13 | Same language as the scrapers; same as PartLens |
| Web framework | FastAPI + Uvicorn | Same as PartLens; automatic API docs at `/docs` |
| Database | SQLite through SQLAlchemy 2.0 | One file, no server to run; can switch to PostgreSQL at deployment if the host needs it |
| Passwords | `pwdlib` with Argon2 | Current FastAPI recommendation |
| Login state | Starlette `SessionMiddleware` (signed, HttpOnly, SameSite=Lax cookie holding the user id) | Simple, no token handling in JS |
| Accounts | Username + password only, no email (user decision 2026-09-29) | Simplest for students, no personal data, no mailbox to run |
| Admin tools | `scripts/manage.py` (make-admin, remove-admin, reset-password, list-users) | Only people with server access can grant admin rights |
| Settings | `.env` file read by `python-dotenv` (see `.env.example`) | Secrets stay out of code |
| Scrapers | Python's `urllib` + `beautifulsoup4` + `truststore`; a background thread started with the server | CEMC's web host refuses the `requests` library (same User-Agent works with urllib); `truststore` uses the computer's certificate store, so it works behind school networks that inspect HTTPS |
| Math | KaTeX 0.19.0 (MIT) in `static/vendor/katex/` (minified JS/CSS, auto-render, woff2 fonts) | Works offline, no CDN (same rule as PartLens) |
| Post images | Pillow checks the format (JPEG/PNG/WEBP), pixel count, and that the file is not damaged | Never trust the file name or the browser's content type |
| Frontend | Plain HTML + vanilla JavaScript (ES modules) | No build tools |
| Styling | Plain CSS in `static/css/app.css`, colors as CSS variables | Beginner-readable |
| Tests | `pytest` + FastAPI `TestClient` (needs `httpx2`); `playwright` (installed Chrome) for browser checks | Same as PartLens |
| Env | `python3 -m venv .venv` + pinned `requirements.txt` | Isolated, reproducible |

Site time zone: **America/Toronto** (used for Weekly Problem weeks).

## 3. Folder layout

```
MathInteract/
├── app/
│   ├── main.py            # FastAPI app: middleware, routers, static files
│   ├── config.py          # settings from environment / .env
│   ├── db.py              # engine, session, Base, get_db dependency
│   ├── models.py          # SQLAlchemy tables
│   ├── security.py        # password hashing, sign-up limit, current-user dependencies
│   ├── catalog.py         # sections, contests/courses, resource types, sources
│   ├── scrapers/
│   │   ├── base.py        # Fetcher (polite web client: robots.txt, 1.5 s pause, own User-Agent) + Item
│   │   ├── aops.py        # US contests: saved AoPS links + standard names for newer contests (no network)
│   │   ├── aops_links.json # 471 AoPS pages checked on 2026-10-01
│   │   ├── cemc.py        # CEMC past-contests table, one year at a time (PDFs downloaded)
│   │   └── cms.py         # CMO/CJMO page + COMC yearly pages (links)
│   ├── sync.py            # runs scrapers, saves resources, daily scheduler
│   ├── weeks.py           # Toronto-time weeks (Monday start) for the Weekly Problem
│   ├── posts.py           # shared post rules: text length, up to 4 images, JSON helpers
│   ├── accounts.py        # admin account changes (set admin, reset password), shared with scripts/manage.py
│   ├── analytics.py       # traffic stats: page keys, visitor codes (no IPs), daily counts, 90-day clean-up
│   └── routers/
│       ├── auth.py        # /api/auth/*
│       ├── resources.py   # /api/catalog, /api/resources/*
│       ├── sync.py        # /api/sync/* (status, Refresh now)
│       ├── images.py      # /api/images (post images)
│       ├── weekly.py      # /api/weekly/*, /api/comments/*
│       ├── qa.py          # /api/questions/*, /api/answers/*
│       └── admin.py       # /api/admin/* (overview, users)
├── static/
│   ├── index.html         # Home
│   ├── login.html, signup.html, account.html
│   ├── resources.html, weekly.html, qa.html, ask.html, question.html, admin.html
│   ├── css/app.css
│   ├── js/common.js       # header/nav, el() DOM builder, API helpers, current user
│   ├── js/<page>.js       # one script per page
│   ├── js/math.js         # shows text + LaTeX (KaTeX) + images
│   ├── js/composer.js     # writing box: text, "Add image", live formula preview
│   ├── js/questions.js    # one row of a question list (Q&A page and Home)
│   └── vendor/katex/
├── scripts/
│   └── manage.py          # admin tools run on the server
├── data/                  # mathinteract.db + uploads/ (NOT committed)
├── tests/                 # fixtures/ = trimmed copies of the real scraped pages; fake_sites.py replaces the network
├── docs/  devlog/
├── .env.example
├── requirements.txt
└── pyproject.toml         # pytest settings
```

## 4. Data model

| Table | Columns | Milestone |
|---|---|---|
| `users` | id, username (unique index on `lower(username)`), password_hash, is_admin, created_at | M1 |
| `resources` | id, section, contest, year (nullable), title, kind, source (`upload`/`aops`/`cemc`/`cms`), url (scraped, unique), stored_name + original_name + size (uploaded), uploaded_by_id, created_at | M2 |
| `scrape_runs` | source (pk: `aops`/`cemc`/`cms`), status (`never`/`running`/`ok`/`error`), message, found, added, started_at, finished_at | M3 |
| `images` | id, owner_id, stored_name, width, height, size, created_at (stored in `data/uploads/images/`) | M4 |
| `weekly_problems` | id, week_start (Monday, unique), title, body, solution, image_ids (JSON), solution_image_ids (JSON), author_id, created_at, updated_at | M4 |
| `comments` | id, problem_id, user_id, body, image_ids (JSON), created_at, updated_at (set when edited) | M4 |
| `questions` | id, title, body, topic (`catalog.QA_TOPICS`), image_ids (JSON), user_id, accepted_answer_id, created_at, updated_at | M5 |
| `answers` | id, question_id, body, image_ids (JSON), user_id, created_at, updated_at | M5 |
| `page_views` | day + page (pk), views | M8 |
| `visitors` | day + code (pk) — code = first 16 hex of sha256(daily salt, address, browser); no IP stored | M8 |
| `active_users` | day + user_id (pk) | M8 |
| `resource_opens` | day + resource_id (pk), opens | M8 |
| `analytics_salts` | day (pk), salt — only today's row is kept | M8 |

Tables are created with `Base.metadata.create_all()` on startup. Admin rights are only granted by `scripts/manage.py make-admin` (and the Admin page in M6).

## 5. API contract (M1)

All bodies are JSON. Errors return `{"detail": "<message>"}`.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | — | `{status: "ok"}` |
| GET | `/api/auth/me` | — | `{user: {id, username, is_admin} \| null}` |
| POST | `/api/auth/signup` | `{username, password}` | 201 `{user}` and logged in. 409 username taken (any case), 422 invalid input, 429 more than `SIGNUPS_PER_HOUR` sign-ups from this address |
| POST | `/api/auth/login` | `{username, password}` (any case) | `{user}`. 401 "Wrong username or password." |
| POST | `/api/auth/logout` | — | `{ok: true}` |
| POST | `/api/auth/password` | `{current_password, new_password}` | `{ok: true}`. 401 not logged in, 400 wrong current password, 422 new one too short |

Input rules: username 3–20 characters (letters, digits, `_`, `-`); password 8–128 characters.

Admin command line (run on the server, from the project root):
```bash
.venv/bin/python scripts/manage.py list-users
.venv/bin/python scripts/manage.py make-admin <username>
.venv/bin/python scripts/manage.py remove-admin <username>     # refuses to remove the last admin
.venv/bin/python scripts/manage.py reset-password <username>   # prints a temporary password
```

### Resources (M2)

Sections, contests/courses, types, and sources are defined in `app/catalog.py` (the only place to add one).

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/catalog` | — | `{sections: {us: {name, blurb, source_note, links, contests:[{key, name}]}, …}, kinds:[{key, name}], sources, max_upload_mb}` |
| GET | `/api/resources` | `?section=us[&contest=amc10]` | resource list, newest year first (undated last), then by type. 404 unknown section/contest, 422 no section |
| GET | `/api/resources/recent` | `?limit=6` (1–20) | newest resources across sections (Home) |
| GET | `/api/resources/{id}/file` | — | the uploaded file under its original name; PDFs/images `inline`, Word `attachment`; `nosniff`. 404 |
| POST | `/api/resources` | multipart: `section, contest, kind, year?, title?, file` | 201 resource. 401/403 not admin, 422 bad field or empty file, 415 type not allowed or first bytes don't match, 413 over `MAX_UPLOAD_MB` |
| DELETE | `/api/resources/{id}` | — | `{ok: true}` (file removed from disk). 401/403 not admin, 404, 400 scraped link |

A resource in JSON: `{id, section, section_name, contest, contest_name, year, title, kind, source, href, file_type ("PDF"… or "Link"), size, created_at}`. `href` is the download route for uploads and the official URL for scraped links.

Allowed uploads: PDF, PNG, JPG/JPEG, WEBP, DOC, DOCX, up to `MAX_UPLOAD_MB` (25). Files are stored as `data/uploads/resources/<random hex>.<ext>`.

### Sync (M3)

| Method | Path | Returns |
|---|---|---|
| GET | `/api/sync/{section}` | `{sources: [{source, name, status, message, found, added, started_at, finished_at}]}` (empty for IB/OSSD). 404 unknown section |
| POST | `/api/sync/{section}` | 202 `{started: ["cemc", "cms"]}` — runs that section's scrapers in the background (admins). 400 IB/OSSD, 401/403, 404 |

How a run works (`app/sync.py`): the scraper returns `Item`s → new URLs are saved (CEMC PDFs downloaded first, checked to start with `%PDF-`, max 50 MB) → known URLs get their title/year/type refreshed → nothing is ever deleted. One failed download is skipped and retried next run. Automatic runs: a thread checks every 30 min; a source is due `SYNC_INTERVAL_HOURS` (24) after a good run or 1 h after a failed one. A run cut off by a server restart is marked "error" at the next start.

Scraped resources: `href` is our download route when we store a copy (CEMC), otherwise the official URL; `official_url` is always the original address.

### Weekly Problem (M4)

Weeks run Monday–Sunday, Toronto time (`app/weeks.py`). A problem's status is `scheduled` (future), `current`, or `past`.

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/images` | multipart `file` | 201 `{id, url, width, height}`. Logged in. 415 not JPG/PNG/WEBP or damaged, 413 over 5 MB or 40 MP, 422 empty |
| GET | `/api/images/{id}` | — | the image (`nosniff`, cached for a year). 404 |
| GET | `/api/weekly/current` | — | `{week_start, problem: detail \| null}` |
| GET | `/api/weekly` | — | `{current_week, problems: [summary]}` newest first; scheduled ones only for admins |
| GET | `/api/weekly/{id}` | — | detail. 404 if missing or scheduled (non-admins) |
| POST | `/api/weekly` | `{week_start, title, body, solution?, image_ids?, solution_image_ids?}` | 201 detail (week_start moved to its Monday). Admin. 409 week taken, 422 bad input |
| PUT | `/api/weekly/{id}` | same | detail. Admin. The week can change only while scheduled, never to a past week |
| DELETE | `/api/weekly/{id}` | — | `{ok}`. Admin, scheduled problems only (409 otherwise) |
| POST | `/api/weekly/{id}/comments` | `{body, image_ids?}` | 201 comment. Logged in; not on scheduled problems |
| PUT | `/api/comments/{id}` | `{body, image_ids?}` | comment. Author only (403) |
| DELETE | `/api/comments/{id}` | — | `{ok}`. Admin only |

Summary: `{id, title, week_start, status, comment_count}`. Detail adds `body, images, week_end, solution_release, solution_released, solution (null until released, except for admins), solution_images, comments`. Comment: `{id, body, images, user: {id, username, is_admin}, created_at, edited}`.

Post rules (`app/posts.py`): text is trimmed; title ≤ 200, problem/solution ≤ 20,000, comment ≤ 10,000 characters; at most 4 images, each owned by the poster (or already on the post).

### Q&A (M5)

Topics: `general`, `us`, `canada`, `ib`, `ossd` (`catalog.QA_TOPICS`).

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/questions` | `?topic=&q=&page=1&limit=20` (limit ≤ 50) | `{topics, total, page, pages, questions: [summary]}` newest first; `q` matches title or text (case-insensitive; `%`/`_` literal). 422 bad topic |
| GET | `/api/questions/{id}` | — | detail (answers: accepted first, then oldest → newest). 404 |
| POST | `/api/questions` | `{title, body, topic, image_ids?}` | 201 detail. Logged in. 422 bad input |
| PUT | `/api/questions/{id}` | same | detail. Asker only (403) |
| DELETE | `/api/questions/{id}` | — | `{ok}` (answers deleted too). Admin only |
| POST | `/api/questions/{id}/accept` | `{answer_id \| null}` | detail. Asker only; the answer must belong to the question (422); null = undo |
| POST | `/api/questions/{id}/answers` | `{body, image_ids?}` | 201 answer. Logged in |
| PUT | `/api/answers/{id}` | `{body, image_ids?}` | answer. Author only (403) |
| DELETE | `/api/answers/{id}` | — | `{ok}`; clears "accepted" if it was. Admin only |

Summary: `{id, title, topic, user, created_at, answer_count, solved}`. Detail adds `body, images, edited, accepted_answer_id, answers`. Answer: `{id, body, images, user, created_at, edited, accepted}`. Limits: title ≤ 200, question/answer ≤ 20,000 characters, ≤ 4 images.

### Traffic stats (M8)

A middleware counts every successful (200/304) GET of a page (`analytics.page_key()`: `home`, `resources/<section>`, `weekly[/<id>]`, `qa`, `ask`, `question/<id>`, `login`, `signup`, `account`; the Admin page, files, and API calls aren't counted). Admins' visits and bot User-Agents are skipped. Resource links point to `/api/resources/{id}/open`, which counts and redirects (302) to the stored file or the official page. A new day's first count deletes older salts and stats older than 90 days.

| Method | Path | Returns |
|---|---|---|
| GET | `/api/resources/{id}/open` | 302 to `href`. 404 |
| GET | `/api/admin/traffic?days=30` (7–90) | `{days: [{day, views, visitors, active_users}], totals: {views, average_visitors, logged_in_users, today_views}, top_pages: [{name, views}], top_resources: [{id, title, opens, where}], top_questions, top_weekly: [{id, title, views}]}`. Admin only |

### Admin (M6)

All need an admin (401 not logged in, 403 not admin).

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/admin/overview` | — | `{counts: {users, admins, questions, answers, comments, weekly_problems, resources}, resources_by_source, disk: {files, database} (bytes), scrapers: [source status incl. section]}` |
| GET | `/api/admin/users` | `?q=&page=` | `{total, page, pages, users: [{id, username, is_admin, created_at, posts}]}` newest first, 20 per page; `q` = part of the username |
| POST | `/api/admin/users/{id}/admin` | `{is_admin}` | user. 409 when removing the last admin, 404 |
| POST | `/api/admin/users/{id}/reset-password` | — | `{username, temporary_password}` (12 random characters, shown once). 404 |

`posts` = questions + answers + comments. A demoted admin loses access on their next request (the role is read from the database every time).

## 6. Running locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env            # then set SECRET_KEY
./scripts/start.sh                # = .venv/bin/uvicorn app.main:app --reload --port 8001 (8000 is used by PartLens)
# keep that terminal open while using the site; Ctrl+C stops it
# open http://127.0.0.1:8001  (API docs: /docs)

.venv/bin/pytest                # run all tests
```

## 7. Deployment (Railway)

Hosted on **Railway**, Hobby plan (US$5/month including $5 of usage; this app uses about $2–3). Changed from Render on 2026-10-11 to save money. Railway builds from the GitHub repo and redeploys on every push to `main`.

| Piece | Where | Value / why |
|---|---|---|
| Python | `.python-version` | 3.13 |
| Start | `railway.json` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, one replica (SQLite and the in-memory rate limits assume a single server), health check `/api/health` |
| Volume | Railway dashboard: attach to the service, mount path `/data` | database, uploads, and CEMC PDFs (~0.45 GB) survive redeploys |
| `SECRET_KEY` | Variables | long random value made on the owner's computer; the app refuses to start with HTTPS_ONLY=true and no key |
| `HTTPS_ONLY` | Variables | true — login cookie only over HTTPS |
| `PROXY_HOPS` | Variables | **2** — Railway's header is `<visitor>, <Railway edge>`, and Railway drops any X-Forwarded-For the visitor sends (checked 2026-10-11 with a temporary echo endpoint, since removed) |
| `DATABASE_URL` | Variables | `sqlite:////data/mathinteract.db` |
| `UPLOAD_DIR` | Variables | `/data/uploads` |
| `AUTO_SYNC` | Variables | true — off unless set, so a half-configured first deploy doesn't start downloading |
| `ADMIN_BOOTSTRAP` | Variables, **temporary** | usernames made admins at startup (only accounts that already exist). Set it after signing up, wait for the redeploy, then delete it |
| Region | Service settings | US East (closest to Toronto) |

After the first deploy:
1. `PROXY_HOPS` was checked on 2026-10-11 with a temporary endpoint that echoed the address the app sees (removed afterwards): with 2 it is the visitor's real address.
2. Sign up as the owner on the live site, then add the variable `ADMIN_BOOTSTRAP=<username>`; after the redeploy the account is an admin — delete the variable. (Later admins are added on the Admin page.)
3. Public address: https://mathinteract-production.up.railway.app (Settings → Networking → Generate Domain; the name can be edited there). An own domain is optional (not bought, user decision 2026-10-11): add it under Custom Domain, create the CNAME **and** TXT records Railway shows, keep Cloudflare's proxy off ("DNS only") so `PROXY_HOPS=2` stays right. Railway issues the HTTPS certificate.
