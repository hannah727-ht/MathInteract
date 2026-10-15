

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:

    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    def public(self) -> dict:

        return {"id": self.id, "username": self.username, "is_admin": self.is_admin}



Index("ix_users_username_lower", func.lower(User.username), unique=True)


class Resource(Base):


    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    section: Mapped[str] = mapped_column(String(20), index=True)
    contest: Mapped[str] = mapped_column(String(20), index=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20))


    url: Mapped[str | None] = mapped_column(String(1000), unique=True)


    stored_name: Mapped[str | None] = mapped_column(String(64))
    original_name: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int | None] = mapped_column(Integer)

    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    uploaded_by: Mapped[User | None] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ScrapeRun(Base):


    __tablename__ = "scrape_runs"

    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    status: Mapped[str] = mapped_column(String(10), default="never")
    message: Mapped[str | None] = mapped_column(String(500))
    found: Mapped[int] = mapped_column(Integer, default=0)
    added: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class Image(Base):


    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stored_name: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WeeklyProblem(Base):


    __tablename__ = "weekly_problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    solution: Mapped[str] = mapped_column(Text, default="")
    image_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    solution_image_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    comments: Mapped[list[Comment]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="Comment.id"
    )


class Comment(Base):


    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("weekly_problems.id"), index=True)
    problem: Mapped[WeeklyProblem] = relationship(back_populates="comments")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship()
    body: Mapped[str] = mapped_column(Text)
    image_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class Question(Base):


    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(20), index=True)
    image_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship()
    accepted_answer_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    answers: Mapped[list[Answer]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="Answer.id"
    )


class Answer(Base):


    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    question: Mapped[Question] = relationship(back_populates="answers")
    body: Mapped[str] = mapped_column(Text)
    image_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)




class PageView(Base):


    __tablename__ = "page_views"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    page: Mapped[str] = mapped_column(String(60), primary_key=True)
    views: Mapped[int] = mapped_column(Integer, default=0)


class Visitor(Base):


    __tablename__ = "visitors"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), primary_key=True)


class ActiveUser(Base):


    __tablename__ = "active_users"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class ResourceOpen(Base):
    __tablename__ = "resource_opens"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opens: Mapped[int] = mapped_column(Integer, default=0)


class AnalyticsSalt(Base):


    __tablename__ = "analytics_salts"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    salt: Mapped[str] = mapped_column(String(64))
