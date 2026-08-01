import asyncio
from contextlib import asynccontextmanager, suppress
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.core.config import BASE_DIR, settings
from app.db.session import SessionLocal, init_db
from app.services.league import purge_expired_match_day_squads
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _should_init_db():
        init_db()

    async def _cleanup_match_day_squads() -> None:
        while True:
            await asyncio.sleep(3600)
            with SessionLocal() as db:
                purge_expired_match_day_squads(db)

    cleanup_task = asyncio.create_task(_cleanup_match_day_squads())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


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
    if _using_local_upload_storage():
        upload_dir = settings.upload_dir
        if not upload_dir.is_absolute():
            upload_dir = BASE_DIR / upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        favicon_path = static_dir / "images" / "logo.jpg"
        if not favicon_path.is_file():
            return Response(status_code=204)
        return FileResponse(favicon_path, media_type="image/jpeg")

    @app.middleware("http")
    async def strip_vercel_api_prefix(request: Request, call_next):
        path = request.scope.get("path", "")
        if path.startswith("/api/index"):
            request.scope["path"] = path.removeprefix("/api/index") or "/"
        elif path.startswith("/api/super_admin"):
            request.scope["path"] = path.removeprefix("/api/super_admin") or "/"
        return await call_next(request)

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


def _using_supabase_storage() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def _using_cloudinary_storage() -> bool:
    return bool(
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
    )


def _using_local_upload_storage() -> bool:
    return not _using_supabase_storage() and not _using_cloudinary_storage()


def _should_init_db() -> bool:
    if _is_vercel_deployment():
        return True
    raw_value = os.getenv("RUN_DB_INIT")
    if raw_value is not None:
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}
    return True


def _is_vercel_deployment() -> bool:
    return bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("VERCEL_URL"))
