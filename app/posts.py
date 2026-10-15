




from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Image, User

MAX_IMAGES = 4


def clean_text(text: str, what: str, max_length: int, required: bool = True) -> str:

    text = text.strip()
    if required and not text:
        raise HTTPException(status_code=422, detail=f"Please write {what}.")
    if len(text) > max_length:
        raise HTTPException(status_code=422, detail=f"That's too long: {what} can be at most {max_length:,} characters.")
    return text


def check_images(db: Session, user: User, image_ids: list[int], already_attached: list[int] = ()) -> list[int]:

    ids = list(dict.fromkeys(image_ids))
    if len(ids) > MAX_IMAGES:
        raise HTTPException(status_code=422, detail=f"A post can have at most {MAX_IMAGES} images.")
    new = [i for i in ids if i not in already_attached]
    if new:
        owned = set(db.scalars(select(Image.id).where(Image.id.in_(new), Image.owner_id == user.id)))
        if owned != set(new):
            raise HTTPException(status_code=422, detail="One of the images could not be found. Please upload it again.")
    return ids


def images_json(db: Session, image_ids: list[int]) -> list[dict]:

    if not image_ids:
        return []
    rows = {img.id: img for img in db.scalars(select(Image).where(Image.id.in_(image_ids)))}
    return [
        {"id": i, "url": f"/api/images/{i}", "width": rows[i].width, "height": rows[i].height}
        for i in image_ids if i in rows
    ]


def iso(value) -> str | None:

    return value.isoformat() + "Z" if value else None


def author_json(user: User) -> dict:
    return {"id": user.id, "username": user.username, "is_admin": user.is_admin}
