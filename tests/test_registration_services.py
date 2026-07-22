from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import (
    ApprovalStatus,
    Category,
    Fixture,
    Match,
    Player,
    PlayerRegistrationRequest,
    Season,
    SuperAdmin,
    TeamAdmin,
    TransferStatus,
)
from app.services.registration import (
    RegistrationError,
    approve_player,
    approve_team,
    approve_team_admin,
    complete_transfer_registration,
    create_super_admin_registration,
    create_team_admin_registration,
    determine_age_group,
    issue_email_verification_code,
    issue_login_code,
    register_player,
    register_team,
    renew_player_registration,
    reject_player,
    reject_team,
    reject_team_admin,
    get_player_registration_expiry_date,
    process_player_registration_lifecycle,
    request_player_from_team,
    request_player_transfer,
    respond_to_transfer,
    suggested_registration_period,
    verify_email_code,
    verify_login_code,
)
from app.services.team_access import (
    load_team_admin_approved_team_ids,
    load_team_admin_approved_teams,
    load_team_admin_owned_approved_teams,
)
from app.services.league import get_player_performances
from app.services.league import submit_match_result
from app.services.league import verify_match_result
from app.web.routes import _load_result_fixture_players
import app.web.routes as routes


def make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, future=True)
    return TestingSession()


def seed_category(db):
    season = Season(
        season_name="2026 Test Season",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db.add(season)
    db.flush()
    category = Category(season_id=season.season_id, category_name="Male U17")
    db.add(category)
    db.commit()
    return category


def years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


def test_age_group_boundaries():
    reference = date(2026, 6, 10)

    assert determine_age_group(date(2013, 6, 10), reference) == "U13"
    assert determine_age_group(date(2011, 6, 10), reference) == "U15"
    assert determine_age_group(date(2009, 6, 10), reference) == "U17"
    assert determine_age_group(date(2006, 6, 10), reference) == "U20"
    assert determine_age_group(date(2005, 6, 9), reference) is None
    assert suggested_registration_period(date(2013, 6, 10), reference) == 1
    assert suggested_registration_period(date(2012, 6, 10), reference) == 2
    assert suggested_registration_period(date(2015, 6, 10), reference) == 3
    assert suggested_registration_period(date(2009, 6, 10), reference) == 1


def test_registration_approval_flow_creates_team_season_and_qr_card():
    db = make_session()
    category = seed_category(db)

    team_admin = create_team_admin_registration(
        db,
        full_name="Mpho Coach",
        team_name="Blue Eagles",
        email="mpho@example.test",
        password="Password123",
        national_id="NID-001",
        phone="+26650000000",
        photo_path="/uploads/admin-photos/mpho.png",
    )
    assert team_admin.status == ApprovalStatus.PENDING.value
    assert team_admin.user.photo_path == "/uploads/admin-photos/mpho.png"
    assert team_admin.requested_team_name == "Blue Eagles"

    original_password_hash = team_admin.user.password_hash
    team_admin = approve_team_admin(db, team_admin.team_admin_id)
    assert team_admin.status == ApprovalStatus.APPROVED.value
    assert team_admin.user.password_hash == original_password_hash
    assert team_admin.admin_code == "MDL001BE"

    team = register_team(
        db,
        team_admin_id=team_admin.team_admin_id,
        team_name="Blue Eagles",
        category_id=category.category_id,
        contact_information="+26650000001",
        team_address="Main Road, Mafeteng",
        training_ground="Mafeteng Training Ground",
        home_ground="Mafeteng Stadium",
        logo=None,
    )
    assert team.status == ApprovalStatus.PENDING.value
    assert team.team_address == "Main Road, Mafeteng"
    assert team.training_ground == "Mafeteng Training Ground"
    assert team.home_ground == "Mafeteng Stadium"

    team = approve_team(db, team.team_id)
    assert team.status == ApprovalStatus.APPROVED.value
    assert team.team_seasons

    player = register_player(
        db,
        team_id=team.team_id,
        full_name="Neo Striker",
        gender="Male",
        dob=years_ago(17),
        nationality="Mosotho",
        email="neo@example.test",
        residential_address="House 12, Mafeteng",
        parent_name="Parent One",
        parent_contact="+26650000002",
        school_name="Mafeteng High",
        position="Forward",
        agreement_form_path="/uploads/player-agreements/neo.pdf",
        photo_path=None,
        documents=[],
        registration_period=1,
    )
    assert player.status == ApprovalStatus.PENDING.value
    assert player.age_group == "U17"
    assert player.registration_period == 1
    assert player.email == "neo@example.test"
    assert player.residential_address == "House 12, Mafeteng"
    assert player.agreement_form_path == "/uploads/player-agreements/neo.pdf"
    assert player.registration_requests[0].registration_type == "new"

    player = approve_player(db, player.player_id)
    assert player.status == ApprovalStatus.APPROVED.value
    assert player.player_code == "MDL001BEM17"
    assert player.qr_player_card is not None
    assert player.qr_player_card.qr_code == player.player_code


def test_additional_team_admin_can_register_with_team_code_only():
    db = make_session()
    category = seed_category(db)

    first_admin = create_team_admin_registration(
        db,
        full_name="First Admin",
        team_name="Blue Eagles",
        email="first@example.test",
        password="Password123",
        national_id="NID-FIRST",
        phone="+26650000010",
        photo_path="/uploads/admin-photos/first.png",
    )
    first_admin = approve_team_admin(db, first_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=first_admin.team_admin_id,
        team_name="Blue Eagles",
        category_id=category.category_id,
        contact_information="+26650000011",
        team_address="Main Road",
        training_ground="Training Ground",
        home_ground="Home Ground",
        logo="/uploads/team-logos/blue-eagles.png",
    )
    team = approve_team(db, team.team_id)

    second_admin = create_team_admin_registration(
        db,
        full_name="Second Admin",
        team_name=None,
        email="second@example.test",
        password="Password123",
        national_id="NID-SECOND",
        phone="+26650000012",
        photo_path="/uploads/admin-photos/second.png",
        team_code=team.team_code,
    )

    assert second_admin.requested_team_name == "Blue Eagles"
    assert second_admin.team_id == team.team_id


def test_approved_team_admins_can_see_their_linked_team_code_and_access():
    db = make_session()
    category = seed_category(db)

    first_admin = create_team_admin_registration(
        db,
        full_name="Primary Admin",
        team_name="North Stars",
        email="primary@example.test",
        password="Password123",
        national_id="NID-PRIMARY",
        phone="+26650000013",
        photo_path="/uploads/admin-photos/primary.png",
    )
    first_admin = approve_team_admin(db, first_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=first_admin.team_admin_id,
        team_name="North Stars",
        category_id=category.category_id,
        contact_information="+26650000014",
        team_address="North Road",
        training_ground="North Training",
        home_ground="North Ground",
        logo="/uploads/team-logos/north-stars.png",
    )
    team = approve_team(db, team.team_id)

    assert db.get(TeamAdmin, first_admin.team_admin_id).team_id == team.team_id
    approved_teams = load_team_admin_approved_teams(db, first_admin.team_admin_id)
    assert [item.team_id for item in approved_teams] == [team.team_id]
    assert load_team_admin_approved_team_ids(db, first_admin.team_admin_id) == [team.team_id]

    colleague_admin = create_team_admin_registration(
        db,
        full_name="Colleague Admin",
        team_name=None,
        email="colleague@example.test",
        password="Password123",
        national_id="NID-COLLEAGUE",
        phone="+26650000015",
        photo_path="/uploads/admin-photos/colleague.png",
        team_code=team.team_code,
    )
    assert colleague_admin.team_id == team.team_id

    colleague_admin = approve_team_admin(db, colleague_admin.team_admin_id)
    assert load_team_admin_approved_team_ids(db, colleague_admin.team_admin_id) == [team.team_id]
    colleague_teams = load_team_admin_approved_teams(db, colleague_admin.team_admin_id)
    assert len(colleague_teams) == 1
    assert colleague_teams[0].team_code == team.team_code


def test_approved_result_updates_player_performances():
    db = make_session()
    category = seed_category(db)

    home_admin = create_team_admin_registration(
        db,
        full_name="Home Admin",
        team_name="Home FC",
        email="home-admin@example.test",
        password="Password123",
        national_id="NID-HOME-PERF",
        phone="+26650000040",
        photo_path="/uploads/admin-photos/home-admin.png",
    )
    home_admin = approve_team_admin(db, home_admin.team_admin_id)
    home_team = register_team(
        db,
        team_admin_id=home_admin.team_admin_id,
        team_name="Home FC",
        category_id=category.category_id,
        contact_information="+26650000041",
        team_address="Home Road",
        training_ground="Home Ground",
        home_ground="Home Stadium",
        logo="/uploads/team-logos/home-fc.png",
    )
    home_team = approve_team(db, home_team.team_id)

    away_admin = create_team_admin_registration(
        db,
        full_name="Away Admin",
        team_name="Away FC",
        email="away-admin@example.test",
        password="Password123",
        national_id="NID-AWAY-PERF",
        phone="+26650000042",
        photo_path="/uploads/admin-photos/away-admin.png",
    )
    away_admin = approve_team_admin(db, away_admin.team_admin_id)
    away_team = register_team(
        db,
        team_admin_id=away_admin.team_admin_id,
        team_name="Away FC",
        category_id=category.category_id,
        contact_information="+26650000043",
        team_address="Away Road",
        training_ground="Away Ground",
        home_ground="Away Stadium",
        logo="/uploads/team-logos/away-fc.png",
    )
    away_team = approve_team(db, away_team.team_id)

    super_admin = create_super_admin_registration(
        db,
        full_name="Super Admin",
        email="super@example.test",
        password="Password123",
        photo_path=None,
    )

    home_scorer = register_player(
        db,
        team_id=home_team.team_id,
        full_name="Home Scorer",
        gender="Male",
        dob=years_ago(16),
        nationality="Mosotho",
        email="home-scorer@example.test",
        residential_address="Home Address",
        parent_name="Parent Home",
        parent_contact="+26650000044",
        school_name="Home School",
        position="Forward",
        agreement_form_path="/uploads/player-agreements/home-scorer.pdf",
        photo_path=None,
        documents=[],
        registration_period=1,
    )
    home_scorer = approve_player(db, home_scorer.player_id)

    home_assister = register_player(
        db,
        team_id=home_team.team_id,
        full_name="Home Assister",
        gender="Male",
        dob=years_ago(16),
        nationality="Mosotho",
        email="home-assister@example.test",
        residential_address="Home Address",
        parent_name="Parent Home Two",
        parent_contact="+26650000045",
        school_name="Home School",
        position="Midfielder",
        agreement_form_path="/uploads/player-agreements/home-assister.pdf",
        photo_path=None,
        documents=[],
        registration_period=1,
    )
    home_assister = approve_player(db, home_assister.player_id)

    away_scorer = register_player(
        db,
        team_id=away_team.team_id,
        full_name="Away Scorer",
        gender="Male",
        dob=years_ago(16),
        nationality="Mosotho",
        email="away-scorer@example.test",
        residential_address="Away Address",
        parent_name="Parent Away",
        parent_contact="+26650000046",
        school_name="Away School",
        position="Forward",
        agreement_form_path="/uploads/player-agreements/away-scorer.pdf",
        photo_path=None,
        documents=[],
        registration_period=1,
    )
    away_scorer = approve_player(db, away_scorer.player_id)

    fixture = Fixture(
        season_id=category.season_id,
        category_id=category.category_id,
        home_team_id=home_team.team_id,
        away_team_id=away_team.team_id,
        fixture_date=datetime.utcnow() - timedelta(days=1),
        venue="Performance Ground",
        status="completed",
    )
    db.add(fixture)
    db.flush()
    db.add(
        Match(
            fixture_id=fixture.fixture_id,
            match_date=fixture.fixture_date,
            status="completed",
            home_score=1,
            away_score=0,
        )
    )
    db.commit()

    submission = submit_match_result(
        db,
        team_admin_id=home_admin.team_admin_id,
        fixture_id=fixture.fixture_id,
        home_score=1,
        away_score=0,
        scorer_names_text="Home Scorer",
        goal_types_text="Open Play",
        assist_names_text="Home Assister",
    )
    assert submission.status == ApprovalStatus.PENDING.value

    performances_before = get_player_performances(db)
    assert all(not rows for rows in performances_before.values())

    verified = verify_match_result(
        db,
        submission_id=submission.submission_id,
        super_admin_id=super_admin.admin_id,
        home_score=1,
        away_score=0,
        scorer_names_text="Home Scorer",
        goal_types_text="Open Play",
        assist_names_text="Home Assister",
        decision=ApprovalStatus.APPROVED.value,
    )
    assert verified.status == ApprovalStatus.APPROVED.value

    performances = get_player_performances(db)
    scorer_row = next(row for row in performances["scorers"] if row["player"].player_id == home_scorer.player_id)
    assister_row = next(row for row in performances["assisters"] if row["player"].player_id == home_assister.player_id)

    assert scorer_row["goals"] == 1
    assert scorer_row["assists"] == 0
    assert scorer_row["goal_types"] == {"Open Play": 1}
    assert assister_row["assists"] == 1


def test_approved_team_codes_are_backfilled_for_legacy_records():
    db = make_session()
    category = seed_category(db)

    admin = create_team_admin_registration(
        db,
        full_name="Legacy Admin",
        team_name="Legacy Club",
        email="legacy@example.test",
        password="Password123",
        national_id="NID-LEGACY",
        phone="+26650000018",
        photo_path="/uploads/admin-photos/legacy.png",
    )
    admin = approve_team_admin(db, admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=admin.team_admin_id,
        team_name="Legacy Club",
        category_id=category.category_id,
        contact_information="+26650000019",
        team_address="Legacy Road",
        training_ground="Legacy Training",
        home_ground="Legacy Ground",
        logo="/uploads/team-logos/legacy-club.png",
    )
    team = approve_team(db, team.team_id)
    team.team_code = None
    db.commit()

    approved_teams = load_team_admin_approved_teams(db, admin.team_admin_id)
    assert len(approved_teams) == 1
    assert approved_teams[0].team_code is not None
    assert approved_teams[0].team_code.endswith("MDL")


def test_team_admin_limit_increases_to_seven_per_team():
    db = make_session()
    category = seed_category(db)

    owner_admin = create_team_admin_registration(
        db,
        full_name="Owner Admin",
        team_name="Seven Club",
        email="owner-seven@example.test",
        password="Password123",
        national_id="NID-OWNER-SEVEN",
        phone="+26650000016",
        photo_path="/uploads/admin-photos/owner-seven.png",
    )
    owner_admin = approve_team_admin(db, owner_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=owner_admin.team_admin_id,
        team_name="Seven Club",
        category_id=category.category_id,
        contact_information="+26650000017",
        team_address="Seven Road",
        training_ground="Seven Training",
        home_ground="Seven Ground",
        logo="/uploads/team-logos/seven-club.png",
    )
    team = approve_team(db, team.team_id)

    for index in range(6):
        extra_admin = create_team_admin_registration(
            db,
            full_name=f"Colleague {['Zero','One','Two','Three','Four','Five'][index]}",
            team_name=None,
            email=f"colleague{index}-seven@example.test",
            password="Password123",
            national_id=f"NID-COLLEAGUE-SEVEN-{index}",
            phone=f"+2665000002{index}",
            photo_path=f"/uploads/admin-photos/colleague-seven-{index}.png",
            team_code=team.team_code,
        )
        assert extra_admin.team_id == team.team_id

    try:
        create_team_admin_registration(
            db,
            full_name="Colleague Seven",
            team_name=None,
            email="colleague7-seven@example.test",
            password="Password123",
            national_id="NID-COLLEAGUE-SEVEN-7",
            phone="+26650000029",
            photo_path="/uploads/admin-photos/colleague-seven-7.png",
            team_code=team.team_code,
        )
    except RegistrationError as exc:
        assert "Maximum number of team admins reached for this team." in str(exc)
    else:
        raise AssertionError("Expected the eighth admin registration to be rejected.")


def test_colleague_admin_cannot_register_clubs_but_keeps_other_team_access():
    db = make_session()
    category = seed_category(db)

    owner_admin = create_team_admin_registration(
        db,
        full_name="Owner Admin",
        team_name="Access Club",
        email="owner-access@example.test",
        password="Password123",
        national_id="NID-OWNER-ACCESS",
        phone="+26650000030",
        photo_path="/uploads/admin-photos/owner-access.png",
    )
    owner_admin = approve_team_admin(db, owner_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=owner_admin.team_admin_id,
        team_name="Access Club",
        category_id=category.category_id,
        contact_information="+26650000031",
        team_address="Access Road",
        training_ground="Access Training",
        home_ground="Access Ground",
        logo="/uploads/team-logos/access-club.png",
    )
    team = approve_team(db, team.team_id)

    colleague_admin = create_team_admin_registration(
        db,
        full_name="Colleague Access",
        team_name=None,
        email="colleague-access@example.test",
        password="Password123",
        national_id="NID-COLLEAGUE-ACCESS",
        phone="+26650000032",
        photo_path="/uploads/admin-photos/colleague-access.png",
        team_code=team.team_code,
    )
    colleague_admin = approve_team_admin(db, colleague_admin.team_admin_id)

    assert load_team_admin_approved_team_ids(db, colleague_admin.team_admin_id) == [team.team_id]
    assert load_team_admin_owned_approved_teams(db, colleague_admin.team_admin_id) == []

    redirect_calls: list[tuple[str, str, str]] = []

    def fake_redirect(*, section: str, notice: str, notice_kind: str = "success"):
        redirect_calls.append((section, notice, notice_kind))
        return {"section": section, "notice": notice, "notice_kind": notice_kind}

    with (
        patch.object(routes, "_require_team_admin", return_value=colleague_admin),
        patch.object(routes, "_team_admin_dashboard_redirect", side_effect=fake_redirect),
        patch.object(routes, "register_team") as register_team_mock,
        patch.object(routes, "_safe_upload", return_value="/uploads/team-logos/blocked.png"),
    ):
        response = routes.create_team_route(
            request=object(),
            team_name="Blocked Club",
            category_id=category.category_id,
            contact_information="+26650000033",
            team_address="Blocked Road",
            training_ground="Blocked Training",
            home_ground="Blocked Ground",
            logo=None,
            team_code=team.team_code,
            db=db,
        )

    assert response["notice_kind"] == "error"
    assert "Only the default team admin can register clubs." in response["notice"]
    assert redirect_calls
    register_team_mock.assert_not_called()


def test_default_team_admin_can_register_another_club_without_team_code():
    db = make_session()
    category = seed_category(db)

    owner_admin = create_team_admin_registration(
        db,
        full_name="Default Admin",
        team_name="Primary Club",
        email="default-admin@example.test",
        password="Password123",
        national_id="NID-DEFAULT-ADMIN",
        phone="+26650000034",
        photo_path="/uploads/admin-photos/default-admin.png",
    )
    owner_admin = approve_team_admin(db, owner_admin.team_admin_id)
    primary_team = register_team(
        db,
        team_admin_id=owner_admin.team_admin_id,
        team_name="Primary Club",
        category_id=category.category_id,
        contact_information="+26650000035",
        team_address="Primary Road",
        training_ground="Primary Training",
        home_ground="Primary Ground",
        logo="/uploads/team-logos/primary-club.png",
    )
    approve_team(db, primary_team.team_id)

    redirect_calls: list[tuple[str, str, str]] = []

    def fake_redirect(*, section: str, notice: str, notice_kind: str = "success"):
        redirect_calls.append((section, notice, notice_kind))
        return {"section": section, "notice": notice, "notice_kind": notice_kind}

    with (
        patch.object(routes, "_require_team_admin", return_value=owner_admin),
        patch.object(routes, "_team_admin_dashboard_redirect", side_effect=fake_redirect),
        patch.object(routes, "register_team", return_value=SimpleNamespace(team_name="Second Club")) as register_team_mock,
        patch.object(routes, "_safe_upload", return_value="/uploads/team-logos/second-club.png"),
        patch.object(routes, "_announce_submission"),
    ):
        response = routes.create_team_route(
            request=object(),
            team_name="Second Club",
            category_id=category.category_id,
            contact_information="+26650000036",
            team_address="Second Road",
            training_ground="Second Training",
            home_ground="Second Ground",
            logo=None,
            team_code=None,
            db=db,
        )

    assert response["notice_kind"] == "success"
    assert redirect_calls
    register_team_mock.assert_called_once()
    assert register_team_mock.call_args.kwargs["team_name"] == "Second Club"
    assert "team_code" not in register_team_mock.call_args.kwargs


def test_player_registration_expiry_reminder_is_sent_once():
    db = make_session()
    category = seed_category(db)

    team_admin = create_team_admin_registration(
        db,
        full_name="Reminder Admin",
        team_name="Gold Stars",
        email="reminder@example.test",
        password="Password123",
        national_id="NID-REMINDER",
        phone="+26650000020",
        photo_path="/uploads/admin-photos/reminder.png",
    )
    team_admin = approve_team_admin(db, team_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=team_admin.team_admin_id,
        team_name="Gold Stars",
        category_id=category.category_id,
        contact_information="+26650000021",
        team_address="Gold Road",
        training_ground="Gold Training",
        home_ground="Gold Ground",
        logo="/uploads/team-logos/gold-stars.png",
    )
    team = approve_team(db, team.team_id)

    player = register_player(
        db,
        team_id=team.team_id,
        full_name="Expiry Player",
        gender="Male",
        dob=years_ago(17),
        nationality="Mosotho",
        email=None,
        residential_address=None,
        parent_name="Parent Expiry",
        parent_contact="+26650000022",
        school_name=None,
        position="Defender",
        agreement_form_path="/uploads/player-agreements/expiry.pdf",
        photo_path="/uploads/player-photos/expiry.jpg",
        documents=[],
        registration_period=1,
    )
    approve_player(db, player.player_id)
    player.approved_at = datetime.utcnow() - timedelta(days=335)
    db.commit()

    expiry_date = get_player_registration_expiry_date(db, player)
    assert expiry_date is not None
    assert expiry_date <= date.today() + timedelta(days=30)

    stats = process_player_registration_lifecycle(db)
    assert stats["reminders_sent"] == 1
    db.refresh(player)
    assert player.registration_reminder_sent_at is not None


def test_player_registration_rejects_periods_longer_than_the_player_allows():
    db = make_session()
    category = seed_category(db)

    team_admin = create_team_admin_registration(
        db,
        full_name="Period Admin",
        team_name="Silver Hawks",
        email="period-admin@example.test",
        password="Password123",
        national_id="NID-PERIOD",
        phone="+26650000010",
        photo_path=None,
    )
    team_admin = approve_team_admin(db, team_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=team_admin.team_admin_id,
        team_name="Silver Hawks",
        category_id=category.category_id,
        contact_information="+26650000011",
        team_address="Silver Road",
        training_ground="Silver Training",
        home_ground="Silver Ground",
        logo=None,
    )
    team = approve_team(db, team.team_id)

    try:
        register_player(
            db,
            team_id=team.team_id,
            full_name="Limit Player",
            gender="Male",
            dob=years_ago(17),
            nationality="Mosotho",
            email="limit@example.test",
            residential_address=None,
            parent_name="Parent Limit",
            parent_contact="+26650000012",
            school_name=None,
            position="Forward",
            agreement_form_path="/uploads/player-agreements/limit.pdf",
            photo_path=None,
            documents=[],
            registration_period=2,
        )
    except RegistrationError as exc:
        assert "up to 1 year" in str(exc)
    else:
        raise AssertionError("Expected the overlong registration period to be rejected.")


def test_player_registration_rejects_category_mismatches_before_super_admin_flow():
    db = make_session()
    category = seed_category(db)

    team_admin = create_team_admin_registration(
        db,
        full_name="Mismatch Admin",
        team_name="Mismatch Club",
        email="mismatch-admin@example.test",
        password="Password123",
        national_id="NID-MISMATCH",
        phone="+26650000013",
        photo_path=None,
    )
    team_admin = approve_team_admin(db, team_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=team_admin.team_admin_id,
        team_name="Mismatch Club",
        category_id=category.category_id,
        contact_information="+26650000014",
        team_address="Mismatch Road",
        training_ground="Mismatch Training",
        home_ground="Mismatch Ground",
        logo=None,
    )
    team = approve_team(db, team.team_id)

    try:
        register_player(
            db,
            team_id=team.team_id,
            full_name="Too Young",
            gender="Male",
            dob=years_ago(13),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            parent_name="Parent Mismatch",
            parent_contact="+26650000015",
            school_name=None,
            position="Forward",
            agreement_form_path="/uploads/player-agreements/mismatch.pdf",
            photo_path=None,
            documents=[],
            registration_period=1,
        )
    except RegistrationError as exc:
        assert "qualifies for Male U13" in str(exc)
    else:
        raise AssertionError("Expected the category mismatch to be rejected.")

    assert db.scalars(select(Player)).all() == []
    assert db.scalars(select(PlayerRegistrationRequest)).all() == []


def test_player_registration_rejects_malformed_gender_with_clear_message():
    db = make_session()
    category = seed_category(db)

    team_admin = create_team_admin_registration(
        db,
        full_name="Gender Admin",
        team_name="Gender Club",
        email="gender-admin@example.test",
        password="Password123",
        national_id="NID-GENDER",
        phone="+26650000016",
        photo_path=None,
    )
    team_admin = approve_team_admin(db, team_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=team_admin.team_admin_id,
        team_name="Gender Club",
        category_id=category.category_id,
        contact_information="+26650000017",
        team_address="Gender Road",
        training_ground="Gender Training",
        home_ground="Gender Ground",
        logo=None,
    )
    team = approve_team(db, team.team_id)

    try:
        register_player(
            db,
            team_id=team.team_id,
            full_name="Invalid Gender Player",
            gender="Unknown",
            dob=years_ago(17),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            parent_name="Parent Gender",
            parent_contact="+26650000018",
            school_name=None,
            position="Forward",
            agreement_form_path="/uploads/player-agreements/gender.pdf",
            photo_path=None,
            documents=[],
            registration_period=1,
        )
    except RegistrationError as exc:
        assert "Player gender must be Male or Female." in str(exc)
    else:
        raise AssertionError("Expected malformed gender to be rejected.")

    assert db.scalars(select(Player)).all() == []
    assert db.scalars(select(PlayerRegistrationRequest)).all() == []


def test_super_admin_registration_is_limited_to_five_accounts():
    db = make_session()

    for index in range(5):
        super_admin = create_super_admin_registration(
            db,
            full_name=f"Admin {index}",
            email=f"admin{index}@example.test",
            password="Password123",
            photo_path=f"/uploads/admin-photos/admin{index}.png",
        )
        assert isinstance(super_admin, SuperAdmin)

    try:
        create_super_admin_registration(
            db,
            full_name="Admin Six",
            email="admin6@example.test",
            password="Password123",
            photo_path=None,
        )
    except RegistrationError as exc:
        assert "maximum of 5" in str(exc)
    else:
        raise AssertionError("Expected the sixth Super Admin registration to fail.")


def test_fixture_creation_records_the_super_admin_who_set_it():
    db = make_session()
    category = seed_category(db)
    super_admin = create_super_admin_registration(
        db,
        full_name="Fixture Admin",
        email="fixture-admin@example.test",
        password="Password123",
        photo_path=None,
    )

    home_admin = create_team_admin_registration(
        db,
        full_name="Home Admin",
        team_name="Blue Eagles",
        email="home-admin@example.test",
        password="Password123",
        national_id="NID-HOME",
        phone="+26650000019",
        photo_path=None,
    )
    away_admin = create_team_admin_registration(
        db,
        full_name="Away Admin",
        team_name="Red Warriors",
        email="away-admin@example.test",
        password="Password123",
        national_id="NID-AWAY",
        phone="+26650000020",
        photo_path=None,
    )
    home_admin = approve_team_admin(db, home_admin.team_admin_id)
    away_admin = approve_team_admin(db, away_admin.team_admin_id)

    home_team = register_team(
        db,
        team_admin_id=home_admin.team_admin_id,
        team_name="Blue Eagles",
        category_id=category.category_id,
        contact_information="+26650000021",
        team_address="Blue Road",
        training_ground="Blue Training",
        home_ground="Blue Stadium",
        logo=None,
    )
    away_team = register_team(
        db,
        team_admin_id=away_admin.team_admin_id,
        team_name="Red Warriors",
        category_id=category.category_id,
        contact_information="+26650000022",
        team_address="Red Road",
        training_ground="Red Training",
        home_ground="Red Stadium",
        logo=None,
    )
    home_team = approve_team(db, home_team.team_id)
    away_team = approve_team(db, away_team.team_id)

    fixture = create_fixture(
        db,
        category_id=category.category_id,
        home_team_id=home_team.team_id,
        away_team_id=away_team.team_id,
        fixture_date=datetime.utcnow() + timedelta(days=10),
        venue="Youth Stadium",
        created_by_super_admin_id=super_admin.admin_id,
    )

    assert fixture.created_by_super_admin_id == super_admin.admin_id
    assert fixture.created_by_super_admin is not None
    assert fixture.created_by_super_admin.user.full_name == "Fixture Admin"
    assert fixture.match is not None


def test_fixture_creation_rejects_category_mismatches():
    db = make_session()
    category = seed_category(db)
    mismatch_category = Category(season_id=category.season_id, category_name="Female U13")
    db.add(mismatch_category)
    db.commit()

    home_admin = create_team_admin_registration(
        db,
        full_name="Mismatch Home Admin",
        team_name="Mismatch Home",
        email="mismatch-home@example.test",
        password="Password123",
        national_id="NID-MISMATCH-HOME",
        phone="+26650000023",
        photo_path=None,
    )
    away_admin = create_team_admin_registration(
        db,
        full_name="Mismatch Away Admin",
        team_name="Mismatch Away",
        email="mismatch-away@example.test",
        password="Password123",
        national_id="NID-MISMATCH-AWAY",
        phone="+26650000024",
        photo_path=None,
    )
    home_admin = approve_team_admin(db, home_admin.team_admin_id)
    away_admin = approve_team_admin(db, away_admin.team_admin_id)

    home_team = register_team(
        db,
        team_admin_id=home_admin.team_admin_id,
        team_name="Mismatch Home",
        category_id=category.category_id,
        contact_information="+26650000025",
        team_address="Home Road",
        training_ground="Home Training",
        home_ground="Home Ground",
        logo=None,
    )
    away_team = register_team(
        db,
        team_admin_id=away_admin.team_admin_id,
        team_name="Mismatch Away",
        category_id=category.category_id,
        contact_information="+26650000026",
        team_address="Away Road",
        training_ground="Away Training",
        home_ground="Away Ground",
        logo=None,
    )
    home_team = approve_team(db, home_team.team_id)
    away_team = approve_team(db, away_team.team_id)

    try:
        create_fixture(
            db,
            category_id=mismatch_category.category_id,
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id,
            fixture_date=datetime.utcnow() + timedelta(days=10),
            venue="Youth Stadium",
            created_by_super_admin_id=None,
        )
    except RegistrationError as exc:
        assert "Selected teams must belong to the chosen category." in str(exc)
    else:
        raise AssertionError("Expected the category mismatch to be rejected.")


def test_result_players_endpoint_returns_only_fixture_team_players_for_the_category():
    db = make_session()
    category = seed_category(db)

    home_admin = create_team_admin_registration(
        db,
        full_name="Home Admin",
        team_name="Blue Eagles",
        email="home-result@example.test",
        password="Password123",
        national_id="NID-HOME-RESULT",
        phone="+26650000030",
        photo_path="/uploads/admin-photos/home-result.png",
    )
    away_admin = create_team_admin_registration(
        db,
        full_name="Away Admin",
        team_name="Red Warriors",
        email="away-result@example.test",
        password="Password123",
        national_id="NID-AWAY-RESULT",
        phone="+26650000031",
        photo_path="/uploads/admin-photos/away-result.png",
    )
    home_admin = approve_team_admin(db, home_admin.team_admin_id)
    away_admin = approve_team_admin(db, away_admin.team_admin_id)

    home_team = register_team(
        db,
        team_admin_id=home_admin.team_admin_id,
        team_name="Blue Eagles",
        category_id=category.category_id,
        contact_information="+26650000032",
        team_address="Blue Road",
        training_ground="Blue Training",
        home_ground="Blue Stadium",
        logo="/uploads/team-logos/blue-eagles.png",
    )
    away_team = register_team(
        db,
        team_admin_id=away_admin.team_admin_id,
        team_name="Red Warriors",
        category_id=category.category_id,
        contact_information="+26650000033",
        team_address="Red Road",
        training_ground="Red Training",
        home_ground="Red Stadium",
        logo="/uploads/team-logos/red-warriors.png",
    )
    home_team = approve_team(db, home_team.team_id)
    away_team = approve_team(db, away_team.team_id)

    approve_player(
        db,
        register_player(
            db,
            team_id=home_team.team_id,
            full_name="Home Striker",
            gender="Male",
            dob=years_ago(17),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            parent_name="Parent Home",
            parent_contact="+26650000034",
            school_name=None,
            position="Forward",
            agreement_form_path="/uploads/player-agreements/home-striker.pdf",
            photo_path=None,
            documents=[],
            registration_period=1,
        ).player_id,
    )
    approve_player(
        db,
        register_player(
            db,
            team_id=home_team.team_id,
            full_name="Home Support",
            gender="Male",
            dob=years_ago(17),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            parent_name="Parent Home Support",
            parent_contact="+26650000035",
            school_name=None,
            position="Midfielder",
            agreement_form_path="/uploads/player-agreements/home-support.pdf",
            photo_path=None,
            documents=[],
            registration_period=1,
        ).player_id,
    )
    approve_player(
        db,
        register_player(
            db,
            team_id=home_team.team_id,
            full_name="Home Younger Player",
            gender="Male",
            dob=years_ago(17),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            parent_name="Parent Younger",
            parent_contact="+26650000038",
            school_name=None,
            position="Defender",
            agreement_form_path="/uploads/player-agreements/home-younger.pdf",
            photo_path=None,
            documents=[],
            registration_period=1,
        ).player_id,
    )
    db.add(
        Player(
            team_id=home_team.team_id,
            parent_id=None,
            full_name="Home U15 Outsider",
            gender="Male",
            dob=years_ago(15),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            school_name=None,
            position="Defender",
            photo_path=None,
            age_group="U15",
            registration_type="new",
            registration_period=1,
            agreement_form_path="/uploads/player-agreements/home-outsider.pdf",
            player_code="TEST-U15",
            rejection_reason=None,
            status=ApprovalStatus.APPROVED.value,
            approved_by_super_admin_id=None,
            approved_at=datetime.utcnow(),
            registration_reminder_sent_at=None,
            is_on_loan=False,
            original_team_id=None,
            loan_end_date=None,
        )
    )
    approve_player(
        db,
        register_player(
            db,
            team_id=away_team.team_id,
            full_name="Away Striker",
            gender="Male",
            dob=years_ago(17),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            parent_name="Parent Away",
            parent_contact="+26650000036",
            school_name=None,
            position="Forward",
            agreement_form_path="/uploads/player-agreements/away-striker.pdf",
            photo_path=None,
            documents=[],
            registration_period=1,
        ).player_id,
    )
    approve_player(
        db,
        register_player(
            db,
            team_id=away_team.team_id,
            full_name="Away Support",
            gender="Male",
            dob=years_ago(17),
            nationality="Mosotho",
            email=None,
            residential_address=None,
            parent_name="Parent Away Support",
            parent_contact="+26650000037",
            school_name=None,
            position="Midfielder",
            agreement_form_path="/uploads/player-agreements/away-support.pdf",
            photo_path=None,
            documents=[],
            registration_period=1,
        ).player_id,
    )

    fixture = Fixture(
        season_id=category.season_id,
        category_id=category.category_id,
        home_team_id=home_team.team_id,
        away_team_id=away_team.team_id,
        fixture_date=datetime.utcnow() - timedelta(days=1),
        venue="Test Ground",
        status="completed",
    )
    db.add(fixture)
    db.flush()
    db.add(
        Match(
            fixture_id=fixture.fixture_id,
            match_date=fixture.fixture_date,
            status="completed",
            home_score=1,
            away_score=1,
        )
    )
    db.commit()

    payload = _load_result_fixture_players(db, fixture.fixture_id)
    assert payload["category_name"] == "Male U17"
    assert [player["player_name"] for player in payload["home_players"]] == [
        "Home Striker",
        "Home Support",
        "Home Younger Player",
    ]
    assert [player["player_name"] for player in payload["away_players"]] == [
        "Away Striker",
        "Away Support",
    ]

    submission = submit_match_result(
        db,
        team_admin_id=home_admin.team_admin_id,
        fixture_id=fixture.fixture_id,
        home_score=1,
        away_score=1,
        scorer_names_text="Home Striker\nAway Striker",
        goal_types_text="penalty\nfreekick",
        assist_names_text="Home Support\nAway Support",
    )
    assert submission.status == ApprovalStatus.PENDING.value
    assert submission.scorer_names_text == "Home Striker\nAway Striker"
    assert submission.goal_types_text == "penalty\nfreekick"
    assert submission.assist_names_text == "Home Support\nAway Support"


def test_rejection_reasons_are_required_and_saved():
    db = make_session()
    category = seed_category(db)

    rejected_admin = create_team_admin_registration(
        db,
        full_name="Rejected Admin",
        team_name="Red Stars",
        email="rejected@example.test",
        password="Password123",
        national_id="NID-REJECTED",
        phone="+26651110000",
        photo_path=None,
    )

    try:
        reject_team_admin(db, rejected_admin.team_admin_id, "")
    except RegistrationError as exc:
        assert "reason is required" in str(exc)
    else:
        raise AssertionError("Expected blank Team Admin rejection reason to fail.")

    rejected_admin = reject_team_admin(
        db,
        rejected_admin.team_admin_id,
        "National ID photo is unclear.",
    )
    assert rejected_admin.status == ApprovalStatus.REJECTED.value
    assert rejected_admin.rejection_reason == "National ID photo is unclear."

    approved_admin = create_team_admin_registration(
        db,
        full_name="Approved Admin",
        team_name="Green City",
        email="approved@example.test",
        password="Password123",
        national_id="NID-APPROVED",
        phone="+26652220000",
        photo_path=None,
    )
    approved_admin = approve_team_admin(db, approved_admin.team_admin_id)

    female_category = Category(season_id=category.season_id, category_name="Female U15")
    db.add(female_category)
    db.commit()

    rejected_team = register_team(
        db,
        team_admin_id=approved_admin.team_admin_id,
        team_name="Green City",
        category_id=category.category_id,
        contact_information="+26652220001",
        team_address="Green City Road",
        training_ground="Green Training",
        home_ground="Green Ground",
        logo=None,
    )
    rejected_team = reject_team(
        db,
        rejected_team.team_id,
        "Home ground needs confirmation.",
    )
    assert rejected_team.status == ApprovalStatus.REJECTED.value
    assert rejected_team.rejection_reason == "Home ground needs confirmation."

    approved_team = register_team(
        db,
        team_admin_id=approved_admin.team_admin_id,
        team_name="Green City Juniors",
        category_id=female_category.category_id,
        contact_information="+26652220002",
        team_address="Green City Road",
        training_ground="Green Training",
        home_ground="Green Ground",
        logo=None,
    )
    approved_team = approve_team(db, approved_team.team_id)
    player = register_player(
        db,
        team_id=approved_team.team_id,
        full_name="Palesa Runner",
        gender="Female",
        dob=date(2011, 8, 2),
        nationality="Mosotho",
        email=None,
        residential_address=None,
        parent_name="Parent Two",
        parent_contact="+26652220003",
        school_name=None,
        position=None,
        agreement_form_path="/uploads/player-agreements/palesa.pdf",
        photo_path=None,
        documents=[],
    )
    player = reject_player(db, player.player_id, "Parent consent picture missing.")
    assert player.status == ApprovalStatus.REJECTED.value
    assert player.rejection_reason == "Parent consent picture missing."


def test_email_verification_and_login_codes_are_required_and_consumed():
    db = make_session()
    super_admin = create_super_admin_registration(
        db,
        full_name="Email Admin",
        email="email-admin@example.test",
        password="Password123",
        photo_path=None,
    )
    assert super_admin.user.email_verified is False

    verification_code = issue_email_verification_code(db, super_admin.user)
    verify_email_code(db, super_admin.user, verification_code)
    assert super_admin.user.email_verified is True
    assert super_admin.user.email_verification_code_hash is None

    login_code = issue_login_code(db, super_admin.user)
    verify_login_code(db, super_admin.user, login_code)
    assert super_admin.user.login_code_hash is None


def test_renewal_and_transfer_registration_flow_records_database_changes():
    db = make_session()
    category = seed_category(db)

    from_admin = create_team_admin_registration(
        db,
        full_name="From Admin",
        team_name="Blue Eagles",
        email="from@example.test",
        password="Password123",
        national_id="NID-FROM",
        phone="+26653330000",
        photo_path=None,
    )
    to_admin = create_team_admin_registration(
        db,
        full_name="To Admin",
        team_name="Red Stars",
        email="to@example.test",
        password="Password123",
        national_id="NID-TO",
        phone="+26654440000",
        photo_path=None,
    )
    from_admin = approve_team_admin(db, from_admin.team_admin_id)
    to_admin = approve_team_admin(db, to_admin.team_admin_id)

    from_team = register_team(
        db,
        team_admin_id=from_admin.team_admin_id,
        team_name="Blue Eagles",
        category_id=category.category_id,
        contact_information="+26653330001",
        team_address="Blue Road",
        training_ground="Blue Training",
        home_ground="Blue Ground",
        logo=None,
    )
    to_team = register_team(
        db,
        team_admin_id=to_admin.team_admin_id,
        team_name="Red Stars",
        category_id=category.category_id,
        contact_information="+26654440001",
        team_address="Red Road",
        training_ground="Red Training",
        home_ground="Red Ground",
        logo=None,
    )
    from_team = approve_team(db, from_team.team_id)
    to_team = approve_team(db, to_team.team_id)

    player = register_player(
        db,
        team_id=from_team.team_id,
        full_name="Transfer Player",
        gender="Male",
        dob=date(2010, 5, 1),
        nationality="Mosotho",
        email=None,
        residential_address=None,
        parent_name="Parent Three",
        parent_contact="+26653330002",
        school_name=None,
        position="Midfielder",
        agreement_form_path="/uploads/player-agreements/transfer-original.pdf",
        photo_path="/uploads/player-photos/player.jpg",
        documents=[("Birth Certificate", "/uploads/player-documents/birth.pdf")],
    )
    approve_player(db, player.player_id)
    player.approved_at = datetime.utcnow() - timedelta(days=400)
    db.commit()

    renewal = renew_player_registration(
        db,
        team_admin_id=from_admin.team_admin_id,
        player_id=player.player_id,
        agreement_form_path="/uploads/player-agreements/renewal.pdf",
    )
    assert renewal.registration_type == "renewal"
    assert renewal.status == ApprovalStatus.PENDING.value

    transfer = request_player_from_team(
        db,
        team_admin_id=to_admin.team_admin_id,
        player_id=player.player_id,
        from_team_id=from_team.team_id,
        to_team_id=to_team.team_id,
        request_type="Loan Request",
        request_details="Return after season",
        request_loan_period="1 year",
    )
    assert transfer.status == TransferStatus.PENDING_RESPONSE.value

    transfer = respond_to_transfer(
        db,
        team_admin_id=from_admin.team_admin_id,
        transfer_id=transfer.transfer_id,
        decision="agree",
        explanation="Terms accepted.",
    )
    assert transfer.status == TransferStatus.AGREED.value
    assert transfer.player.team_id == from_team.team_id
    assert transfer.player.is_on_loan is True

    transfer = complete_transfer_registration(
        db,
        team_admin_id=to_admin.team_admin_id,
        transfer_id=transfer.transfer_id,
        agreement_form_path="/uploads/player-agreements/transfer-new.pdf",
    )
    assert transfer.status == TransferStatus.REGISTERED.value
    assert transfer.player.team_id == from_team.team_id

    transfer_registration = db.scalar(
        select(PlayerRegistrationRequest)
        .where(PlayerRegistrationRequest.registration_type == "transfer")
        .order_by(PlayerRegistrationRequest.registration_id.desc())
    )
    assert transfer_registration is not None
    assert transfer_registration.status == ApprovalStatus.PENDING.value
    assert transfer_registration.team_id == to_team.team_id
    assert transfer_registration.agreement_form_path == "/uploads/player-agreements/transfer-new.pdf"

    new_player = transfer_registration.player
    assert new_player.team_id == to_team.team_id
    assert new_player.status == ApprovalStatus.PENDING.value
    assert new_player.photo_path == "/uploads/player-photos/player.jpg"
    assert any(doc.file_path == "/uploads/player-documents/birth.pdf" for doc in new_player.documents)
    assert any(doc.document_type == "Parent/Guardian Consent Form" for doc in new_player.documents)

    permanent_player = register_player(
        db,
        team_id=from_team.team_id,
        full_name="Permanent Player",
        gender="Male",
        dob=years_ago(16),
        nationality="Mosotho",
        email=None,
        residential_address=None,
        parent_name="Parent Four",
        parent_contact="+26653330004",
        school_name=None,
        position="Defender",
        agreement_form_path="/uploads/player-agreements/permanent-original.pdf",
        photo_path="/uploads/player-photos/permanent.jpg",
        documents=[("Medical Certificate", "/uploads/player-documents/medical.pdf")],
    )
    approve_player(db, permanent_player.player_id)

    permanent_transfer = request_player_from_team(
        db,
        team_admin_id=to_admin.team_admin_id,
        player_id=permanent_player.player_id,
        from_team_id=from_team.team_id,
        to_team_id=to_team.team_id,
        request_type="Permanent Request",
        request_details="Permanent move agreed.",
    )
    permanent_transfer = respond_to_transfer(
        db,
        team_admin_id=from_admin.team_admin_id,
        transfer_id=permanent_transfer.transfer_id,
        decision="approved",
    )
    assert permanent_transfer.player.status == "transferred"
    assert permanent_transfer.player.team_id == from_team.team_id

    complete_transfer_registration(
        db,
        team_admin_id=to_admin.team_admin_id,
        transfer_id=permanent_transfer.transfer_id,
        agreement_form_path="/uploads/player-agreements/permanent-new.pdf",
    )
    permanent_registration = db.scalar(
        select(PlayerRegistrationRequest)
        .where(
            PlayerRegistrationRequest.registration_type == "transfer",
            PlayerRegistrationRequest.agreement_form_path == "/uploads/player-agreements/permanent-new.pdf",
        )
    )
    assert permanent_registration is not None
    assert permanent_registration.player.team_id == to_team.team_id
    assert permanent_registration.player.status == ApprovalStatus.PENDING.value


def test_renewal_registration_rejects_players_whose_current_term_has_not_expired():
    db = make_session()
    category = seed_category(db)

    team_admin = create_team_admin_registration(
        db,
        full_name="Renewal Admin",
        team_name="Gold United",
        email="renewal-admin@example.test",
        password="Password123",
        national_id="NID-RENEWAL",
        phone="+26660000010",
        photo_path=None,
    )
    team_admin = approve_team_admin(db, team_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=team_admin.team_admin_id,
        team_name="Gold United",
        category_id=category.category_id,
        contact_information="+26660000011",
        team_address="Gold Road",
        training_ground="Gold Training",
        home_ground="Gold Ground",
        logo=None,
    )
    team = approve_team(db, team.team_id)

    player = register_player(
        db,
        team_id=team.team_id,
        full_name="Fresh Player",
        gender="Male",
        dob=years_ago(17),
        nationality="Mosotho",
        email=None,
        residential_address=None,
        parent_name="Parent Fresh",
        parent_contact="+26660000012",
        school_name=None,
        position="Defender",
        agreement_form_path="/uploads/player-agreements/fresh.pdf",
        photo_path=None,
        documents=[],
        registration_period=1,
    )
    approve_player(db, player.player_id)

    try:
        renew_player_registration(
            db,
            team_admin_id=team_admin.team_admin_id,
            player_id=player.player_id,
            agreement_form_path="/uploads/player-agreements/fresh-renewal.pdf",
            registration_period=1,
        )
    except RegistrationError as exc:
        assert "valid until" in str(exc)
    else:
        raise AssertionError("Expected renewal before expiry to be rejected.")


def test_renewal_registration_rejects_on_loan_players():
    db = make_session()
    category = seed_category(db)

    team_admin = create_team_admin_registration(
        db,
        full_name="Loan Admin",
        team_name="Crimson Town",
        email="loan-admin@example.test",
        password="Password123",
        national_id="NID-LOAN",
        phone="+26660000020",
        photo_path=None,
    )
    team_admin = approve_team_admin(db, team_admin.team_admin_id)
    team = register_team(
        db,
        team_admin_id=team_admin.team_admin_id,
        team_name="Crimson Town",
        category_id=category.category_id,
        contact_information="+26660000021",
        team_address="Crimson Road",
        training_ground="Crimson Training",
        home_ground="Crimson Ground",
        logo=None,
    )
    team = approve_team(db, team.team_id)

    player = register_player(
        db,
        team_id=team.team_id,
        full_name="Loan Player",
        gender="Male",
        dob=years_ago(16),
        nationality="Mosotho",
        email=None,
        residential_address=None,
        parent_name="Parent Loan",
        parent_contact="+26660000022",
        school_name=None,
        position="Midfielder",
        agreement_form_path="/uploads/player-agreements/loan.pdf",
        photo_path=None,
        documents=[],
        registration_period=1,
    )
    approve_player(db, player.player_id)
    player.approved_at = datetime.utcnow() - timedelta(days=400)
    player.is_on_loan = True
    db.commit()

    try:
        renew_player_registration(
            db,
            team_admin_id=team_admin.team_admin_id,
            player_id=player.player_id,
            agreement_form_path="/uploads/player-agreements/loan-renewal.pdf",
            registration_period=1,
        )
    except RegistrationError as exc:
        assert "on loan" in str(exc)
    else:
        raise AssertionError("Expected on-loan renewal to be rejected.")
