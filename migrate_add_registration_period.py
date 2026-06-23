"""Add registration_period field to PlayerRegistrationRequest table."""
from sqlalchemy import text, inspect
from app.db.session import SessionLocal
from app.models import PlayerRegistrationRequest


def run_migration():
    """Add registration_period field to PlayerRegistrationRequest table."""
    db = SessionLocal()
    try:
        inspector = inspect(db.connection())
        columns = [col["name"] for col in inspector.get_columns(PlayerRegistrationRequest.__tablename__)]

        if "registration_period" not in columns:
            db.execute(
                text(
                    "ALTER TABLE player_registration_requests ADD COLUMN registration_period INTEGER DEFAULT 1 NOT NULL"
                )
            )
            db.commit()
            print("✓ Added registration_period column to player_registration_requests table")

        print("✓ PlayerRegistrationRequest table migration completed successfully")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
