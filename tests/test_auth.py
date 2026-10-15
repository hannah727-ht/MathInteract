

from tests.conftest import sign_up




def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_me_logged_out(client):
    assert client.get("/api/auth/me").json() == {"user": None}




def test_signup_logs_in(client):
    user = sign_up(client, username="Amy")
    assert user["username"] == "Amy" and user["is_admin"] is False
    me = client.get("/api/auth/me").json()["user"]
    assert me == user
    assert "password_hash" not in me


def test_signup_rejects_bad_input(client):
    cases = [
        {"username": "a", "password": "password123"},
        {"username": "amy smith", "password": "password123"},
        {"username": "a" * 21, "password": "password123"},
        {"username": "amy", "password": "short"},
        {"username": "amy"},
    ]
    for body in cases:
        res = client.post("/api/auth/signup", json=body)
        assert res.status_code == 422, body
        assert isinstance(res.json()["detail"], str)


def test_username_must_be_unique_ignoring_case(client):
    sign_up(client, username="Amy")
    for name in ("Amy", "amy", "AMY"):
        res = client.post("/api/auth/signup", json={"username": name, "password": "password123"})
        assert res.status_code == 409
        assert "taken" in res.json()["detail"]


def test_signup_limit_per_network(client):
    for i in range(5):
        sign_up(client, username=f"user{i}")
    res = client.post("/api/auth/signup", json={"username": "user5", "password": "password123"})
    assert res.status_code == 429




def test_logout_then_login_any_case(client):
    sign_up(client, username="Amy")
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").json() == {"user": None}

    res = client.post("/api/auth/login", json={"username": "amy", "password": "password123"})
    assert res.status_code == 200
    assert client.get("/api/auth/me").json()["user"]["username"] == "Amy"


def test_login_wrong_password_and_unknown_user(client):
    sign_up(client)
    client.post("/api/auth/logout")
    for body in [{"username": "amy", "password": "wrongpass1"},
                 {"username": "nobody", "password": "password123"}]:
        res = client.post("/api/auth/login", json=body)
        assert res.status_code == 401
        assert res.json()["detail"] == "Wrong username or password."




def test_change_password(client):
    sign_up(client)
    res = client.post("/api/auth/password", json={"current_password": "password123", "new_password": "brandnew123"})
    assert res.status_code == 200
    client.post("/api/auth/logout")

    old = client.post("/api/auth/login", json={"username": "amy", "password": "password123"})
    new = client.post("/api/auth/login", json={"username": "amy", "password": "brandnew123"})
    assert old.status_code == 401 and new.status_code == 200


def test_change_password_errors(client):
    body = {"current_password": "password123", "new_password": "brandnew123"}
    assert client.post("/api/auth/password", json=body).status_code == 401

    sign_up(client)
    wrong = client.post("/api/auth/password", json={**body, "current_password": "nope12345"})
    assert wrong.status_code == 400
    short = client.post("/api/auth/password", json={**body, "new_password": "short"})
    assert short.status_code == 422




def test_account_locks_after_ten_wrong_passwords(client):
    sign_up(client)
    client.post("/api/auth/logout")
    wrong = {"username": "amy", "password": "wrongpass1"}
    for _ in range(10):
        assert client.post("/api/auth/login", json=wrong).status_code == 401

    res = client.post("/api/auth/login", json={"username": "AMY", "password": "password123"})
    assert res.status_code == 429 and "this account" in res.json()["detail"]


def test_one_locked_account_doesnt_block_others_on_the_same_network(client):
    sign_up(client, username="amy")
    sign_up(client, username="bob")
    client.post("/api/auth/logout")
    for _ in range(10):
        client.post("/api/auth/login", json={"username": "amy", "password": "wrongpass1"})
    assert client.post("/api/auth/login", json={"username": "bob", "password": "password123"}).status_code == 200


def test_network_cap_across_many_accounts(client):
    for i in range(100):
        assert client.post("/api/auth/login", json={"username": f"user{i}", "password": "password123"}).status_code == 401
    res = client.post("/api/auth/login", json={"username": "someone", "password": "x"})
    assert res.status_code == 429 and "your network" in res.json()["detail"]


def test_successful_login_clears_wrong_tries(client):
    sign_up(client)
    client.post("/api/auth/logout")
    for _ in range(9):
        client.post("/api/auth/login", json={"username": "amy", "password": "wrongpass1"})
    assert client.post("/api/auth/login", json={"username": "amy", "password": "password123"}).status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"username": "amy", "password": "wrongpass1"}).status_code == 401


def test_fake_forwarded_addresses_dont_bypass_limits(client, monkeypatch):

    import dataclasses

    from app import security
    monkeypatch.setattr(security, "settings", dataclasses.replace(security.settings, proxy_hops=1))

    def signup(name, forwarded):
        return client.post("/api/auth/signup", json={"username": name, "password": "password123"},
                           headers={"X-Forwarded-For": forwarded})

    for i in range(5):
        assert signup(f"user{i}", f"10.0.0.{i}, 203.0.113.7").status_code == 201
    assert signup("user5", "10.0.0.99, 203.0.113.7").status_code == 429
    assert signup("user6", "198.51.100.4").status_code == 201
