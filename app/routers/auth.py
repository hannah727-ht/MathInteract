





from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import (
    account_login_limit, client_ip, find_user, get_current_user, hash_password, log_in, log_out,
    network_login_limit, require_user, signup_limit, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,20}$")

_DUMMY_HASH = hash_password("not-a-real-password")




def _check_password(v: str) -> str:
    if not 8 <= len(v) <= 128:
        raise ValueError("Password must be at least 8 characters.")
    return v


class SignupIn(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str) -> str:
        v = v.strip()
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3–20 characters: letters, digits, _ or -.")
        return v

    password_rule = field_validator("password")(_check_password)


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    password_rule = field_validator("new_password")(_check_password)




@router.get("/me")
def me(user: User | None = Depends(get_current_user)) -> dict:

    return {"user": user.public() if user else None}


@router.post("/signup", status_code=201)
def signup(body: SignupIn, request: Request, db: Session = Depends(get_db)) -> dict:

    if find_user(db, body.username) is not None:
        raise HTTPException(status_code=409, detail="This username is taken. Please choose another.")
    ip = client_ip(request)
    signup_limit.check(ip)
    signup_limit.record(ip)

    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This username is taken. Please choose another.")
    log_in(request, user)
    return {"user": user.public()}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> dict:
    ip, account = client_ip(request), body.username.strip().lower()

    account_login_limit.check(account)
    network_login_limit.check(ip)
    user = find_user(db, body.username)
    password_hash = user.password_hash if user else _DUMMY_HASH
    if not verify_password(body.password, password_hash) or user is None:
        account_login_limit.record(account)
        network_login_limit.record(ip)
        raise HTTPException(status_code=401, detail="Wrong username or password.")
    account_login_limit.clear(account)
    log_in(request, user)
    return {"user": user.public()}


@router.post("/logout")
def logout(request: Request) -> dict:
    log_out(request)
    return {"ok": True}


@router.post("/password")
def change_password(
    body: ChangePasswordIn, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> dict:

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Your current password is wrong.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
