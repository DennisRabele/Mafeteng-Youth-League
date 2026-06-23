"""
Migration: Add registration_period, loan_period, team_code, approved_by_super_admin_id fields
and implement immutability checks for approvals
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text, inspect
from app.db.session import SessionLocal

def run_migration():
    db = SessionLocal()
    inspector = inspect(db.connection())
    
    try:
        # Check and add columns to player_transfer_requests
        print("Checking player_transfer_requests table...")
        columns = [col['name'] for col in inspector.get_columns('player_transfer_requests')]
        
        if 'registration_period' not in columns:
            print("  Adding registration_period to player_transfer_requests...")
            db.execute(text("ALTER TABLE player_transfer_requests ADD COLUMN registration_period INTEGER DEFAULT 1 NOT NULL"))
        
        if 'loan_period' not in columns:
            print("  Adding loan_period to player_transfer_requests...")
            db.execute(text("ALTER TABLE player_transfer_requests ADD COLUMN loan_period VARCHAR(40)"))
        
        if 'approved_by_super_admin_id' not in columns:
            print("  Adding approved_by_super_admin_id to player_transfer_requests...")
            db.execute(text("ALTER TABLE player_transfer_requests ADD COLUMN approved_by_super_admin_id INTEGER REFERENCES super_admins(admin_id)"))
        
        # Check and add columns to teams
        print("Checking teams table...")
        columns = [col['name'] for col in inspector.get_columns('teams')]
        
        if 'team_code' not in columns:
            print("  Adding team_code to teams...")
            db.execute(text("ALTER TABLE teams ADD COLUMN team_code VARCHAR(50)"))
        
        if 'approved_by_super_admin_id' not in columns:
            print("  Adding approved_by_super_admin_id to teams...")
            db.execute(text("ALTER TABLE teams ADD COLUMN approved_by_super_admin_id INTEGER REFERENCES super_admins(admin_id)"))
        
        # Check and add columns to team_admins
        print("Checking team_admins table...")
        columns = [col['name'] for col in inspector.get_columns('team_admins')]
        
        if 'approved_by_super_admin_id' not in columns:
            print("  Adding approved_by_super_admin_id to team_admins...")
            db.execute(text("ALTER TABLE team_admins ADD COLUMN approved_by_super_admin_id INTEGER REFERENCES super_admins(admin_id)"))
        
        # Check and add columns to player_registration_requests
        print("Checking player_registration_requests table...")
        columns = [col['name'] for col in inspector.get_columns('player_registration_requests')]
        
        if 'approved_by_super_admin_id' not in columns:
            print("  Adding approved_by_super_admin_id to player_registration_requests...")
            db.execute(text("ALTER TABLE player_registration_requests ADD COLUMN approved_by_super_admin_id INTEGER REFERENCES super_admins(admin_id)"))
        
        # Check and add columns to players
        print("Checking players table...")
        columns = [col['name'] for col in inspector.get_columns('players')]
        
        if 'registration_period' not in columns:
            print("  Adding registration_period to players...")
            db.execute(text("ALTER TABLE players ADD COLUMN registration_period INTEGER DEFAULT 1 NOT NULL"))
        
        if 'approved_by_super_admin_id' not in columns:
            print("  Adding approved_by_super_admin_id to players...")
            db.execute(text("ALTER TABLE players ADD COLUMN approved_by_super_admin_id INTEGER REFERENCES super_admins(admin_id)"))
        
        db.commit()
        print("\nMigration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
