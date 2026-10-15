








from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app import accounts
from app.db import SessionLocal, init_db
from app.models import User
from app.security import find_user


def get_user(db, username: str) -> User:
    user = find_user(db, username)
    if user is None:
        sys.exit(f"No user named '{username}'. Sign up on the website first, then run this again.")
    return user


def list_users(db, _args) -> None:
    users = db.scalars(select(User).order_by(User.created_at)).all()
    if not users:
        print("No users yet.")
    for u in users:
        print(f"{u.username:<20} {'admin' if u.is_admin else 'user':<6} joined {u.created_at:%Y-%m-%d}")


def make_admin(db, args) -> None:
    user = get_user(db, args.username)
    accounts.set_admin(db, user, True)
    print(f"{user.username} is now an admin.")


def remove_admin(db, args) -> None:
    user = get_user(db, args.username)
    try:
        accounts.set_admin(db, user, False)
    except accounts.LastAdminError as e:
        sys.exit(str(e))
    print(f"{user.username} is no longer an admin.")


def reset_password(db, args) -> None:
    user = get_user(db, args.username)
    temporary = accounts.reset_password(db, user)
    print(f"New temporary password for {user.username}: {temporary}")
    print("Tell them to log in with it and change it on their Account page.")


def main() -> None:
    parser = argparse.ArgumentParser(description="MathInteract account tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-users", help="show every account").set_defaults(run=list_users)
    for name, run, text in [
        ("make-admin", make_admin, "give a user admin rights"),
        ("remove-admin", remove_admin, "take admin rights away"),
        ("reset-password", reset_password, "set a random temporary password"),
    ]:
        command = commands.add_parser(name, help=text)
        command.add_argument("username")
        command.set_defaults(run=run)

    args = parser.parse_args()
    init_db()
    with SessionLocal() as db:
        args.run(db, args)


if __name__ == "__main__":
    main()
