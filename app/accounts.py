

from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.security import find_user, hash_password


class LastAdminError(Exception):
    pass


def set_admin(db: Session, user: User, is_admin: bool) -> None:
    if not is_admin and user.is_admin:
        admins = db.scalar(select(func.count()).select_from(User).where(User.is_admin.is_(True)))
        if admins <= 1:
            raise LastAdminError(f"{user.username} is the only admin. Make someone else an admin first.")
    user.is_admin = is_admin
    db.commit()


def reset_password(db: Session, user: User) -> str:

    temporary = secrets.token_urlsafe(9)
    user.password_hash = hash_password(temporary)
    db.commit()
    return temporary


def apply_admin_bootstrap(db: Session, usernames: frozenset[str]) -> list[str]:


    made = []
    for name in sorted(usernames):
        user = find_user(db, name)
        if user is not None and not user.is_admin:
            user.is_admin = True
            made.append(user.username)
    db.commit()
    return made
