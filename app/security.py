

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

_password_hash = PasswordHash.recommended()




def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)




def find_user(db: Session, username: str) -> User | None:

    return db.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))




def client_ip(request: Request) -> str:






    if settings.proxy_hops:
        forwarded = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
        if len(forwarded) >= settings.proxy_hops:
            return forwarded[-settings.proxy_hops]
    return request.client.host if request.client else "unknown"


class RateLimit:


    def __init__(self, limit: int, window: int, message: str) -> None:
        self.limit, self.window, self.message = limit, window, message
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, ip: str) -> deque[float]:
        events, now = self._events[ip], time.monotonic()
        while events and now - events[0] > self.window:
            events.popleft()
        return events

    def check(self, ip: str) -> None:

        if len(self._recent(ip)) >= self.limit:
            raise HTTPException(status_code=429, detail=self.message)

    def record(self, ip: str) -> None:
        self._recent(ip).append(time.monotonic())

    def clear(self, ip: str) -> None:
        self._events.pop(ip, None)

    def reset(self) -> None:
        self._events.clear()



signup_limit = RateLimit(settings.signups_per_hour, 3600, "Too many new accounts from your network. Please try again later.")


account_login_limit = RateLimit(10, 15 * 60, "Too many wrong passwords for this account. Please wait 15 minutes and try again.")

network_login_limit = RateLimit(100, 15 * 60, "Too many wrong tries from your network. Please wait 15 minutes and try again.")


def reset_limits() -> None:

    signup_limit.reset()
    account_login_limit.reset()
    network_login_limit.reset()




def log_in(request: Request, user: User) -> None:
    request.session["user_id"] = user.id


def log_out(request: Request) -> None:
    request.session.clear()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    return db.get(User, user_id) if user_id is not None else None


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Please log in first.")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can do this.")
    return user
