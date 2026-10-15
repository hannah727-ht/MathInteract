




from __future__ import annotations

import secrets
from datetime import date
from pathlib import Path, PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import analytics, catalog
from app.config import settings
from app.db import get_db
from app.models import Resource, User
from app.security import require_admin

router = APIRouter(prefix="/api", tags=["resources"])

CHUNK = 1024 * 1024



FILE_TYPES: dict[str, tuple[str, bool, tuple[bytes, ...]]] = {
    ".pdf": ("application/pdf", True, (b"%PDF-",)),
    ".png": ("image/png", True, (b"\x89PNG\r\n\x1a\n",)),
    ".jpg": ("image/jpeg", True, (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", True, (b"\xff\xd8\xff",)),
    ".webp": ("image/webp", True, (b"RIFF",)),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", False, (b"PK\x03\x04",)),
    ".doc": ("application/msword", False, (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)),
}


def uploads_dir() -> Path:
    folder = settings.upload_dir / "resources"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def to_json(r: Resource) -> dict:
    section = catalog.SECTIONS[r.section]
    stored = r.stored_name is not None
    return {
        "id": r.id,
        "section": r.section,
        "section_name": section["name"],
        "contest": r.contest,
        "contest_name": section["contests"].get(r.contest, r.contest),
        "year": r.year,
        "title": r.title,
        "kind": r.kind,
        "source": r.source,

        "href": f"/api/resources/{r.id}/file" if stored else r.url,
        "official_url": r.url,
        "open_url": f"/api/resources/{r.id}/open",
        "file_type": PurePath(r.original_name).suffix.lstrip(".").upper() if stored else "Link",
        "size": r.size,
        "created_at": r.created_at.isoformat() + "Z",
    }


def sort_key(r: Resource) -> tuple:
    kind_order = list(catalog.KINDS).index(r.kind) if r.kind in catalog.KINDS else 99

    return (-(r.year or 0), kind_order, r.title.lower())




@router.get("/catalog")
def get_catalog() -> dict:
    result = catalog.public_catalog()
    result["max_upload_mb"] = settings.max_upload_mb
    return result


@router.get("/resources")
def list_resources(
    section: str = Query(..., description="Section key, e.g. us"),
    contest: str | None = Query(None, description="Only this contest/course, e.g. amc10"),
    db: Session = Depends(get_db),
) -> list[dict]:

    if not catalog.is_valid(section, contest):
        raise HTTPException(status_code=404, detail="Unknown section or contest.")
    query = select(Resource).where(Resource.section == section)
    if contest:
        query = query.where(Resource.contest == contest)
    return [to_json(r) for r in sorted(db.scalars(query), key=sort_key)]


@router.get("/resources/recent")
def recent_resources(limit: int = Query(6, ge=1, le=20), db: Session = Depends(get_db)) -> list[dict]:

    rows = db.scalars(select(Resource).order_by(Resource.created_at.desc(), Resource.id.desc()).limit(limit))
    return [to_json(r) for r in rows]


@router.get("/resources/{resource_id}/open")
def open_resource(resource_id: int, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:

    r = db.get(Resource, resource_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    analytics.record_open(r.id, request.headers.get("user-agent", ""), request.session.get("user_id"))
    return RedirectResponse(to_json(r)["href"], status_code=302)


@router.get("/resources/{resource_id}/file")
def download(resource_id: int, db: Session = Depends(get_db)) -> FileResponse:

    r = db.get(Resource, resource_id)
    path = uploads_dir() / r.stored_name if r is not None and r.stored_name else None
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    content_type, inline, _ = FILE_TYPES[path.suffix]
    return FileResponse(
        path,
        media_type=content_type,
        filename=r.original_name,
        content_disposition_type="inline" if inline else "attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )




def parse_year(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
    if not text.isdigit() or not 1950 <= int(text) <= date.today().year + 1:
        raise HTTPException(status_code=422, detail="Year must be a 4-digit year, or left empty.")
    return int(text)


def save_upload(file: UploadFile, extension: str) -> tuple[str, int]:

    limit = settings.max_upload_mb * 1024 * 1024
    stored_name = secrets.token_hex(16) + extension
    path = uploads_dir() / stored_name
    size = 0
    try:
        with path.open("wb") as out:
            chunk = file.file.read(CHUNK)
            while chunk:
                if size == 0:
                    starts = FILE_TYPES[extension][2]
                    if not chunk.startswith(starts) or (extension == ".webp" and chunk[8:12] != b"WEBP"):
                        raise HTTPException(status_code=415, detail="This file isn’t a real " + extension.lstrip(".").upper() + " file.")
                size += len(chunk)
                if size > limit:
                    raise HTTPException(status_code=413, detail=f"Files can be at most {settings.max_upload_mb} MB.")
                out.write(chunk)
                chunk = file.file.read(CHUNK)
        if size == 0:
            raise HTTPException(status_code=422, detail="The file is empty.")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return stored_name, size


@router.post("/resources", status_code=201)
def upload(
    section: str = Form(...),
    contest: str = Form(...),
    kind: str = Form(...),
    year: str = Form(""),
    title: str = Form(""),
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:

    if not catalog.is_valid(section, contest):
        raise HTTPException(status_code=422, detail="Please choose a valid section and contest.")
    if kind not in catalog.KINDS:
        raise HTTPException(status_code=422, detail="Please choose a valid type.")
    original_name = PurePath(file.filename or "file").name[:255]
    extension = PurePath(original_name).suffix.lower()
    if extension not in FILE_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF, image (PNG, JPG, WEBP), and Word (DOC, DOCX) files can be uploaded.")
    year_value = parse_year(year)
    title = title.strip()[:200] or PurePath(original_name).stem[:200]

    stored_name, size = save_upload(file, extension)
    r = Resource(
        section=section, contest=contest, year=year_value, title=title, kind=kind, source="upload",
        stored_name=stored_name, original_name=original_name, size=size, uploaded_by=admin,
    )
    db.add(r)
    db.commit()
    return to_json(r)


@router.delete("/resources/{resource_id}")
def delete(resource_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:

    r = db.get(Resource, resource_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    if r.source != "upload":
        raise HTTPException(status_code=400, detail="Only uploaded files can be deleted. Scraped links are updated by the scrapers.")
    (uploads_dir() / r.stored_name).unlink(missing_ok=True)
    db.delete(r)
    db.commit()
    return {"ok": True}
