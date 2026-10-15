

from argparse import Namespace

import pytest

import manage
from app.db import SessionLocal
from tests.conftest import sign_up


def run(command, username):
    with SessionLocal() as db:
        command(db, Namespace(username=username))


def is_admin(client):
    return client.get("/api/auth/me").json()["user"]["is_admin"]


def test_make_and_remove_admin(client):
    sign_up(client, username="hannah")
    run(manage.make_admin, "Hannah")
    assert is_admin(client) is True

    sign_up(client, username="bob")
    run(manage.make_admin, "bob")
    run(manage.remove_admin, "bob")
    assert is_admin(client) is False


def test_cannot_remove_last_admin(client):
    sign_up(client, username="hannah")
    run(manage.make_admin, "hannah")
    with pytest.raises(SystemExit):
        run(manage.remove_admin, "hannah")
    assert is_admin(client) is True


def test_unknown_user(client):
    with pytest.raises(SystemExit):
        run(manage.make_admin, "nobody")


def test_reset_password_prints_working_temporary_password(client, capsys):
    sign_up(client, username="amy")
    client.post("/api/auth/logout")
    run(manage.reset_password, "amy")
    temporary = capsys.readouterr().out.split(": ")[1].split()[0]

    old = client.post("/api/auth/login", json={"username": "amy", "password": "password123"})
    new = client.post("/api/auth/login", json={"username": "amy", "password": temporary})
    assert old.status_code == 401 and new.status_code == 200


def test_admin_bootstrap_makes_existing_accounts_admins(client):
    from app import accounts
    sign_up(client, username="Hannah")
    with SessionLocal() as db:
        made = accounts.apply_admin_bootstrap(db, frozenset({"hannah", "nobody"}))
    assert made == ["Hannah"]
    assert is_admin(client) is True
