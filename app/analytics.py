








from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import catalog, weeks
from app.db import SessionLocal
from app.models import ActiveUser, AnalyticsSalt, PageView, Question, Resource, ResourceOpen, User, Visitor, WeeklyProblem

log = logging.getLogger("mathinteract.analytics")

KEEP_DAYS = 90
BOT = re.compile(r"bot|crawl|spider|slurp|preview|monitor|curl|wget|python|httpx|headless|scrapy|facebookexternalhit", re.I)
SIMPLE_PAGES = {"/": "home", "/index.html": "home", "/qa.html": "qa", "/ask.html": "ask",
                "/login.html": "login", "/signup.html": "signup", "/account.html": "account"}


def page_key(path: str, query: dict) -> str | None:

    if path in SIMPLE_PAGES:
        return SIMPLE_PAGES[path]
    item = query.get("id", "")
    if path == "/resources.html":
        section = query.get("section")
        return f"resources/{section if section in catalog.SECTIONS else 'us'}"
    if path == "/weekly.html":
        return f"weekly/{item}" if item.isdigit() else "weekly"
    if path == "/question.html" and item.isdigit():
        return f"question/{item}"
    return None


def is_bot(user_agent: str) -> bool:
    return not user_agent or bool(BOT.search(user_agent))


def salt_for(db: Session, day: date) -> str:

    row = db.get(AnalyticsSalt, day)
    if row:
        return row.salt
    db.execute(delete(AnalyticsSalt).where(AnalyticsSalt.day < day))
    oldest = day - timedelta(days=KEEP_DAYS)
    for model in (PageView, Visitor, ActiveUser, ResourceOpen):
        db.execute(delete(model).where(model.day < oldest))
    db.add(AnalyticsSalt(day=day, salt=secrets.token_hex(32)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return db.get(AnalyticsSalt, day).salt


def visitor_code(salt: str, ip: str, user_agent: str) -> str:
    return hashlib.sha256(f"{salt}|{ip}|{user_agent}".encode()).hexdigest()[:16]


def _skip(db: Session, user_agent: str, user_id: int | None) -> bool:
    if is_bot(user_agent):
        return True
    user = db.get(User, user_id) if user_id else None
    return bool(user and user.is_admin)


def record_view(page: str, ip: str, user_agent: str, user_id: int | None) -> None:

    try:
        with SessionLocal() as db:
            if _skip(db, user_agent, user_id):
                return
            day = weeks.today()
            code = visitor_code(salt_for(db, day), ip, user_agent)
            db.execute(insert(PageView).values(day=day, page=page, views=1)
                       .on_conflict_do_update(index_elements=["day", "page"], set_={"views": PageView.views + 1}))
            db.execute(insert(Visitor).values(day=day, code=code).on_conflict_do_nothing())
            if user_id:
                db.execute(insert(ActiveUser).values(day=day, user_id=user_id).on_conflict_do_nothing())
            db.commit()
    except Exception:
        log.exception("could not record a page view")


def record_open(resource_id: int, user_agent: str, user_id: int | None) -> None:
    try:
        with SessionLocal() as db:
            if _skip(db, user_agent, user_id):
                return
            db.execute(insert(ResourceOpen).values(day=weeks.today(), resource_id=resource_id, opens=1)
                       .on_conflict_do_update(index_elements=["day", "resource_id"], set_={"opens": ResourceOpen.opens + 1}))
            db.commit()
    except Exception:
        log.exception("could not record a resource open")


def areas() -> dict[str, str]:

    names = {"home": "Home", "weekly": "Weekly Problem", "qa": "Q&A", "question": "Q&A", "ask": "Q&A",
             "login": "Log in", "signup": "Sign up", "account": "Account"}
    names.update({f"resources/{k}": s["name"] for k, s in catalog.SECTIONS.items()})
    return names


def area_of(page: str) -> str:
    names = areas()
    return names.get(page) or names.get(page.split("/")[0], page)


def stats(db: Session, days: int) -> dict:

    today = weeks.today()
    first = today - timedelta(days=days - 1)
    series = {first + timedelta(days=i): {"views": 0, "visitors": 0, "active_users": 0} for i in range(days)}
    page_rows = db.execute(select(PageView.day, PageView.page, PageView.views).where(PageView.day >= first)).all()
    for day, _, views in page_rows:
        series[day]["views"] += views
    for model, field in ((Visitor, "visitors"), (ActiveUser, "active_users")):
        for (day,) in db.execute(select(model.day).where(model.day >= first)).all():
            series[day][field] += 1

    by_page: dict[str, int] = {}
    for _, page, views in page_rows:
        by_page[page] = by_page.get(page, 0) + views
    by_area: dict[str, int] = {}
    for page, views in by_page.items():
        by_area[area_of(page)] = by_area.get(area_of(page), 0) + views

    def top_items(prefix: str, model, limit: int) -> list[dict]:
        counts = {int(p.split("/")[1]): v for p, v in by_page.items() if p.startswith(prefix + "/")}
        rows = {r.id: r for r in db.scalars(select(model).where(model.id.in_(counts)))} if counts else {}
        ranked = sorted(((v, i) for i, v in counts.items() if i in rows), reverse=True)[:limit]
        return [{"id": i, "title": rows[i].title, "views": v} for v, i in ranked]

    opens: dict[int, int] = {}
    for resource_id, n in db.execute(select(ResourceOpen.resource_id, ResourceOpen.opens).where(ResourceOpen.day >= first)).all():
        opens[resource_id] = opens.get(resource_id, 0) + n
    resources = {r.id: r for r in db.scalars(select(Resource).where(Resource.id.in_(opens)))} if opens else {}
    top_resources = [
        {"id": i, "title": resources[i].title, "opens": n,
         "where": f"{catalog.SECTIONS[resources[i].section]['contests'].get(resources[i].contest, resources[i].contest)} · {catalog.SECTIONS[resources[i].section]['name']}"}
        for n, i in sorted(((n, i) for i, n in opens.items() if i in resources), reverse=True)[:10]
    ]
    distinct_users = len(set(db.scalars(select(ActiveUser.user_id).where(ActiveUser.day >= first))))
    return {
        "days": [{"day": d.isoformat(), **v} for d, v in series.items()],
        "totals": {
            "views": sum(v["views"] for v in series.values()),
            "average_visitors": round(sum(v["visitors"] for v in series.values()) / days, 1),
            "logged_in_users": distinct_users,
            "today_views": series[today]["views"],
        },
        "top_pages": [{"name": n, "views": v} for n, v in sorted(by_area.items(), key=lambda x: -x[1])],
        "top_resources": top_resources,
        "top_questions": top_items("question", Question, 10),
        "top_weekly": top_items("weekly", WeeklyProblem, 5),
    }
