"""Add password recovery and account suspension fields to User table."""
from datetime import datetime
from sqlalchemy import text, inspect
from app.db.session import SessionLocal
from app.models import User


def run_migration():
    """Add password recovery and account suspension fields to User."""
    db = SessionLocal()
    try:
        inspector = inspect(db.connection())
        columns = [col["name"] for col in inspector.get_columns(User.__tablename__)]

        if "password_recovery_count" not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN password_recovery_count INTEGER DEFAULT 0 NOT NULL"))
            db.commit()
            print("✓ Added password_recovery_count column")

        if "account_suspended" not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN account_suspended BOOLEAN DEFAULT FALSE NOT NULL"))
            db.commit()
            print("✓ Added account_suspended column")

        if "account_suspension_expiry" not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN account_suspension_expiry TIMESTAMP"))
            db.commit()
            print("✓ Added account_suspension_expiry column")

        if "password_recovery_code_hash" not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN password_recovery_code_hash VARCHAR(255)"))
            db.commit()
            print("✓ Added password_recovery_code_hash column")

        if "password_recovery_expires_at" not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN password_recovery_expires_at TIMESTAMP"))
            db.commit()
            print("✓ Added password_recovery_expires_at column")

        print("✓ User table migration completed successfully")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
