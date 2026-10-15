







from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.security import client_ip
from app.db import SessionLocal, init_db
from app import accounts, analytics, sync
from app.routers import admin, auth, images, qa, resources, weekly
from app.routers import sync as sync_router

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.admin_bootstrap:
        with SessionLocal() as db:
            accounts.apply_admin_bootstrap(db, settings.admin_bootstrap)
    sync.mark_interrupted_runs()
    stop = threading.Event()
    if settings.auto_sync:
        sync.start_scheduler(stop)
    yield
    stop.set()


app = FastAPI(title="MathInteract", description="Learn and discuss math.", lifespan=lifespan)



@app.middleware("http")
async def count_page_views(request: Request, call_next):

    response = await call_next(request)
    if request.method == "GET" and response.status_code in (200, 304):
        page = analytics.page_key(request.url.path, request.query_params)
        if page:
            await run_in_threadpool(analytics.record_view, page, client_ip(request),
                                    request.headers.get("user-agent", ""), request.session.get("user_id"))
    return response



app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="mi_session",
    max_age=30 * 24 * 3600,
    same_site="lax",
    https_only=settings.https_only,
)


@app.exception_handler(RequestValidationError)
async def friendly_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:

    error = exc.errors()[0]
    field = error["loc"][-1] if error["loc"] else ""
    if error["type"] == "missing":
        message = f"Please fill in {field}."
    else:
        message = error["msg"]
        if message.startswith("Value error, "):
            message = message[len("Value error, "):]
    return JSONResponse(status_code=422, content={"detail": message})


app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(sync_router.router)
app.include_router(images.router)
app.include_router(weekly.router)
app.include_router(qa.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}




app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
