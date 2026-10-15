







from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import weeks
from app.db import get_db
from app.models import Comment, User, WeeklyProblem, utcnow
from app.posts import author_json, check_images, clean_text, images_json, iso
from app.security import get_current_user, require_admin, require_user

router = APIRouter(prefix="/api", tags=["weekly"])

MAX_TITLE = 200
MAX_PROBLEM = 20_000
MAX_COMMENT = 10_000


class ProblemIn(BaseModel):
    week_start: date
    title: str
    body: str
    solution: str = ""
    image_ids: list[int] = []
    solution_image_ids: list[int] = []


class CommentIn(BaseModel):
    body: str
    image_ids: list[int] = []




def comment_json(db: Session, c: Comment) -> dict:
    return {
        "id": c.id,
        "body": c.body,
        "images": images_json(db, c.image_ids),
        "user": author_json(c.user),
        "created_at": iso(c.created_at),
        "edited": c.updated_at is not None,
    }


def problem_summary(db: Session, p: WeeklyProblem) -> dict:
    count = db.scalar(select(func.count()).select_from(Comment).where(Comment.problem_id == p.id))
    return {
        "id": p.id,
        "title": p.title,
        "week_start": p.week_start.isoformat(),
        "status": weeks.status_of(p.week_start),
        "comment_count": count,
    }


def problem_detail(db: Session, p: WeeklyProblem, viewer: User | None) -> dict:
    status = weeks.status_of(p.week_start)
    release = p.week_start + timedelta(days=7)
    released = status == "past"
    show_solution = released or (viewer is not None and viewer.is_admin)
    return {
        **problem_summary(db, p),
        "body": p.body,
        "images": images_json(db, p.image_ids),
        "week_end": (p.week_start + timedelta(days=6)).isoformat(),
        "solution_release": release.isoformat(),
        "solution_released": released,

        "solution": p.solution if show_solution else None,
        "solution_images": images_json(db, p.solution_image_ids) if show_solution else [],
        "comments": [comment_json(db, c) for c in p.comments],
    }


def visible_problem(db: Session, problem_id: int, viewer: User | None) -> WeeklyProblem:

    p = db.get(WeeklyProblem, problem_id)
    if p is None or (weeks.status_of(p.week_start) == "scheduled" and not (viewer and viewer.is_admin)):
        raise HTTPException(status_code=404, detail="Problem not found.")
    return p




@router.get("/weekly/current")
def current(db: Session = Depends(get_db), viewer: User | None = Depends(get_current_user)) -> dict:

    week = weeks.current_week()
    p = db.scalar(select(WeeklyProblem).where(WeeklyProblem.week_start == week))
    return {"week_start": week.isoformat(), "problem": problem_detail(db, p, viewer) if p else None}


@router.get("/weekly")
def archive(db: Session = Depends(get_db), viewer: User | None = Depends(get_current_user)) -> dict:

    query = select(WeeklyProblem).order_by(WeeklyProblem.week_start.desc())
    if not (viewer and viewer.is_admin):
        query = query.where(WeeklyProblem.week_start <= weeks.current_week())
    return {"current_week": weeks.current_week().isoformat(), "problems": [problem_summary(db, p) for p in db.scalars(query)]}


@router.get("/weekly/{problem_id}")
def get_problem(problem_id: int, db: Session = Depends(get_db), viewer: User | None = Depends(get_current_user)) -> dict:
    return problem_detail(db, visible_problem(db, problem_id, viewer), viewer)




def apply_problem(db: Session, p: WeeklyProblem, body: ProblemIn, admin: User) -> None:
    p.title = clean_text(body.title, "a title", MAX_TITLE)
    p.body = clean_text(body.body, "the problem", MAX_PROBLEM)
    p.solution = clean_text(body.solution, "the solution", MAX_PROBLEM, required=False)
    p.image_ids = check_images(db, admin, body.image_ids, already_attached=p.image_ids or [])
    p.solution_image_ids = check_images(db, admin, body.solution_image_ids, already_attached=p.solution_image_ids or [])


def save(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="There is already a problem for that week.")


@router.post("/weekly", status_code=201)
def create_problem(body: ProblemIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    week = weeks.monday_of(body.week_start)
    if db.scalar(select(WeeklyProblem).where(WeeklyProblem.week_start == week)):
        raise HTTPException(status_code=409, detail="There is already a problem for that week.")
    p = WeeklyProblem(week_start=week, author_id=admin.id)
    apply_problem(db, p, body, admin)
    db.add(p)
    save(db)
    return problem_detail(db, p, admin)


@router.put("/weekly/{problem_id}")
def edit_problem(problem_id: int, body: ProblemIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    p = visible_problem(db, problem_id, admin)
    week = weeks.monday_of(body.week_start)
    if week != p.week_start:
        if weeks.status_of(p.week_start) != "scheduled":
            raise HTTPException(status_code=422, detail="This problem's week has started, so its week can't change.")
        if week < weeks.current_week():
            raise HTTPException(status_code=422, detail="A scheduled problem can't be moved to a past week.")
        p.week_start = week
    apply_problem(db, p, body, admin)
    p.updated_at = utcnow()
    save(db)
    return problem_detail(db, p, admin)


@router.delete("/weekly/{problem_id}")
def delete_problem(problem_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    p = visible_problem(db, problem_id, admin)
    if weeks.status_of(p.week_start) != "scheduled":
        raise HTTPException(status_code=409, detail="This problem's week has started, so it can't be deleted (its discussion would be lost).")
    db.delete(p)
    db.commit()
    return {"ok": True}




@router.post("/weekly/{problem_id}/comments", status_code=201)
def add_comment(problem_id: int, body: CommentIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    p = visible_problem(db, problem_id, user)
    if weeks.status_of(p.week_start) == "scheduled":
        raise HTTPException(status_code=409, detail="This problem hasn't started yet.")
    c = Comment(problem=p, user=user, body=clean_text(body.body, "a comment", MAX_COMMENT),
                image_ids=check_images(db, user, body.image_ids))
    db.add(c)
    db.commit()
    return comment_json(db, c)


@router.put("/comments/{comment_id}")
def edit_comment(comment_id: int, body: CommentIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    c = db.get(Comment, comment_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if c.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments.")
    c.body = clean_text(body.body, "a comment", MAX_COMMENT)
    c.image_ids = check_images(db, user, body.image_ids, already_attached=c.image_ids)
    c.updated_at = utcnow()
    db.commit()
    return comment_json(db, c)


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    c = db.get(Comment, comment_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    db.delete(c)
    db.commit()
    return {"ok": True}
