





from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import catalog
from app.db import contains, get_db, page_count
from app.models import Answer, Question, User, utcnow
from app.posts import author_json, check_images, clean_text, images_json, iso
from app.security import require_admin, require_user

router = APIRouter(prefix="/api", tags=["qa"])

MAX_TITLE = 200
MAX_BODY = 20_000


class QuestionIn(BaseModel):
    title: str
    body: str
    topic: str = "general"
    image_ids: list[int] = []


class AnswerIn(BaseModel):
    body: str
    image_ids: list[int] = []


class AcceptIn(BaseModel):
    answer_id: int | None




def answer_count(db: Session, question_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Answer).where(Answer.question_id == question_id))


def question_summary(db: Session, q: Question) -> dict:
    return {
        "id": q.id,
        "title": q.title,
        "topic": q.topic,
        "user": author_json(q.user),
        "created_at": iso(q.created_at),
        "answer_count": answer_count(db, q.id),
        "solved": q.accepted_answer_id is not None,
    }


def answer_json(db: Session, a: Answer, accepted_id: int | None) -> dict:
    return {
        "id": a.id,
        "body": a.body,
        "images": images_json(db, a.image_ids),
        "user": author_json(a.user),
        "created_at": iso(a.created_at),
        "edited": a.updated_at is not None,
        "accepted": a.id == accepted_id,
    }


def question_detail(db: Session, q: Question) -> dict:

    answers = sorted(q.answers, key=lambda a: (a.id != q.accepted_answer_id, a.id))
    return {
        **question_summary(db, q),
        "body": q.body,
        "images": images_json(db, q.image_ids),
        "edited": q.updated_at is not None,
        "accepted_answer_id": q.accepted_answer_id,
        "answers": [answer_json(db, a, q.accepted_answer_id) for a in answers],
    }


def get_question(db: Session, question_id: int) -> Question:
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    return q


def get_answer(db: Session, answer_id: int) -> Answer:
    a = db.get(Answer, answer_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Answer not found.")
    return a


def check_topic(topic: str) -> str:
    if topic not in catalog.QA_TOPICS:
        raise HTTPException(status_code=422, detail="Please choose a valid topic.")
    return topic




@router.get("/questions")
def list_questions(
    topic: str | None = Query(None, description="Only this topic, e.g. ib"),
    q: str | None = Query(None, description="Search text, matched against the title and the question"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:

    query = select(Question)
    if topic:
        query = query.where(Question.topic == check_topic(topic))
    if q and q.strip():
        needle = contains(q.strip())
        query = query.where(or_(Question.title.ilike(needle, escape="\\"), Question.body.ilike(needle, escape="\\")))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Question.created_at.desc(), Question.id.desc()).offset((page - 1) * limit).limit(limit))
    return {
        "topics": [{"key": k, "name": n} for k, n in catalog.QA_TOPICS.items()],
        "total": total,
        "page": page,
        "pages": page_count(total, limit),
        "questions": [question_summary(db, row) for row in rows],
    }


@router.get("/questions/{question_id}")
def read_question(question_id: int, db: Session = Depends(get_db)) -> dict:
    return question_detail(db, get_question(db, question_id))




@router.post("/questions", status_code=201)
def ask(body: QuestionIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    q = Question(
        title=clean_text(body.title, "a title", MAX_TITLE),
        body=clean_text(body.body, "your question", MAX_BODY),
        topic=check_topic(body.topic),
        image_ids=check_images(db, user, body.image_ids),
        user=user,
    )
    db.add(q)
    db.commit()
    return question_detail(db, q)


@router.put("/questions/{question_id}")
def edit_question(question_id: int, body: QuestionIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    q = get_question(db, question_id)
    if q.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own questions.")
    q.title = clean_text(body.title, "a title", MAX_TITLE)
    q.body = clean_text(body.body, "your question", MAX_BODY)
    q.topic = check_topic(body.topic)
    q.image_ids = check_images(db, user, body.image_ids, already_attached=q.image_ids)
    q.updated_at = utcnow()
    db.commit()
    return question_detail(db, q)


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    db.delete(get_question(db, question_id))
    db.commit()
    return {"ok": True}


@router.post("/questions/{question_id}/accept")
def accept(question_id: int, body: AcceptIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:

    q = get_question(db, question_id)
    if q.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the person who asked can accept an answer.")
    if body.answer_id is not None and body.answer_id not in {a.id for a in q.answers}:
        raise HTTPException(status_code=422, detail="That answer doesn't belong to this question.")
    q.accepted_answer_id = body.answer_id
    db.commit()
    return question_detail(db, q)




@router.post("/questions/{question_id}/answers", status_code=201)
def add_answer(question_id: int, body: AnswerIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    q = get_question(db, question_id)
    a = Answer(question=q, user=user, body=clean_text(body.body, "an answer", MAX_BODY),
               image_ids=check_images(db, user, body.image_ids))
    db.add(a)
    db.commit()
    return answer_json(db, a, q.accepted_answer_id)


@router.put("/answers/{answer_id}")
def edit_answer(answer_id: int, body: AnswerIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    a = get_answer(db, answer_id)
    if a.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own answers.")
    a.body = clean_text(body.body, "an answer", MAX_BODY)
    a.image_ids = check_images(db, user, body.image_ids, already_attached=a.image_ids)
    a.updated_at = utcnow()
    db.commit()
    return answer_json(db, a, a.question.accepted_answer_id)


@router.delete("/answers/{answer_id}")
def delete_answer(answer_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    a = get_answer(db, answer_id)
    if a.question.accepted_answer_id == a.id:
        a.question.accepted_answer_id = None
    db.delete(a)
    db.commit()
    return {"ok": True}
