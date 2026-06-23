#!/usr/bin/env python3
"""
Database migration script to add loan tracking fields to the players table.
Run this script to update your database schema.
"""

from sqlalchemy import text, inspect
from app.db.session import SessionLocal, engine

def add_loan_fields():
    """Add loan tracking fields to players table."""
    
    # Check if columns already exist
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('players')]
    
    with SessionLocal() as db:
        try:
            # Add is_on_loan column
            if 'is_on_loan' not in columns:
                print("Adding is_on_loan column...")
                db.execute(text("""
                    ALTER TABLE players 
                    ADD COLUMN is_on_loan BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("✓ is_on_loan column added")
            else:
                print("✓ is_on_loan column already exists")
            
            # Add original_team_id column
            if 'original_team_id' not in columns:
                print("Adding original_team_id column...")
                db.execute(text("""
                    ALTER TABLE players 
                    ADD COLUMN original_team_id INTEGER REFERENCES teams(team_id)
                """))
                print("✓ original_team_id column added")
            else:
                print("✓ original_team_id column already exists")
            
            # Add loan_end_date column
            if 'loan_end_date' not in columns:
                print("Adding loan_end_date column...")
                db.execute(text("""
                    ALTER TABLE players 
                    ADD COLUMN loan_end_date DATE
                """))
                print("✓ loan_end_date column added")
            else:
                print("✓ loan_end_date column already exists")
            
            db.commit()
            print("\n✓ Database migration completed successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"✗ Migration failed: {e}")
            raise

if __name__ == "__main__":
    print("Starting database migration...")
    print("-" * 50)
    add_loan_fields()
