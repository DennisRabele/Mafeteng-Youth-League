#!/usr/bin/env python
"""Debug script to simulate login attempts."""
import sys
sys.path.insert(0, '/'.join(__file__.split('\\')[:-1]))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import User
from app.core.security import verify_password

def check_login(email: str, password: str):
    db = SessionLocal()
    
    print(f"\nTesting login: {email} / {password}")
    print("-" * 60)
    
    # Simulate what the login route does
    search_email = email.strip().lower()
    print(f"Searching for email: {search_email}")
    
    user = db.scalar(select(User).where(User.email == search_email))
    
    if not user:
        print("❌ User not found in database")
        return False
    
    print(f"✅ User found: {user.email} (role: {user.role})")
    print(f"   Email verified: {user.email_verified}")
    print(f"   Password hash: {user.password_hash[:30]}...")
    
    # Try to verify password
    is_valid = verify_password(password, user.password_hash)
    print(f"   Password verification: {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    if not is_valid:
        print(f"   Expected hash format: pbkdf2_sha256$<salt>$<digest>")
        print(f"   Your hash starts with: {user.password_hash.split('$')[0]}")
    
    return is_valid

if __name__ == "__main__":
    print("=" * 60)
    print("LOGIN DEBUG - Testing all users in database")
    print("=" * 60)
    
    db = SessionLocal()
    users = db.scalars(select(User)).all()
    
    for user in users:
        print(f"\n📧 {user.email} (role: {user.role})")
        print(f"   Email verified: {user.email_verified}")
        if user.team_admin_profile:
            print(f"   Team Admin approved: {user.team_admin_profile.status}")
        print(f"   Hash: {user.password_hash[:40]}...")
        print(f"   NOTE: You must enter the ACTUAL password for this user.")
        print(f"   Try passwords like: 'password', 'test123', '123456'")
    
    print("\n" + "=" * 60)
