

from tests.conftest import sign_up, sign_up_admin


def log_out(client):
    client.post("/api/auth/logout")


def log_in(client, name, password="password123"):
    return client.post("/api/auth/login", json={"username": name, "password": password})


def user_id(client, name):
    return next(u["id"] for u in client.get(f"/api/admin/users?q={name}").json()["users"] if u["username"].lower() == name.lower())


def test_admin_only(client):
    urls = ["/api/admin/overview", "/api/admin/users"]
    for url in urls:
        assert client.get(url).status_code == 401
    sign_up(client, username="student")
    for url in urls:
        assert client.get(url).status_code == 403
    assert client.post("/api/admin/users/1/admin", json={"is_admin": True}).status_code == 403
    assert client.post("/api/admin/users/1/reset-password").status_code == 403


def test_overview(client):
    sign_up(client, username="amy")
    client.post("/api/questions", json={"title": "Q", "body": "B", "topic": "general"})
    log_out(client)
    sign_up_admin(client)
    data = client.get("/api/admin/overview").json()
    assert (data["counts"]["users"], data["counts"]["admins"], data["counts"]["questions"]) == (2, 1, 1)
    assert [s["source"] for s in data["scrapers"]] == ["aops", "cemc", "cms"]
    assert data["scrapers"][0]["status"] == "never" and data["scrapers"][1]["section"] == "canada"
    assert isinstance(data["disk"]["files"], int) and isinstance(data["disk"]["database"], int)


def test_user_list_search_posts_and_pages(client):
    sign_up(client, username="amy")
    client.post("/api/questions", json={"title": "Q", "body": "B", "topic": "general"})
    q = client.get("/api/questions").json()["questions"][0]
    client.post(f"/api/questions/{q['id']}/answers", json={"body": "A"})
    log_out(client)
    sign_up_admin(client)

    users = client.get("/api/admin/users").json()
    assert users["total"] == 2 and [u["username"] for u in users["users"]] == ["hannah", "amy"]
    amy = users["users"][1]
    assert amy["posts"] == 2 and amy["is_admin"] is False
    assert [u["username"] for u in client.get("/api/admin/users?q=AM").json()["users"]] == ["amy"]
    assert client.get("/api/admin/users?q=_").json()["total"] == 0


def test_make_and_remove_admin(client):
    sign_up(client, username="amy")
    log_out(client)
    sign_up_admin(client)
    amy = user_id(client, "amy")
    res = client.post(f"/api/admin/users/{amy}/admin", json={"is_admin": True})
    assert res.status_code == 200 and res.json()["is_admin"] is True


    log_out(client)
    log_in(client, "amy")
    hannah = user_id(client, "hannah")
    assert client.post(f"/api/admin/users/{hannah}/admin", json={"is_admin": False}).status_code == 200
    log_out(client)
    log_in(client, "hannah")
    assert client.get("/api/admin/overview").status_code == 403


def test_last_admin_cannot_be_removed(client):
    sign_up_admin(client)
    me = user_id(client, "hannah")
    res = client.post(f"/api/admin/users/{me}/admin", json={"is_admin": False})
    assert res.status_code == 409 and "only admin" in res.json()["detail"]
    assert client.get("/api/admin/overview").status_code == 200
    assert client.post("/api/admin/users/999/admin", json={"is_admin": True}).status_code == 404


def test_reset_password(client):
    sign_up(client, username="amy")
    log_out(client)
    sign_up_admin(client)
    res = client.post(f"/api/admin/users/{user_id(client, 'amy')}/reset-password")
    assert res.status_code == 200
    temporary = res.json()["temporary_password"]
    assert res.json()["username"] == "amy" and len(temporary) >= 12
    log_out(client)
    assert log_in(client, "amy").status_code == 401
    assert log_in(client, "amy", temporary).status_code == 200
    assert client.post("/api/admin/users/999/reset-password").status_code in (403, 404)
