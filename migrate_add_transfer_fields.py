#!/usr/bin/env python3
"""
Database migration script to add transfer request tracking fields.
"""

from sqlalchemy import text, inspect
from app.db.session import SessionLocal, engine

def add_transfer_request_fields():
    """Add transfer request tracking fields to player_transfer_requests table."""
    
    # Check if columns already exist
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('player_transfer_requests')]
    
    with SessionLocal() as db:
        try:
            # Add rejection_reason column
            if 'rejection_reason' not in columns:
                print("Adding rejection_reason column...")
                db.execute(text("""
                    ALTER TABLE player_transfer_requests 
                    ADD COLUMN rejection_reason TEXT
                """))
                print("✓ rejection_reason column added")
            else:
                print("✓ rejection_reason column already exists")
            
            # Add consent_form_uploaded column
            if 'consent_form_uploaded' not in columns:
                print("Adding consent_form_uploaded column...")
                db.execute(text("""
                    ALTER TABLE player_transfer_requests 
                    ADD COLUMN consent_form_uploaded BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("✓ consent_form_uploaded column added")
            else:
                print("✓ consent_form_uploaded column already exists")
            
            # Add loan_end_date column
            if 'loan_end_date' not in columns:
                print("Adding loan_end_date column...")
                db.execute(text("""
                    ALTER TABLE player_transfer_requests 
                    ADD COLUMN loan_end_date DATE
                """))
                print("✓ loan_end_date column added")
            else:
                print("✓ loan_end_date column already exists")
            
            # Add approved_by_super_admin_at column
            if 'approved_by_super_admin_at' not in columns:
                print("Adding approved_by_super_admin_at column...")
                db.execute(text("""
                    ALTER TABLE player_transfer_requests 
                    ADD COLUMN approved_by_super_admin_at TIMESTAMP
                """))
                print("✓ approved_by_super_admin_at column added")
            else:
                print("✓ approved_by_super_admin_at column already exists")
            
            db.commit()
            print("\n✓ Transfer request migration completed successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"✗ Migration failed: {e}")
            raise

if __name__ == "__main__":
    print("Starting transfer request migration...")
    print("-" * 50)
    add_transfer_request_fields()
