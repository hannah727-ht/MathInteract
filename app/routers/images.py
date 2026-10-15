




from __future__ import annotations

import io
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Image, User
from app.security import require_user

router = APIRouter(prefix="/api/images", tags=["images"])

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 40_000_000
FORMATS = {"JPEG": (".jpg", "image/jpeg"), "PNG": (".png", "image/png"), "WEBP": (".webp", "image/webp")}
CONTENT_TYPES = {ext: content_type for ext, content_type in FORMATS.values()}


def images_dir() -> Path:
    folder = settings.upload_dir / "images"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def read_image(file: UploadFile) -> tuple[bytes, str, int, int]:

    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Images can be at most 5 MB.")
    if not data:
        raise HTTPException(status_code=422, detail="The file is empty.")
    try:
        with PILImage.open(io.BytesIO(data)) as img:
            fmt, (width, height) = img.format, img.size
            if fmt not in FORMATS:
                raise HTTPException(status_code=415, detail="Only JPG, PNG, and WEBP images can be attached.")
            if width * height > MAX_PIXELS:
                raise HTTPException(status_code=413, detail="That image is too large (too many pixels).")
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, PILImage.DecompressionBombError):
        raise HTTPException(status_code=415, detail="That file isn't a valid JPG, PNG, or WEBP image.")
    return data, fmt, width, height


@router.post("", status_code=201)
def upload_image(file: UploadFile = File(...), user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    data, fmt, width, height = read_image(file)
    stored_name = secrets.token_hex(16) + FORMATS[fmt][0]
    (images_dir() / stored_name).write_bytes(data)
    image = Image(owner_id=user.id, stored_name=stored_name, width=width, height=height, size=len(data))
    db.add(image)
    db.commit()
    return {"id": image.id, "url": f"/api/images/{image.id}", "width": width, "height": height}


@router.get("/{image_id}")
def get_image(image_id: int, db: Session = Depends(get_db)) -> FileResponse:
    image = db.get(Image, image_id)
    path = images_dir() / image.stored_name if image else None
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(
        path,
        media_type=CONTENT_TYPES[path.suffix],
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=31536000, immutable"},
    )
