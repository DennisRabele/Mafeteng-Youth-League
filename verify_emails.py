#!/usr/bin/env python
"""Mark all emails as verified."""
import sys
sys.path.insert(0, '/'.join(__file__.split('\\')[:-1]))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import User

if __name__ == "__main__":
    db = SessionLocal()
    users = db.scalars(select(User)).all()
    
    print("Marking all emails as verified...")
    for user in users:
        if not user.email_verified:
            print(f"  ✅ Verified: {user.email}")
            user.email_verified = True
    
    db.commit()
    print("\n✅ All emails are now verified!")
