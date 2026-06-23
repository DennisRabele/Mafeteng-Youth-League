# Running The Two Apps Locally

The project now has two distinct FastAPI apps that share one PostgreSQL database:

- Super Admin app: `app.super_admin_main:app`
- Team Admin app: `app.team_admin_main:app`

## Database

Use one shared PostgreSQL database:

```text
Database name: youth_league
Username: postgres
Password: Software
Host: localhost
Port: 5432
```

The local `.env` already points to:

```text
postgresql+psycopg://postgres:Software@localhost:5432/youth_league
```

Create the database manually if it does not exist:

```powershell
$env:PGPASSWORD='Software'
createdb -h localhost -U postgres -w youth_league
```

You do not need to manually create the tables. The app creates them from the Python models on startup. The current table set is:

```text
announcements
categories
coach_awards
coaches
fixtures
match_events
match_official_assignments
match_result_submissions
matches
news
parents
player_awards
player_documents
player_pdi
players
qr_player_cards
referees
result_verifications
seasons
super_admins
team_admins
team_seasons
teams
training_attendance
users
```

## Run Commands

From `C:\Users\DENNIS\Documents\youth league\League`:

If you previously started hidden test servers or see `WinError 10013`, first check which process owns the ports:

```powershell
Get-NetTCPConnection -LocalPort 8001,8002 -State Listen -ErrorAction SilentlyContinue
```

If a process is shown and you want to stop it:

```powershell
Stop-Process -Id <OwningProcess>
```

Then run the apps in two separate PowerShell windows.

```powershell
.\.venv\Scripts\python -m uvicorn app.super_admin_main:app --reload --host 127.0.0.1 --port 8001
```

Open:

```text
http://127.0.0.1:8001
```

In a second PowerShell window:

```powershell
.\.venv\Scripts\python -m uvicorn app.team_admin_main:app --reload --host 127.0.0.1 --port 8002
```

Open:

```text
http://127.0.0.1:8002
```

## Default Login

Super Admin:

```text
Email: admin@ydl.local
Password: Admin123!
```

Team Admins do not have a default account. They register in the Team Admin app with their own password, then the Super Admin approves or rejects them.

## Registration Rules

- Super Admins register in the Super Admin app at `/register/super-admin`.
- The system accepts a maximum of 5 Super Admin accounts.
- Super Admin registration includes a profile photo upload.
- Team Admins register in the Team Admin app at `/register/team-admin`.
- Team Admins create their own password during registration.
- Passwords are hashed in the database and are never displayed to Super Admin.
- Super Admin reviews Team Admin registration details, including profile photo, then approves or rejects.
- Approved Team Admins can log into the Team Admin app and register teams.
- Team registration includes team name, category, contact information, and logo upload.
- Super Admin reviews Team registration details, including team logo, then approves or rejects.
