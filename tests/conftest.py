




import os
import shutil
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="mathinteract-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["HTTPS_ONLY"] = "false"
os.environ["SIGNUPS_PER_HOUR"] = "5"
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["MAX_UPLOAD_MB"] = "1"
os.environ["AUTO_SYNC"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import Base, engine
from app.main import app
from app.security import reset_limits


@pytest.fixture
def client():

    Base.metadata.drop_all(engine)
    shutil.rmtree(settings.upload_dir, ignore_errors=True)
    reset_limits()
    with TestClient(app) as c:
        yield c


def sign_up(client, username="amy", password="password123"):
    res = client.post("/api/auth/signup", json={"username": username, "password": password})
    assert res.status_code == 201, res.text
    return res.json()["user"]


def sign_up_admin(client, username="hannah"):

    from app.db import SessionLocal
    from app.security import find_user

    user = sign_up(client, username=username)
    with SessionLocal() as db:
        find_user(db, username).is_admin = True
        db.commit()
    return user
