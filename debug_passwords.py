#!/usr/bin/env python
"""Debug script to check password hashes in database."""
import sys
sys.path.insert(0, '/'.join(__file__.split('\\')[:-1]))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import User
from app.core.security import verify_password, hash_password

def main():
    db = SessionLocal()
    
    print("=" * 80)
    print("PASSWORD HASH DEBUG")
    print("=" * 80)
    
    users = db.scalars(select(User)).all()
    
    if not users:
        print("❌ No users found in database")
        return
    
    for user in users:
        print(f"\nUser: {user.email}")
        print(f"Role: {user.role}")
        print(f"Email Verified: {user.email_verified}")
        print(f"Password Hash (first 50 chars): {user.password_hash[:50]}...")
        print(f"Hash Format: {user.password_hash.split('$')[0] if '$' in user.password_hash else 'PLAINTEXT OR UNKNOWN'}")
        
        # Try to verify with a test password
        test_password = "test123"
        result = verify_password(test_password, user.password_hash)
        print(f"Verify test with 'test123': {result}")
    
    print("\n" + "=" * 80)
    print("TO FIX: You need to hash the existing passwords in the database.")
    print("Run: python fix_password_hashes.py")
    print("=" * 80)

if __name__ == "__main__":
    main()
