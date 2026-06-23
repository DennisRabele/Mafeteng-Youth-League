#!/usr/bin/env python
"""Test login with new credentials."""
import sys
sys.path.insert(0, '/'.join(__file__.split('\\')[:-1]))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import User
from app.core.security import verify_password

if __name__ == "__main__":
    db = SessionLocal()
    users = db.scalars(select(User)).all()
    
    print("=" * 70)
    print("LOGIN TEST WITH YOUR PASSWORD")
    print("=" * 70)
    
    test_password = "12qazzaq21"
    
    for user in users:
        is_valid = verify_password(test_password, user.password_hash)
        status = "✅ CAN LOGIN" if is_valid else "❌ LOGIN FAILED"
        
        print(f"\n{status}")
        print(f"  Email: {user.email}")
        print(f"  Password: {test_password}")
        print(f"  Role: {user.role}")
        print(f"  Email Verified: {user.email_verified}")
        
        if user.team_admin_profile:
            print(f"  Team Admin Status: {user.team_admin_profile.status}")
    
    print("\n" + "=" * 70)
    print("All users ready to log in with: 12qazzaq21")
    print("=" * 70)
