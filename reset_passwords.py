#!/usr/bin/env python
"""Reset user passwords to known values for testing."""
import sys
sys.path.insert(0, '/'.join(__file__.split('\\')[:-1]))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import User
from app.core.security import hash_password

def reset_password(email: str, new_password: str):
    """Reset password for a user."""
    db = SessionLocal()
    
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user:
        print(f"❌ User {email} not found")
        return False
    
    # Hash the new password
    hashed = hash_password(new_password)
    user.password_hash = hashed
    
    db.commit()
    print(f"✅ Password reset for {email} to: {new_password}")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("PASSWORD RESET UTILITY")
    print("=" * 60)
    
    # Reset all users to your custom password
    default_password = "12qazzaq21"
    
    db = SessionLocal()
    users = db.scalars(select(User)).all()
    
    for user in users:
        hashed = hash_password(default_password)
        user.password_hash = hashed
        print(f"✅ Reset {user.email} to: {default_password}")
    
    db.commit()
    print("\n" + "=" * 60)
    print("All passwords have been reset!")
    print(f"Use password: {default_password}")
    print("=" * 60)
