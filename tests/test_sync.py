

from datetime import timedelta

from sqlalchemy import select

from app import sync
from app.config import settings
from app.db import SessionLocal
from app.models import Resource, ScrapeRun, utcnow
from tests.conftest import sign_up, sign_up_admin
from tests.fake_sites import FakeFetcher


def resources(source):
    with SessionLocal() as db:
        return db.scalars(select(Resource).where(Resource.source == source)).all()


def run_status(source):
    with SessionLocal() as db:
        return db.get(ScrapeRun, source)


def test_cemc_papers_are_stored_on_our_site(client):
    fetch = FakeFetcher()
    sync.sync_source("cemc", fetch)
    saved = resources("cemc")
    assert len(saved) == len(fetch.downloads) > 0
    run = run_status("cemc")
    assert (run.status, run.found, run.added, run.message) == ("ok", len(saved), len(saved), None)

    item = next(r for r in client.get("/api/resources?section=canada&contest=gauss").json() if r["title"] == "2026 Gauss Grade 7 Contest")
    assert item["href"] == f"/api/resources/{item['id']}/file"
    assert item["official_url"].startswith("https://cemc.uwaterloo.ca/") and item["file_type"] == "PDF"
    file = client.get(item["href"])
    assert file.status_code == 200 and file.content.startswith(b"%PDF-")
    assert file.headers["content-disposition"].startswith("inline")


def test_link_only_sources_are_not_downloaded(client):
    fetch = FakeFetcher()
    sync.sync_source("aops", fetch)
    sync.sync_source("cms", fetch)
    assert fetch.downloads == []
    item = client.get("/api/resources?section=us&contest=aime").json()[0]
    assert item["href"].startswith("https://artofproblemsolving.com/") and item["file_type"] == "Link"


def test_second_run_adds_nothing_and_refreshes_titles(client):
    sync.sync_source("cms", FakeFetcher())
    count = len(resources("cms"))
    with SessionLocal() as db:
        db.scalar(select(Resource).where(Resource.source == "cms")).title = "old title"
        db.commit()
    sync.sync_source("cms", FakeFetcher())
    assert len(resources("cms")) == count
    assert run_status("cms").added == 0
    assert "old title" not in {r.title for r in resources("cms")}


def test_failed_download_is_skipped_then_retried(client):
    broken = "https://cemc.uwaterloo.ca/sites/default/files/documents/2026/2026Gauss7%28E%29.pdf"
    sync.sync_source("cemc", FakeFetcher(fail_downloads=[broken]))
    run = run_status("cemc")
    assert run.status == "ok" and run.message.startswith("1 file(s)")
    assert broken not in {r.url for r in resources("cemc")}

    sync.sync_source("cemc", FakeFetcher())
    assert run_status("cemc").added == 1
    assert broken in {r.url for r in resources("cemc")}


def test_site_down_marks_the_run_as_error(client):
    sync.sync_source("cemc", FakeFetcher(broken=True))
    run = run_status("cemc")
    assert run.status == "error" and run.message == "Couldn't reach the site (site down)."
    assert resources("cemc") == []


def test_error_messages():
    from urllib.error import HTTPError
    assert "slow down" in sync.describe(HTTPError("u", 429, "Too Many Requests", {}, None))
    assert sync.describe(HTTPError("u", 503, "Unavailable", {}, None)) == "The site answered with error 503."


def test_is_due():
    now = utcnow()
    hours = settings.sync_interval_hours
    assert sync.is_due(None, now)
    assert not sync.is_due(ScrapeRun(status="ok", finished_at=now - timedelta(hours=hours - 1)), now)
    assert sync.is_due(ScrapeRun(status="ok", finished_at=now - timedelta(hours=hours)), now)
    assert not sync.is_due(ScrapeRun(status="error", finished_at=now - timedelta(minutes=30)), now)
    assert sync.is_due(ScrapeRun(status="error", finished_at=now - timedelta(hours=1)), now)


def test_interrupted_run_is_marked_and_due_again(client):
    with SessionLocal() as db:
        db.add(ScrapeRun(source="cemc", status="running", started_at=utcnow()))
        db.commit()
    sync.mark_interrupted_runs()
    run = run_status("cemc")
    assert run.status == "error" and "continuing" in run.message
    assert sync.is_due(run, utcnow())




def test_status_api(client):
    never = client.get("/api/sync/us").json()["sources"]
    assert [(s["source"], s["status"]) for s in never] == [("aops", "never")]
    sync.sync_source("aops", FakeFetcher())
    done = client.get("/api/sync/us").json()["sources"][0]
    assert done["status"] == "ok" and done["name"] == "AoPS Wiki" and done["found"] >= 471 and done["finished_at"].endswith("Z")
    assert [s["source"] for s in client.get("/api/sync/canada").json()["sources"]] == ["cemc", "cms"]
    assert client.get("/api/sync/ib").json() == {"sources": []}
    assert client.get("/api/sync/mars").status_code == 404


def test_refresh_now(client, monkeypatch):
    started = []
    monkeypatch.setattr(sync, "start_in_background", started.append)

    assert client.post("/api/sync/canada").status_code == 401
    sign_up(client, username="student")
    assert client.post("/api/sync/canada").status_code == 403
    client.post("/api/auth/logout")

    sign_up_admin(client)
    res = client.post("/api/sync/canada")
    assert res.status_code == 202 and res.json() == {"started": ["cemc", "cms"]}
    assert started == [["cemc", "cms"]]
    assert client.post("/api/sync/ib").status_code == 400
    assert client.post("/api/sync/mars").status_code == 404
