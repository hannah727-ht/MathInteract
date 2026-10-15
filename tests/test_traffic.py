

from datetime import date, timedelta

from sqlalchemy import inspect, select

from app import analytics, weeks
from app.db import SessionLocal, engine
from app.models import AnalyticsSalt, PageView, Resource, Visitor
from tests.conftest import sign_up, sign_up_admin

BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/130"}


def traffic(client, days=30):

    client.post("/api/auth/login", json={"username": "boss", "password": "password123"})
    data = client.get(f"/api/admin/traffic?days={days}").json()
    client.post("/api/auth/logout")
    return data


def make_admin(client):
    sign_up_admin(client, username="boss")
    client.post("/api/auth/logout")


def test_page_keys():
    key = analytics.page_key
    assert key("/", {}) == "home" and key("/index.html", {}) == "home"
    assert key("/resources.html", {"section": "ib"}) == "resources/ib"
    assert key("/resources.html", {"section": "mars"}) == "resources/us"
    assert key("/weekly.html", {}) == "weekly" and key("/weekly.html", {"id": "4"}) == "weekly/4"
    assert key("/question.html", {"id": "12"}) == "question/12" and key("/question.html", {"id": "x"}) is None
    assert key("/admin.html", {}) is None and key("/js/app.js", {}) is None and key("/api/questions", {}) is None


def test_page_views_and_top_pages(client):
    make_admin(client)
    for url in ["/", "/", "/resources.html?section=ib", "/qa.html", "/admin.html", "/api/questions", "/css/app.css"]:
        client.get(url, headers=BROWSER)
    data = traffic(client)
    assert data["totals"]["today_views"] == 4
    assert {p["name"]: p["views"] for p in data["top_pages"]} == {"Home": 2, "IB Math": 1, "Q&A": 1}
    assert len(data["days"]) == 30 and data["days"][-1]["day"] == weeks.today().isoformat()


def test_bots_and_admins_are_not_counted(client):
    make_admin(client)
    for agent in ("Googlebot/2.1", "curl/8.7.1", "python-requests/2.32", ""):
        client.get("/", headers={"User-Agent": agent})
    client.post("/api/auth/login", json={"username": "boss", "password": "password123"})
    client.get("/", headers=BROWSER)
    client.post("/api/auth/logout")
    assert traffic(client)["totals"]["today_views"] == 0


def test_visitors_and_logged_in_users(client):
    make_admin(client)
    client.get("/", headers=BROWSER)
    client.get("/qa.html", headers=BROWSER)
    client.get("/", headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari/17"})
    sign_up(client, username="amy")
    client.get("/", headers=BROWSER)
    client.post("/api/auth/logout")
    today = traffic(client)["days"][-1]
    assert (today["views"], today["visitors"], today["active_users"]) == (4, 2, 1)


def test_no_ip_addresses_are_stored(client):
    client.get("/", headers=BROWSER)
    for table in ("page_views", "visitors", "active_users", "resource_opens", "analytics_salts"):
        assert not any("ip" in c["name"].lower() for c in inspect(engine).get_columns(table)), table
    with SessionLocal() as db:
        codes = list(db.scalars(select(Visitor.code)))
    assert len(codes) == 1 and len(codes[0]) == 16 and "testclient" not in codes[0]


def test_resource_opens_count_and_redirect(client):
    make_admin(client)
    with SessionLocal() as db:
        db.add(Resource(section="us", contest="amc10", year=2024, title="2024 AMC 10A Problems", kind="problems",
                        source="aops", url="https://artofproblemsolving.com/wiki/index.php/2024_AMC_10A_Problems"))
        db.commit()
    item = client.get("/api/resources?section=us").json()[0]
    assert item["open_url"] == f"/api/resources/{item['id']}/open"
    for _ in range(3):
        res = client.get(item["open_url"], headers=BROWSER, follow_redirects=False)
        assert res.status_code == 302 and res.headers["location"] == item["href"]
    assert client.get("/api/resources/999/open").status_code == 404
    top = traffic(client)["top_resources"]
    assert top == [{"id": item["id"], "title": "2024 AMC 10A Problems", "opens": 3, "where": "AMC 10 · US Competitions"}]


def test_top_questions_and_weekly(client):
    make_admin(client)
    sign_up(client, username="amy")
    q = client.post("/api/questions", json={"title": "Vectors?", "body": "Dot product", "topic": "ossd"}).json()
    client.post("/api/auth/logout")
    for _ in range(2):
        client.get(f"/question.html?id={q['id']}", headers=BROWSER)
    client.get("/question.html?id=999", headers=BROWSER)
    data = traffic(client)
    assert data["top_questions"] == [{"id": q["id"], "title": "Vectors?", "views": 2}]
    assert data["top_weekly"] == []


def test_old_stats_and_salts_are_deleted(client, monkeypatch):
    start = date(2026, 1, 1)
    monkeypatch.setattr(weeks, "today", lambda: start)
    client.get("/", headers=BROWSER)
    monkeypatch.setattr(weeks, "today", lambda: start + timedelta(days=1))
    client.get("/", headers=BROWSER)
    with SessionLocal() as db:
        assert [s.day for s in db.scalars(select(AnalyticsSalt))] == [start + timedelta(days=1)]
    monkeypatch.setattr(weeks, "today", lambda: start + timedelta(days=analytics.KEEP_DAYS + 1))
    client.get("/", headers=BROWSER)
    with SessionLocal() as db:
        days = sorted({p.day for p in db.scalars(select(PageView))})
    assert days == [start + timedelta(days=1), start + timedelta(days=analytics.KEEP_DAYS + 1)]


def test_traffic_is_admin_only_and_checks_days(client):
    assert client.get("/api/admin/traffic").status_code == 401
    sign_up(client)
    assert client.get("/api/admin/traffic").status_code == 403
    client.post("/api/auth/logout")
    make_admin(client)
    client.post("/api/auth/login", json={"username": "boss", "password": "password123"})
    assert len(client.get("/api/admin/traffic?days=7").json()["days"]) == 7
    assert client.get("/api/admin/traffic?days=3").status_code == 422
