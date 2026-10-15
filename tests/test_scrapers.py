

from collections import Counter
from datetime import date

from app.scrapers import aops, cemc, cms
from tests.fake_sites import FakeFetcher


def by_title(items):
    return {i.title: i for i in items}


def test_aops_uses_saved_links_without_the_network():
    items = aops.scrape(None)
    titles = by_title(items)
    assert len(items) >= 471 and len(titles) == len(items)
    item = titles["2025 AIME II Problems"]
    assert (item.section, item.contest, item.year, item.kind) == ("us", "aime", 2025, "problems")
    assert item.url == "https://artofproblemsolving.com/wiki/index.php/2025_AIME_II_Problems"
    assert titles["2024 AMC 10A Answer Key"].kind == "answers"
    assert not any(i.download for i in items)


def test_aops_adds_newer_contests_after_their_dates():
    saved = aops.saved_items()
    before = {i.title for i in aops.newer_items(saved, date(2026, 11, 24))}
    after = {i.title for i in aops.newer_items(saved, date(2026, 11, 25))}
    assert before == set()
    assert after == {f"2026 AMC {n}{v} {s}" for n in (10, 12) for v in "AB" for s in ("Problems", "Answer Key")}
    spring = {i.title for i in aops.newer_items(saved, date(2027, 4, 5))}
    assert {"2027 AMC 8 Problems", "2027 AIME I Answer Key", "2027 AIME II Problems", "2027 USAJMO Problems", "2027 USAMO Problems"} <= spring
    assert "2027 AMC 10A Problems" not in spring
    assert aops.page_url("2026 AMC 10A Problems") == "https://artofproblemsolving.com/wiki/index.php/2026_AMC_10A_Problems"


def test_cemc_reads_the_table_and_keeps_copies():
    items = cemc.scrape(FakeFetcher())
    titles = by_title(items)

    assert {"2026 Gauss Grade 7 Contest", "2026 Gauss Grade 8 Contest", "2026 Gauss Solutions"} <= set(titles)
    assert titles["2026 Gauss Grade 7 Contest"].url == "https://cemc.uwaterloo.ca/sites/default/files/documents/2026/2026Gauss7%28E%29.pdf"

    assert "2025 Canadian Intermediate Mathematics Contest" in titles
    assert "2025 CSIMC Results" in titles
    assert not any("Contest Contest" in t for t in titles)
    assert all(i.download and i.section == "canada" and i.url.endswith(".pdf") for i in items)
    assert Counter(i.title for i in items).most_common(1)[0][1] == 1
    assert {i.kind for i in items} == {"problems", "solutions", "results"}


def test_cemc_without_year_filter_reads_one_short_page():
    fetch = FakeFetcher()
    cemc.scrape(fetch)
    pages = [p["page"] for _, p in fetch.requests if p["contest_category"] == 13]
    assert pages == [0]


def test_cemc_asks_one_year_at_a_time_when_it_can():

    fetch = FakeFetcher(cemc_year_filter=True)
    titles = {i.title for i in cemc.scrape(fetch) if i.contest == "pcf"}
    assert {"2023 Fermat Contest", "2023 Fermat Solutions", "2020 Pascal Contest", "2020 Cayley Solutions"} <= titles
    pcf = [p for _, p in fetch.requests if p["contest_category"] == 14]
    assert [p.get("academic_year") for p in pcf] == [None, "31", "34"]


def test_cms_cmo_cjmo_and_comc():
    items = cms.scrape(FakeFetcher())
    titles = by_title(items)
    assert titles["2026 CMO Problems"].url == "https://cms.math.ca/wp-content/uploads/2026/03/CMO2026-problems.pdf"
    assert titles["2020 CJMO Problems"].url.endswith("/jexam2020.pdf")
    assert titles["1969 CMO Problems"].url.endswith("/exam1969.pdf")
    assert titles["2023 COMC Problems"].url.endswith("COMC2023-exam.pdf.pdf")
    assert "2026 COMC Problems" not in titles
    assert not any("imo-official" in i.url for i in items)
    assert len(items) == len({i.url for i in items})
    assert Counter(i.title for i in items).most_common(1)[0][1] == 1
    assert not any(i.download for i in items)
