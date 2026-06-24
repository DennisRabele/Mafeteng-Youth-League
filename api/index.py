import os

from app.app_factory import create_app


def _app_mode() -> str:
    vercel_hint = (
        os.getenv("VERCEL_URL")
        or os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
        or os.getenv("VERCEL_PROJECT_NAME")
        or ""
    ).strip().lower()
    compact_hint = vercel_hint.replace("-", "").replace("_", "").replace(".", "")
    if "superadmin" in compact_hint:
        return "super_admin"
    if "teamadmin" in compact_hint:
        return "team_admin"

    mode = os.getenv("APP_MODE", "combined").strip().lower()
    if mode in {"team_admin", "super_admin", "combined"}:
        return mode

    return "combined"


app = create_app(_app_mode())
