






from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.scrapers.base import Item

CMO_PAGE = "https://cms.math.ca/competitions/cmo/"
COMC_INDEX = "https://cms.math.ca/competitions/comc/"
YEAR = re.compile(r"(19[6-9]\d|20\d\d)")
KIND_WORDS = {"problems": "Problems", "solutions": "Solutions"}


def kind_of(link_text: str) -> str | None:
    text = link_text.lower()
    if "solution" in text:
        return "solutions"
    if "problem" in text or "exam" in text:
        return "problems"
    return None


def pdf_links(html: str, page_url: str):

    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        url = urljoin(page_url, a["href"])
        parts = urlsplit(url)
        if parts.netloc != "cms.math.ca" or not parts.path.lower().endswith(".pdf"):
            continue
        kind = kind_of(a.get_text(" "))
        if kind:
            yield url, parts.path.rsplit("/", 1)[-1].lower(), kind


def item(contest: str, year: int, kind: str, url: str) -> Item:
    return Item(section="canada", contest=contest, year=year, title=f"{year} {contest.upper()} {KIND_WORDS[kind]}",
                kind=kind, url=url, download=False)


def scrape_cmo(fetch) -> list[Item]:
    items = []
    for url, name, kind in pdf_links(fetch.text(CMO_PAGE), CMO_PAGE):
        year = YEAR.search(name)
        if year:
            contest = "cjmo" if "cjmo" in name or name.startswith("j") else "cmo"
            items.append(item(contest, int(year.group()), kind, url))
    return items


def scrape_comc(fetch) -> list[Item]:
    index = fetch.text(COMC_INDEX)
    years = sorted({int(y) for y in re.findall(r"/competitions/comc/comc(\d{4})/", index)})
    items = []
    for year in years:
        page = f"https://cms.math.ca/competitions/comc/comc{year}/"
        items += [item("comc", year, kind, url) for url, _, kind in pdf_links(fetch.text(page), page)]
    return items


def scrape(fetch) -> list[Item]:
    found: dict[str, Item] = {}
    for it in scrape_cmo(fetch) + scrape_comc(fetch):
        found.setdefault(it.url, it)
    return list(found.values())
