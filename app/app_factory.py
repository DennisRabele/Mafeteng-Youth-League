from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import BASE_DIR, settings
from app.db.session import init_db
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app(app_mode: str = "combined") -> FastAPI:
    title = settings.app_name
    if app_mode == "super_admin":
        title = f"{settings.app_name} - Super Admin"
    elif app_mode == "team_admin":
        title = f"{settings.app_name} - Team Admin"

    app = FastAPI(title=title, lifespan=lifespan)
    app.state.app_mode = app_mode

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    upload_dir = settings.upload_dir
    if not upload_dir.is_absolute():
        upload_dir = BASE_DIR / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    @app.middleware("http")
    async def app_mode_guard(request: Request, call_next):
        path = request.url.path
        if app_mode == "super_admin":
            blocked = path.startswith("/team-admin") or path.startswith(
                "/register/team-admin"
            )
            if blocked:
                return RedirectResponse("/login", status_code=303)

        if app_mode == "team_admin" and (
            path.startswith("/super-admin") or path.startswith("/register/super-admin")
        ):
            return RedirectResponse("/login", status_code=303)

        return await call_next(request)

    app.include_router(web_router)
    return app
