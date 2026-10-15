

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import catalog, sync
from app.db import get_db
from app.models import ScrapeRun, User
from app.posts import iso
from app.security import require_admin

router = APIRouter(prefix="/api/sync", tags=["sync"])


def source_status(db: Session, source: str) -> dict:

    run = db.get(ScrapeRun, source) or ScrapeRun(source=source, status="never", found=0, added=0)
    return {
        "source": source,
        "name": sync.SCRAPERS[source][2],
        "section": sync.SCRAPERS[source][1],
        "status": "running" if sync.is_running(source) else run.status,
        "message": run.message,
        "found": run.found,
        "added": run.added,
        "started_at": iso(run.started_at),
        "finished_at": iso(run.finished_at),
    }


@router.get("/{section}")
def status(section: str, db: Session = Depends(get_db)) -> dict:

    if not catalog.is_valid(section):
        raise HTTPException(status_code=404, detail="Unknown section.")
    return {"sources": [source_status(db, source) for source in sync.sources_for(section)]}


@router.post("/{section}", status_code=202)
def refresh_now(section: str, admin: User = Depends(require_admin)) -> dict:

    if not catalog.is_valid(section):
        raise HTTPException(status_code=404, detail="Unknown section.")
    sources = sync.sources_for(section)
    if not sources:
        raise HTTPException(status_code=400, detail="This section has no scrapers; its files are uploaded by admins.")
    sync.start_in_background(sources)
    return {"started": sources}
