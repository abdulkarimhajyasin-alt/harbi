from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import engine
from app.database.init_db import upgrade_local_schema
from app.routes import admin, auth, customers, dashboard, downloads
from app.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site="lax",
        https_only=False,
    )
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(downloads.router)
    app.include_router(customers.router)
    app.include_router(admin.router)

    @app.get("/")
    def index(request: Request):
        if request.session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    upgrade_local_schema()
