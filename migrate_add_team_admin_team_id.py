"""Add team_id field to TeamAdmin table for multiple team admin support."""
from sqlalchemy import text, inspect
from app.db.session import SessionLocal
from app.models import TeamAdmin


def run_migration():
    """Add team_id field to TeamAdmin table."""
    db = SessionLocal()
    try:
        inspector = inspect(db.connection())
        columns = [col["name"] for col in inspector.get_columns(TeamAdmin.__tablename__)]

        if "team_id" not in columns:
            db.execute(
                text(
                    "ALTER TABLE team_admins ADD COLUMN team_id INTEGER REFERENCES teams(team_id)"
                )
            )
            db.commit()
            print("✓ Added team_id column to team_admins table")

        print("✓ TeamAdmin table migration completed successfully")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
