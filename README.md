# Mafeteng Youth Development League

FastAPI web app for the Youth Development League. The first sprint focuses on registration and approval for Team Admins, Teams, and Players, with the full EERD/class-diagram data model represented in SQLAlchemy.

## Stack

- Python FastAPI
- PostgreSQL through SQLAlchemy/psycopg
- Jinja2 server-rendered pages
- Supabase Storage for uploads, with local disk fallback only when Supabase env vars are absent

## Project Map

- Project name: set in `.env` as `APP_NAME`. The default is `Mafeteng Youth Development League`.
- HTML pages: `app/templates/`
- Shared header/footer layout: `app/templates/base.html`
- Main stylesheet: `app/static/css/styles.css`
- Dashboard/loading behavior: `app/static/js/dashboard.js`
- Logo file location: `app/static/images/logo.jpg`
- Home page player photo location: `app/static/images/home.jpg`

The app stores public asset URLs in the `app_assets` database table. Local defaults are `/static/images/logo.jpg` and `/static/images/home.jpg`; when hosting with Supabase Storage, update those rows to the Supabase public URLs.

Generated IDs:

- Team Admin approval creates `admin_code` as `MDL00{number}{team initials}`, for example `MDL001BE`.
- Player approval creates `player_code` as `MDL00{number}{first two team initials}{category}`, for example `MDL001BEM15`.
- Super Admin rejection of Team Admins, teams, or players requires a short reason stored as `rejection_reason`.

## Email Verification And 2FA

Both Super Admin and Team Admin registration require email verification. Login uses email address, password, and a one-time two-factor code sent by SMTP.

Set these values in `.env` before using live email:

```powershell
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USERNAME="your-sender-email@example.com"
SMTP_PASSWORD="your-email-app-password"
SMTP_FROM_EMAIL="your-sender-email@example.com"
SMTP_FROM_NAME="Mafeteng Youth League"
```

The sender email address is required; an app password alone cannot send SMTP mail.

## Hosting Notes

- Supabase/Postgres: set `DATABASE_URL` to the Supabase pooled Postgres URL, using `postgresql+psycopg://...` and `sslmode=require`.
- Supabase Storage: set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, and make the buckets public so stored URLs render in the app. The bucket names used by this repo are `admin photos`, `team logos`, `player documents`, `player photos`, and `player agreements`.
- Vercel frontend: the current app is server-rendered FastAPI/Jinja. A Vercel frontend can later consume the same backend flows through API endpoints.

## Local setup

1. For local PostgreSQL, create a database named `youth_league`. For Supabase, use the pooled connection string in `.env`.
2. Copy `.env.example` to `.env` and fill in `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and SMTP values as needed.
3. Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

4. Run the two apps:

```powershell
.\.venv\Scripts\python -m uvicorn app.super_admin_main:app --reload --port 8001
.\.venv\Scripts\python -m uvicorn app.team_admin_main:app --reload --port 8002
```

The startup task creates the tables, the default season/categories, and the default Super Admin account from `.env`. Both apps share the same PostgreSQL database.

See [docs/run_two_apps.md](docs/run_two_apps.md) for the database name, table list, ports, and full run steps.

Default Super Admin from `.env.example`:

- Email: `admin@ydl.local`
- Password: `Admin123!`

## Sprint 1 Scope

- Prospective Team Admin registration starts as pending.
- Super Admin approves or rejects Team Admins.
- Approved and email-verified Team Admins can log in with 2FA and submit team/player registrations.
- Teams start as pending and become fixture-eligible only after Super Admin approval.
- Players are age-classified into U13/U15/U17/U20 where eligible.
- Approved players receive a QR player card record.
