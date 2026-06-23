# Requirements Diagram Mapping

This file records how the DOCX diagrams map into the current FastAPI codebase.

## EERD and Class Diagram

Core user specialization:

- `User`: `user_id`, `full_name`, `email`, `password_hash`, `role`, `email_verified`, email verification code fields, login code fields
- `TeamAdmin`: `team_admin_id`, `national_id`, `phone`, `requested_team_name`, `admin_code`, `rejection_reason`, linked one-to-one with `User`
- `SuperAdmin`: `admin_id`, linked one-to-one with `User`

League setup:

- `Season`: `season_id`, `season_name`, `start_date`, `end_date`
- `Category`: `category_id`, `category_name`, linked to `Season`
- `TeamSeason`: composite team/season registration with `registration_date`

Registration and people:

- `Team`: `team_id`, `team_name`, `logo`, `status`, `contact_information`, `team_address`, `training_ground`, `home_ground`, linked to `TeamAdmin` and `Category`
- `Parent`: `parent_id`, `name`, `contact`
- `Player`: `player_id`, `full_name`, `gender`, `dob`, `nationality`, `email`, `residential_address`, `registration_type`, `agreement_form_path`, `player_code`, `rejection_reason`
- `PlayerDocument`: `document_id`, `document_type`, `file_path`
- `PlayerRegistrationRequest`: new, renewal, or transfer registration audit record with agreement form URL
- `PlayerTransferRequest`: transfer workflow record with source team, destination team, transfer type, conditions, response explanation, and status
- `QRPlayerCard`: `card_id`, `qr_code`, `issue_date`
- `PlayerPDI`: `pdi_id`, `score`, `rating`
- `TrainingAttendance`: `attendance_id`, `date`, `status`
- `PlayerAward`: `award_id`, `award_name`, `season`
- `Coach`: `coach_id`, `qualification`
- `CoachAward`: `award_id`, `award_name`, `season`

Competition and publishing:

- `Fixture`: `fixture_id`, `fixture_date`, `venue`, `status`
- `Match`: `match_id`, `match_date`, `status`
- `MatchEvent`: `event_id`, `event_type`, `minute`
- `Referee`: `referee_id`, `qualification`
- `MatchOfficialAssignment`: `assignment_id`, `role`
- `MatchResultSubmission`: `submission_id`, `submitted_date`, `status`
- `ResultVerification`: `verification_id`, `verification_date`, `decision`
- `News`: `news_id`, `title`, `content`, `date_posted`
- `Announcement`: `announcement_id`, `title`, `content`, `date_posted`

Some workflow fields are added where the sequence diagrams require state transitions, for example `status` on Team Admin and Player registration.

## Sequence Diagram Implementation

Team Admin registration:

- Public form captures full name, team name, national ID, phone, email, password, and profile photo.
- Registration sends an SMTP email verification code and the account must be verified before login.
- Registration is saved as `pending`.
- Super Admin approves or rejects from `/super-admin`.
- Approval generates a Team Admin ID in the `MDL00{number}{team initials}` format, for example `MDL001BE`.
- Rejection requires a short explanation, saved as `rejection_reason`.
- Approval activates the Team Admin. The Team Admin logs in with the password created during registration.
- Passwords are hashed and are never displayed to Super Admin.

Super Admin registration:

- Public form captures full name, email, password, and profile photo.
- Registration sends an SMTP email verification code and the account must be verified before login.
- The system accepts a maximum of five Super Admin accounts.
- Passwords are hashed before storage.

Login:

- Login captures email address, password, and an optional one-time 2FA code.
- First valid email/password submission sends a one-time login code by SMTP.
- The user submits the same credentials with the one-time code to create a session.

Team registration:

- Approved Team Admin logs in.
- Team Admin submits team name, category, contact information, team address, training ground, home ground, and optional logo.
- Team is saved as `pending`.
- Rejection requires a short explanation that the Team Admin can see from their dashboard.
- Super Admin approval changes status to `approved` and creates the `TeamSeason` registration record.

Player registration:

- Approved Team Admin opens Players Registration and chooses New Player, Renewal Registration, or Transfer Registration.
- New Player keeps player, parent, school, photo, identity document, parent consent picture, and optional medical certificate data, and requires a player-club agreement upload instead of jersey number.
- Renewal Registration only requires selecting an existing player and uploading the player-club agreement.
- Transfer Registration lets the current club request a loan or permanent transfer to another approved team, records player details and transfer conditions, and lets the receiving club agree or disagree with an explanation.
- When the receiving club registers an agreed transfer, the existing player record moves to the new team, preserving personal details, photo, and identity documents.
- Age is calculated and mapped to `U13`, `U15`, `U17`, or `U20`.
- Ineligible players are rejected immediately.
- Eligible players wait for Super Admin approval.
- Approval generates a Player ID in the `MDL00{number}{first two team initials}{category}` format, for example `MDL001BEM15`, and creates a `QRPlayerCard` record using that ID.
- Rejection requires a short explanation that the Team Admin can see from their dashboard.

Access rules:

- Team Admin dashboard queries are scoped by `Team.team_admin_id`, so Team Admins only see their own teams and players.
- Pending or rejected Team Admins can log into `/team-admin/account` to see their status and rejection explanation, but cannot access the registration dashboard until approved.

Shared visual assets:

- `AppAsset` stores public URLs for reusable assets such as `league_logo` and `home_hero_photo`.
- Local defaults point to `/static/images/logo.jpg` and `/static/images/home.jpg`.
- Hosted deployments can update these rows to Supabase Storage public URLs without changing templates.

Fixture and result flows are modeled in the database for later sprints, but their full UI workflows are intentionally left out of Sprint 1.
