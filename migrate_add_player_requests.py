"""
Migration script to add player_requests table for player request functionality.
"""

from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    """Run migration."""
    database_url = settings.database_url
    engine = create_engine(database_url)
    
    with engine.begin() as connection:
        # Create player_requests table
        print("Creating player_requests table...")
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS player_requests (
                request_id SERIAL PRIMARY KEY,
                player_id INTEGER NOT NULL REFERENCES players(player_id),
                from_team_id INTEGER NOT NULL REFERENCES teams(team_id),
                to_team_id INTEGER NOT NULL REFERENCES teams(team_id),
                requested_by_team_admin_id INTEGER NOT NULL REFERENCES team_admins(team_admin_id),
                request_type VARCHAR(40) NOT NULL,
                request_details TEXT NOT NULL,
                registration_period INTEGER NOT NULL DEFAULT 1,
                request_loan_period VARCHAR(40),
                status VARCHAR(40) NOT NULL DEFAULT 'pending',
                rejection_reason TEXT,
                response_explanation TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                responded_at TIMESTAMP,
                approved_by_super_admin_id INTEGER REFERENCES super_admins(admin_id),
                approved_by_super_admin_at TIMESTAMP
            )
        """))
        print("✓ player_requests table created successfully!")

if __name__ == "__main__":
    main()
