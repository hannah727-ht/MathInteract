

from datetime import date

import pytest

from app import weeks
from tests.conftest import sign_up, sign_up_admin
from tests.test_images import upload as upload_image


TODAY = date(2026, 10, 7)
THIS_WEEK, LAST_WEEK, NEXT_WEEK = "2026-10-05", "2026-09-28", "2026-10-12"


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(weeks, "today", lambda: TODAY)


def new_problem(client, week=THIS_WEEK, **fields):
    body = {"week_start": week, "title": f"Problem of {week}", "body": "Find $x$ if $x^2 = 4$.",
            "solution": "$x = \\pm 2$", **fields}
    return client.post("/api/weekly", json=body)


def log_out(client):
    client.post("/api/auth/logout")


def setup_weeks(client):

    sign_up_admin(client)
    ids = {w: new_problem(client, w).json()["id"] for w in (LAST_WEEK, THIS_WEEK, NEXT_WEEK)}
    log_out(client)
    return ids




def test_no_problem_this_week(client):
    assert client.get("/api/weekly/current").json() == {"week_start": THIS_WEEK, "problem": None}


def test_current_problem_hides_solution_until_next_week(client):
    ids = setup_weeks(client)
    cur = client.get("/api/weekly/current").json()["problem"]
    assert cur["id"] == ids[THIS_WEEK] and cur["status"] == "current"
    assert cur["solution"] is None and cur["solution_released"] is False
    assert cur["solution_release"] == "2026-10-12" and cur["week_end"] == "2026-10-11"

    past = client.get(f"/api/weekly/{ids[LAST_WEEK]}").json()
    assert past["status"] == "past" and past["solution"] == "$x = \\pm 2$"


def test_future_problems_are_hidden_from_everyone_but_admins(client):
    ids = setup_weeks(client)
    assert client.get(f"/api/weekly/{ids[NEXT_WEEK]}").status_code == 404
    weeks_listed = [p["week_start"] for p in client.get("/api/weekly").json()["problems"]]
    assert weeks_listed == [THIS_WEEK, LAST_WEEK]

    sign_up(client, username="student")
    assert client.get(f"/api/weekly/{ids[NEXT_WEEK]}").status_code == 404
    log_out(client)

    client.post("/api/auth/login", json={"username": "hannah", "password": "password123"})
    admin_list = client.get("/api/weekly").json()["problems"]
    assert [(p["week_start"], p["status"]) for p in admin_list] == [(NEXT_WEEK, "scheduled"), (THIS_WEEK, "current"), (LAST_WEEK, "past")]
    assert client.get("/api/weekly/current").json()["problem"]["solution"] == "$x = \\pm 2$"


def test_week_rolls_over_on_monday(client, monkeypatch):
    ids = setup_weeks(client)
    monkeypatch.setattr(weeks, "today", lambda: date(2026, 10, 12))
    cur = client.get("/api/weekly/current").json()["problem"]
    assert cur["id"] == ids[NEXT_WEEK]
    assert client.get(f"/api/weekly/{ids[THIS_WEEK]}").json()["solution"] == "$x = \\pm 2$"




def test_create_normalizes_to_monday_and_rejects_duplicates(client):
    sign_up_admin(client)
    res = new_problem(client, week="2026-10-08")
    assert res.status_code == 201 and res.json()["week_start"] == THIS_WEEK
    assert new_problem(client, week=THIS_WEEK).status_code == 409


def test_create_needs_admin_and_valid_input(client):
    assert new_problem(client).status_code == 401
    sign_up(client, username="student")
    assert new_problem(client).status_code == 403
    log_out(client)
    sign_up_admin(client)
    assert new_problem(client, title="  ").status_code == 422
    assert new_problem(client, body="").status_code == 422
    assert new_problem(client, body="x" * 20_001).status_code == 422
    assert new_problem(client, week="not a date").status_code == 422


def test_problem_images(client):
    sign_up_admin(client)
    img = upload_image(client).json()
    p = new_problem(client, image_ids=[img["id"]], solution_image_ids=[img["id"]]).json()
    assert [i["id"] for i in p["images"]] == [img["id"]]
    assert p["images"][0]["url"] == img["url"]
    assert new_problem(client, week=NEXT_WEEK, image_ids=[999]).status_code == 422


def test_edit_problem(client):
    sign_up_admin(client)
    p = new_problem(client).json()
    res = client.put(f"/api/weekly/{p['id']}", json={"week_start": THIS_WEEK, "title": "Fixed typo", "body": "New body"})
    assert res.status_code == 200 and res.json()["title"] == "Fixed typo"

    assert client.put(f"/api/weekly/{p['id']}", json={"week_start": NEXT_WEEK, "title": "t", "body": "b"}).status_code == 422
    future = new_problem(client, week=NEXT_WEEK).json()
    assert client.put(f"/api/weekly/{future['id']}", json={"week_start": "2026-10-19", "title": "t", "body": "b"}).json()["week_start"] == "2026-10-19"
    assert client.put(f"/api/weekly/{future['id']}", json={"week_start": LAST_WEEK, "title": "t", "body": "b"}).status_code == 422
    assert client.put(f"/api/weekly/{future['id']}", json={"week_start": THIS_WEEK, "title": "t", "body": "b"}).status_code == 409


def test_delete_only_scheduled_problems(client):
    ids = setup_weeks(client)
    sign_up(client, username="student")
    assert client.delete(f"/api/weekly/{ids[NEXT_WEEK]}").status_code == 403
    log_out(client)
    client.post("/api/auth/login", json={"username": "hannah", "password": "password123"})
    assert client.delete(f"/api/weekly/{ids[THIS_WEEK]}").status_code == 409
    assert client.delete(f"/api/weekly/{ids[NEXT_WEEK]}").status_code == 200
    assert client.get(f"/api/weekly/{ids[NEXT_WEEK]}").status_code == 404




def test_comment_flow(client):
    ids = setup_weeks(client)
    res = client.post(f"/api/weekly/{ids[THIS_WEEK]}/comments", json={"body": "Is it $2$?"})
    assert res.status_code == 401

    sign_up(client, username="amy")
    img = upload_image(client).json()
    res = client.post(f"/api/weekly/{ids[THIS_WEEK]}/comments", json={"body": "  Is it $2$?  ", "image_ids": [img["id"]]})
    assert res.status_code == 201
    c = res.json()
    assert c["body"] == "Is it $2$?" and c["user"]["username"] == "amy" and c["edited"] is False
    assert len(c["images"]) == 1

    problem = client.get("/api/weekly/current").json()["problem"]
    assert problem["comment_count"] == 1 and problem["comments"][0]["id"] == c["id"]
    assert client.post(f"/api/weekly/{ids[LAST_WEEK]}/comments", json={"body": "late idea"}).status_code == 201
    assert client.post(f"/api/weekly/{ids[NEXT_WEEK]}/comments", json={"body": "early"}).status_code == 404


def test_comment_validation(client):
    ids = setup_weeks(client)
    sign_up(client, username="amy")
    url = f"/api/weekly/{ids[THIS_WEEK]}/comments"
    assert client.post(url, json={"body": "   "}).status_code == 422
    assert client.post(url, json={"body": "x" * 10_001}).status_code == 422
    imgs = [upload_image(client).json()["id"] for _ in range(5)]
    assert client.post(url, json={"body": "five images", "image_ids": imgs}).status_code == 422
    log_out(client)
    sign_up(client, username="bob")
    assert client.post(url, json={"body": "stolen image", "image_ids": imgs[:1]}).status_code == 422


def test_edit_own_comment_only(client):
    ids = setup_weeks(client)
    sign_up(client, username="amy")
    c = client.post(f"/api/weekly/{ids[THIS_WEEK]}/comments", json={"body": "first try"}).json()
    res = client.put(f"/api/comments/{c['id']}", json={"body": "second try"})
    assert res.status_code == 200 and res.json()["body"] == "second try" and res.json()["edited"] is True
    log_out(client)
    sign_up(client, username="bob")
    assert client.put(f"/api/comments/{c['id']}", json={"body": "hacked"}).status_code == 403
    assert client.put("/api/comments/999", json={"body": "x"}).status_code == 404


def test_admin_deletes_comments(client):
    ids = setup_weeks(client)
    sign_up(client, username="amy")
    c = client.post(f"/api/weekly/{ids[THIS_WEEK]}/comments", json={"body": "spam"}).json()
    assert client.delete(f"/api/comments/{c['id']}").status_code == 403
    log_out(client)
    client.post("/api/auth/login", json={"username": "hannah", "password": "password123"})
    assert client.delete(f"/api/comments/{c['id']}").status_code == 200
    assert client.get("/api/weekly/current").json()["problem"]["comment_count"] == 0
    assert client.delete(f"/api/comments/{c['id']}").status_code == 404


def test_real_monday_calculation():
    assert weeks.monday_of(date(2026, 10, 11)) == date(2026, 10, 5)
    assert weeks.monday_of(date(2026, 10, 12)) == date(2026, 10, 12)
