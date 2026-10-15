# MathInteract

MathInteract is a small website for students to find math resources, try weekly problems, and discuss questions with other students.

Live site: [mathinteract-production.up.railway.app](https://mathinteract-production.up.railway.app)

## Features

- Past papers and resources for US competitions, Canadian competitions, IB, and OSSD courses
- A weekly problem with comments and delayed solutions
- A question and answer section with topics and accepted answers
- Username and password accounts
- Image uploads and LaTeX formulas with KaTeX
- Admin tools for resources, users, weekly problems, and traffic statistics
- Automatic resource updates from CEMC and CMS

## Built with

- Python 3.13
- FastAPI and Uvicorn
- SQLAlchemy and SQLite
- HTML, CSS, and JavaScript
- KaTeX
- pytest

## Project folders

- `app` contains the FastAPI server, database models, routes, and scrapers.
- `static` contains the pages, styles, and browser JavaScript.
- `tests` contains the automated tests and scraper fixtures.
- `scripts` contains the local start script and account tools.
- `docs` contains the project requirements and technical notes.

Local databases, uploaded files, and `.env` settings are not committed to Git.
