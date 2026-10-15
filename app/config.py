

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


load_dotenv(ROOT_DIR / ".env")


def _flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str
    https_only: bool
    signups_per_hour: int
    upload_dir: Path
    max_upload_mb: int
    auto_sync: bool
    sync_interval_hours: int
    proxy_hops: int
    admin_bootstrap: frozenset[str]


DEV_SECRET = "dev-only-secret"


def load_settings() -> Settings:
    if _flag("HTTPS_ONLY") and os.environ.get("SECRET_KEY", DEV_SECRET) == DEV_SECRET:

        raise RuntimeError("SECRET_KEY must be set to a long random value when HTTPS_ONLY is true.")
    return Settings(
        secret_key=os.environ.get("SECRET_KEY", DEV_SECRET),
        database_url=os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'mathinteract.db'}"),
        https_only=_flag("HTTPS_ONLY"),
        signups_per_hour=int(os.environ.get("SIGNUPS_PER_HOUR", "30")),
        upload_dir=Path(os.environ.get("UPLOAD_DIR", DATA_DIR / "uploads")),
        max_upload_mb=int(os.environ.get("MAX_UPLOAD_MB", "25")),
        auto_sync=_flag("AUTO_SYNC", "false"),
        sync_interval_hours=int(os.environ.get("SYNC_INTERVAL_HOURS", "24")),

        proxy_hops=int(os.environ.get("PROXY_HOPS", "0")),

        admin_bootstrap=frozenset(n.strip().lower() for n in os.environ.get("ADMIN_BOOTSTRAP", "").split(",") if n.strip()),
    )


settings = load_settings()
