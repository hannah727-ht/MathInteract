












from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import quote

from app import weeks
from app.scrapers.base import Item

WIKI = "https://artofproblemsolving.com/wiki/index.php/"
SAVED_LINKS = Path(__file__).with_name("aops_links.json")



SCHEDULE = {
    "amc8": (["AMC 8"], ["Problems", "Answer Key"], (2, 10)),
    "amc10": (["AMC 10A", "AMC 10B"], ["Problems", "Answer Key"], (11, 25)),
    "amc12": (["AMC 12A", "AMC 12B"], ["Problems", "Answer Key"], (11, 25)),
    "aime": (["AIME I", "AIME II"], ["Problems", "Answer Key"], (2, 25)),
    "usajmo": (["USAJMO"], ["Problems"], (4, 5)),
    "usamo": (["USAMO"], ["Problems"], (4, 5)),
}
KINDS = {"Problems": "problems", "Answer Key": "answers"}


def page_url(title: str) -> str:
    return WIKI + quote(title.replace(" ", "_"))


def saved_items() -> list[Item]:
    links = json.loads(SAVED_LINKS.read_text())["links"]
    return [Item(section="us", contest=l["contest"], year=l["year"], title=l["title"], kind=l["kind"],
                 url=l["url"], download=False) for l in links]


def newer_items(saved: list[Item], today: date) -> list[Item]:

    items = []
    for contest, (tests, suffixes, (month, day)) in SCHEDULE.items():
        last_saved = max((i.year for i in saved if i.contest == contest), default=today.year - 1)
        for year in range(last_saved + 1, today.year + 1):
            if today < date(year, month, day):
                continue
            for test in tests:
                for suffix in suffixes:
                    title = f"{year} {test} {suffix}"
                    items.append(Item(section="us", contest=contest, year=year, title=title, kind=KINDS[suffix],
                                      url=page_url(title), download=False))
    return items


def scrape(fetch=None) -> list[Item]:

    saved = saved_items()
    return saved + newer_items(saved, weeks.today())
