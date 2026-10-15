




from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import accounts, analytics, sync
from app.config import settings
from app.db import contains, get_db, page_count
from app.models import Answer, Comment, Question, Resource, User, WeeklyProblem
from app.posts import iso
from app.routers.sync import source_status
from app.security import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

PAGE_SIZE = 20


class AdminIn(BaseModel):
    is_admin: bool


def count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where))


def folder_size(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) if folder.exists() else 0


def database_size() -> int:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        return 0
    path = Path(settings.database_url[len(prefix):])
    return path.stat().st_size if path.is_file() else 0


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    resources = dict(db.execute(select(Resource.source, func.count()).group_by(Resource.source)).all())
    return {
        "counts": {
            "users": count(db, User),
            "admins": count(db, User, User.is_admin.is_(True)),
            "questions": count(db, Question),
            "answers": count(db, Answer),
            "comments": count(db, Comment),
            "weekly_problems": count(db, WeeklyProblem),
            "resources": sum(resources.values()),
        },
        "resources_by_source": resources,
        "disk": {"files": folder_size(settings.upload_dir), "database": database_size()},
        "scrapers": [source_status(db, source) for source in sync.SCRAPERS],
    }


@router.get("/traffic")
def traffic(days: int = Query(30, ge=7, le=90), db: Session = Depends(get_db)) -> dict:

    return analytics.stats(db, days)


def posts_of(user_id) -> object:

    return (
        select(func.count()).select_from(Question).where(Question.user_id == user_id).scalar_subquery()
        + select(func.count()).select_from(Answer).where(Answer.user_id == user_id).scalar_subquery()
        + select(func.count()).select_from(Comment).where(Comment.user_id == user_id).scalar_subquery()
    )


def user_json(user: User, posts: int) -> dict:
    return {"id": user.id, "username": user.username, "is_admin": user.is_admin, "created_at": iso(user.created_at), "posts": posts}


@router.get("/users")
def list_users(q: str | None = Query(None), page: int = Query(1, ge=1), db: Session = Depends(get_db)) -> dict:

    query = select(User, posts_of(User.id).label("posts"))
    if q and q.strip():
        query = query.where(User.username.ilike(contains(q.strip()), escape="\\"))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(query.order_by(User.created_at.desc(), User.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    return {
        "total": total,
        "page": page,
        "pages": page_count(total, PAGE_SIZE),
        "users": [user_json(user, posts) for user, posts in rows],
    }


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.post("/users/{user_id}/admin")
def change_admin(user_id: int, body: AdminIn, db: Session = Depends(get_db)) -> dict:

    user = get_user(db, user_id)
    try:
        accounts.set_admin(db, user, body.is_admin)
    except accounts.LastAdminError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return user_json(user, db.scalar(select(posts_of(user.id))))


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db)) -> dict:

    user = get_user(db, user_id)
    return {"username": user.username, "temporary_password": accounts.reset_password(db, user)}
