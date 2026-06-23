import os

from app.app_factory import create_app


def _app_mode() -> str:
    mode = os.getenv("APP_MODE", "combined").strip().lower()
    if mode not in {"combined", "team_admin", "super_admin"}:
        return "combined"
    return mode


app = create_app(_app_mode())
