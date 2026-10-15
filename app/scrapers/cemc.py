









from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app import catalog
from app.scrapers.base import Item

BASE = "https://cemc.uwaterloo.ca"
LIST_PAGE = BASE + "/resources/past-contests"

CATEGORIES = {"gauss": 13, "pcf": 14, "fgh": 25, "euclid": 24, "csimc": 23}


COLUMNS = {
    "view-nothing-table-column": ("problems", "Contest"),
    "view-nothing-2-table-column": ("solutions", "Solutions"),
    "view-nothing-1-table-column": ("results", "Results"),
}
MAX_PAGES = 30
PAGE_SIZE = 10


def cell_text(row, header: str) -> str:
    cell = row.find("td", headers=header)
    return " ".join(cell.get_text(" ").split()) if cell else ""


def parse_page(html: str, contest: str) -> list[Item]:
    rows = []
    for row in BeautifulSoup(html, "html.parser").select("tbody tr"):
        name = cell_text(row, "view-title-table-column")
        year_match = re.search(r"\d{4}", cell_text(row, "view-field-year-term-table-column"))
        if not name or not year_match:
            continue
        pdfs = {}
        for header in COLUMNS:
            cell = row.find("td", headers=header)
            link = cell.find("a", href=re.compile(r"\.pdf$", re.I)) if cell else None
            if link:
                pdfs[header] = urljoin(BASE, link["href"])
        rows.append((name, int(year_match.group()), cell_text(row, "view-field-grades-table-column"), pdfs))

    items: dict[str, Item] = {}
    for name, year, grade, pdfs in rows:
        for header, url in pdfs.items():
            kind, word = COLUMNS[header]
            label = row_label(rows, name, year, grade, url, contest)
            title = f"{year} {label}" if word == "Contest" and label.endswith("Contest") else f"{year} {label} {word}"
            items.setdefault(url, Item(section="canada", contest=contest, year=year, title=title,
                                       kind=kind, url=url, download=True))
    return list(items.values())


def row_label(rows, name: str, year: int, grade: str, url: str, contest: str) -> str:







    sharing = [r for r in rows if url in r[3].values()]
    if len({r[0] for r in sharing}) > 1:
        return catalog.SECTIONS["canada"]["contests"][contest]
    same_name = [r for r in rows if r[0] == name and r[1] == year]
    if len(same_name) > 1 and len(sharing) == 1 and grade:
        return f"{name} Grade {grade}"
    return name


def year_filters(html: str) -> list[str]:

    options = BeautifulSoup(html, "html.parser").select("select[name=academic_year] option")
    return [o["value"] for o in options if o.get("value") and o["value"] != "All"]


def row_count(html: str) -> int:
    return len(BeautifulSoup(html, "html.parser").select("tbody tr"))


def scrape(fetch) -> list[Item]:
    found: dict[str, Item] = {}
    for contest, category in CATEGORIES.items():
        first = fetch.text(LIST_PAGE, {"contest_category": category, "page": 0})
        years = year_filters(first)



        queries = [{"contest_category": category, "academic_year": y} for y in years] or [{"contest_category": category}]
        for query in queries:
            for page in range(MAX_PAGES):
                html = first if not years and page == 0 else fetch.text(LIST_PAGE, {**query, "page": page})
                new = [item for item in parse_page(html, contest) if item.url not in found]
                found.update((item.url, item) for item in new)
                if not new or row_count(html) < PAGE_SIZE:
                    break
    return list(found.values())
