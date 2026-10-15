# Product Requirements

> Status: agreed with the user on 2026-09-28; accounts changed to username + password on 2026-09-29; scraped papers stored on our site where the licence allows (2026-10-01). Update this file whenever a requirement changes.

## 1. Goal
MathInteract is a website for learning and discussing math. Students can find past papers for math competitions and school programs in one place, try a new problem every week, and ask questions.

## 2. Users and roles
- **Visitor** (not logged in): can browse everything (resources, Weekly Problem, Q&A).
- **User** (logged in): can also comment on the Weekly Problem, ask questions, answer questions, and edit their own posts.
- **Admin**: can also upload and delete uploaded resources, run the scrapers on demand, post Weekly Problems, delete any post, and make other users admins.
  - Admins are set with a command run on the server (`scripts/manage.py make-admin <username>`), so nobody can grab admin rights by signing up with a certain name.
  - Admins can add more admins later from the Admin page (M6).

## 3. Accounts
Target: a small community site (classmates, clubs; tens to hundreds of users). Decision on 2026-09-29: **no email at all**.
- Sign up with a **username + password** (typed twice). Usernames are unique, ignoring upper/lower case ("Amy" = "amy"). The new account is logged in right away.
- Log in with username + password. Log out.
- Account page: change your own password (needs the current one).
- Forgot password: ask an admin, who sets a temporary password (command now, Admin page in M6).
- At most 30 new accounts per network address per hour, to stop bulk spam accounts (raised from 5 on 2026-10-11: a whole school shares one address).
- Wrong passwords: 10 per account in 15 minutes locks that account's login for the rest of the 15 minutes; 100 per network address in 15 minutes locks logins from that address. One person's typos never block others.
- Out of scope: email, verification codes, self-service password reset, banning users, social login.

## 4. Pages

All pages share a top navigation bar: **Home · US · Canada · IB · OSSD · Weekly Problem · Q&A**, plus **Log in / Sign up** or the username and **Log out** on the right.

### 4.1 Home
- Entry cards: US Competitions, Canada Competitions, IB, OSSD, Weekly Problem, Q&A.
- Live previews: this week's problem, latest questions, recently added resources.

### 4.2 Resource sections (US, Canada, IB, OSSD)
Each section lists its contests or courses. Inside one, resources are grouped by year and labeled by type: Problems, Solutions, Answer key, Results, Notes, Other.

| Section | Contests / courses | Source |
|---|---|---|
| US | AMC 8, AMC 10, AMC 12, AIME, USAJMO, USAMO | Links to AoPS Wiki pages + admin uploads. AoPS blocks bots since October 2026, so the links come from a list checked on 2026-10-01 plus AoPS's standard page names for newer contests (added after each contest date) |
| Canada | Gauss, Pascal/Cayley/Fermat, Fryer/Galois/Hypatia, Euclid, CSIMC (CEMC); COMC, CJMO, CMO (CMS) | Scraped from cemc.uwaterloo.ca and cms.math.ca + admin uploads |
| IB | Math AA SL, AA HL, AI SL, AI HL, IA | Admin uploads only, plus links to official IB sites (IB papers are copyrighted and sold by the IBO) |
| OSSD | MTH1W, MPM2D, MCR3U, MCF3M, MHF4U, MCV4U, MDM4U | Admin uploads only, plus links to the official Ontario curriculum (no public provincial exams) |

- How scraped papers open depends on each source's licence (user decision 2026-10-01: "store them on our site, not make users find them"):

  | Source | Licence | What we do |
  |---|---|---|
  | CEMC | CC BY-NC 4.0 (non-commercial reuse allowed with credit; never charge) | **Download the PDFs and store them on our site**; credit the CEMC and link the licence |
  | CMS (COMC, CJMO, CMO) | personal copies only | Link straight to the official PDF (one click opens the paper) |
  | AoPS Wiki (AMC, AIME, USA(J)MO) | problems © MAA; AoPS has no PDFs | Link straight to that test's Problems / Answer Key page |

  If the CMS gives permission later, its papers can switch to stored copies.
- Scrapers run **automatically once a day**, and admins have a **Refresh now** button. The page shows when each section was last synced.
- Admins upload files (PDF, images, Word) with contest/course, year, type, and title. Admins can delete uploaded files.

### 4.3 Weekly Problem
- One problem per week (weeks start Monday, Toronto time). Only admins post problems; they can schedule future weeks in advance. Visitors never see a future week's problem.
- Logged-in users post comments under the problem (also under past weeks' problems).
- **Spoiler protection** (user decision 2026-10-01): this week's discussion is folded behind a "Show discussion (N comments)" button; past weeks' discussions are shown open. The comment box is always visible to logged-in users.
- The official solution becomes visible automatically when the next week begins; until then the page says when it will appear.
- If no problem is scheduled for this week, the page says "No problem this week yet" and links to the archive.
- An archive lists past weeks' problems, each with its comments and solution.
- Admins can edit a problem (and its solution) at any time, and delete a problem only before its week starts (so no discussion is lost).

### 4.4 Q&A
- Logged-in users ask questions (title + body + topic: General, US, Canada, IB, OSSD); others answer (askers may answer too).
- The list shows the newest questions first, 20 per page, each with its topic, asker, date, number of answers, and a "Solved" mark once an answer is accepted.
- Filter by topic and search by text (matches the title and the question text).
- The asker can accept one answer as the best answer, change it, or undo it. The accepted answer is shown first, marked "Accepted answer".
- Authors edit their own questions and answers; admins delete any question (with its answers) or answer.
- Home shows the 5 latest questions.
- Out of scope: votes/likes.

### 4.5 Admin
An Admin page (`admin.html`), reached from the orange "Admin" label in the header. Only admins can open it.
- **Overview**: number of users, questions, answers, comments, weekly problems, and resources; disk space used by files (the hosting disk is 2 GB).
- **Scrapers**: status of each scraper (last sync, papers, problems) with Refresh now per section.
- **Users**: list with search (20 per page) showing username, joined date, role, and number of posts.
  - Make a user an admin or remove admin rights. The last admin can't be removed.
  - Reset a user's password to a temporary one, shown once on screen for the admin to pass on privately; the user then changes it on their Account page.
- (Uploads, Refresh now, and Weekly Problem posting also stay on their own pages.)

### 4.6 Traffic stats (added 2026-10-11, user request)
Counted by our own server — no third-party analytics, no tracking cookies.
- **What**: page views per page per day; visitors per day (estimate); logged-in users per day; opens of each resource (including AoPS/CMS links, which now pass through our site on the way out); views of each question and weekly problem.
- **Not counted**: admins' own visits, bots and scripts (by their User-Agent), API calls.
- **Privacy**: IP addresses are never stored. A visitor is counted with a code made from the address, the browser, and a random value that changes every day; old daily values are deleted, so a code can't be traced back or followed across days. All stats older than 90 days are deleted.
- **Shown** on the Admin page, "Traffic": last 30 days of daily views and visitors, totals, and top pages, resources, questions, and weekly problems.

## 5. Post format
- Problems, comments, questions, and answers are **plain text with LaTeX**: `$...$` inline and `$$...$$` display math, rendered with KaTeX. No Markdown.
- Posts can have **attached images** (upload button), shown below the text: at most 4 per post, JPG/PNG/WEBP, up to 5 MB each.
- While writing, a live preview shows how the text and formulas will look.
- Authors can edit their own posts. Admins can delete any post.

## 6. Non-functional
- UI language: English. Desktop browsers only (no phone layout needed).
- Simple, clean design with **orange** as the primary color (see [design-guidelines.md](design-guidelines.md)).
- **Open to everyone on the internet** (user decision 2026-10-08; on 2026-10-09 the user chose to finish the remaining features — Q&A and the Admin page — before launching): hosted on **Railway** (Hobby plan, US$5/month, paid by the user; chosen on 2026-10-11 over Render at ~$7.5 to save money), deployed from the GitHub repo. Address: **https://mathinteract-production.up.railway.app** (free, HTTPS). No own domain for now (user decision 2026-10-11) — it can be added later in Railway (Settings → Networking → Custom Domain; Cloudflare or Namecheap, "DNS only"); `mathinteract.org` was still free on 2026-10-11.
- **Always free.** The CEMC licence forbids charging for access to its papers, so the site never charges users.
- Site name: MathInteract (temporary).

## 7. Out of scope (for now)
Email and verification codes, votes/likes, banning users, Markdown, phone layout, MATHCOUNTS/HMMT/CTMC, scraping IB or OSSD papers.
