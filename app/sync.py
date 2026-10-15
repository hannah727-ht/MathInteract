









from __future__ import annotations

import logging
import secrets
import threading
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Resource, ScrapeRun, utcnow
from app.routers.resources import uploads_dir
from app.scrapers import aops, cemc, cms
from app.scrapers.base import BlockedByRobots, Fetcher, Item

log = logging.getLogger("mathinteract.sync")


SCRAPERS = {
    "aops": (aops.scrape, "us", "AoPS Wiki"),
    "cemc": (cemc.scrape, "canada", "CEMC"),
    "cms": (cms.scrape, "canada", "CMS"),
}
MAX_PDF_BYTES = 50 * 1024 * 1024
RETRY_AFTER_ERROR = timedelta(hours=1)
CHECK_EVERY_SECONDS = 30 * 60

_running: set[str] = set()
_running_lock = threading.Lock()


def sources_for(section: str) -> list[str]:
    return [key for key, (_, sec, _) in SCRAPERS.items() if sec == section]


def make_fetcher() -> Fetcher:
    return Fetcher()




def sync_source(source: str, fetch=None) -> None:

    with _running_lock:
        if source in _running:
            return
        _running.add(source)
    try:
        _run(source, fetch or make_fetcher())
    finally:
        with _running_lock:
            _running.discard(source)


def _run(source: str, fetch) -> None:
    scrape = SCRAPERS[source][0]
    with SessionLocal() as db:
        run = db.get(ScrapeRun, source) or ScrapeRun(source=source)
        run.status, run.message, run.found, run.added = "running", None, 0, 0
        run.started_at = utcnow()
        db.add(run)
        db.commit()
        try:
            items = scrape(fetch)
            run.found = len(items)
            db.commit()
            failed = save_items(db, source, items, fetch, run)
            run.status = "ok"
            run.message = f"{failed} file(s) could not be downloaded; will retry next time." if failed else None
        except Exception as e:
            db.rollback()
            log.exception("sync of %s failed", source)
            run.status, run.message = "error", describe(e)[:500]
        run.finished_at = utcnow()
        db.commit()


def describe(error: Exception) -> str:

    if isinstance(error, HTTPError) and error.code == 429:
        return "The site asked us to slow down (too many requests from this network)."
    if isinstance(error, HTTPError):
        return f"The site answered with error {error.code}."
    if isinstance(error, URLError):
        return f"Couldn't reach the site ({error.reason})."
    return f"{type(error).__name__}: {error}"


def save_items(db, source: str, items: list[Item], fetch, run: ScrapeRun) -> int:

    known = {r.url: r for r in db.scalars(select(Resource).where(Resource.source == source))}
    failed = 0
    for item in items:
        existing = known.get(item.url)
        if existing is not None:
            existing.contest, existing.year, existing.title, existing.kind = item.contest, item.year, item.title, item.kind
            continue
        resource = Resource(section=item.section, contest=item.contest, year=item.year, title=item.title,
                            kind=item.kind, source=source, url=item.url)
        if item.download:
            try:
                resource.stored_name = secrets.token_hex(16) + ".pdf"
                resource.size = fetch.download(item.url, uploads_dir() / resource.stored_name, MAX_PDF_BYTES)
                resource.original_name = unquote(urlsplit(item.url).path.rsplit("/", 1)[-1])
            except (URLError, OSError, ValueError, BlockedByRobots) as e:
                log.warning("could not download %s: %s", item.url, e)
                failed += 1
                continue
        db.add(resource)
        run.added += 1
        db.commit()
    db.commit()
    return failed


def start_in_background(sources: list[str]) -> threading.Thread:
    def run_sources():
        for source in sources:
            sync_source(source)

    thread = threading.Thread(target=run_sources, name="sync-now", daemon=True)
    thread.start()
    return thread


def is_running(source: str) -> bool:
    with _running_lock:
        return source in _running




def is_due(run: ScrapeRun | None, now: datetime) -> bool:
    if run is None or run.finished_at is None:
        return True
    if run.status == "ok":
        return now - run.finished_at >= timedelta(hours=settings.sync_interval_hours)
    return now - run.finished_at >= RETRY_AFTER_ERROR


def mark_interrupted_runs() -> None:

    with SessionLocal() as db:
        for run in db.scalars(select(ScrapeRun).where(ScrapeRun.status == "running")):

            run.status, run.message, run.finished_at = "error", "Interrupted (the server restarted); continuing.", None
        db.commit()


def run_due_sources() -> None:
    for source in SCRAPERS:
        with SessionLocal() as db:
            due = is_due(db.get(ScrapeRun, source), utcnow())
        if due:
            sync_source(source)


def start_scheduler(stop: threading.Event) -> threading.Thread:
    def loop() -> None:
        if stop.wait(15):
            return
        while True:
            try:
                run_due_sources()
            except Exception:
                log.exception("scheduled sync failed")
            if stop.wait(CHECK_EVERY_SECONDS):
                return

    thread = threading.Thread(target=loop, name="sync-scheduler", daemon=True)
    thread.start()
    return thread
