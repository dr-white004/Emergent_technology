"""
Script to create a superadmin user via command line.

Usage:
    python scripts/create_superadmin.py

This will prompt for email, password, and full name, then create a superadmin user.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.modules.user import crud
from app.modules.user.model import UserRole
from app.core.security import validate_password_strength, hash_password
from sqlalchemy.exc import IntegrityError
import getpass


def create_superadmin():
    """Create a superadmin user interactively."""
    print("=" * 50)
    print("CREATE SUPERADMIN USER")
    print("=" * 50)
    print()
    
    # Get user input
    email = input("Email address: ").strip()
    if not email:
        print("Error: Email is required")
        return
    
    password = getpass.getpass("Password: ")
    if not password:
        print("Error: Password is required")
        return
    
    # Validate password
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        print(f"Error: {error_message}")
        return
    
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Error: Passwords do not match")
        return
    
    full_name = input("Full name: ").strip()
    if not full_name:
        print("Error: Full name is required")
        return
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = crud.get_user_by_email(db, email)
        if existing_user:
            print(f"\nError: User with email '{email}' already exists")
            
            # Offer to upgrade existing user to superadmin
            upgrade = input("Do you want to upgrade this user to superadmin? (yes/no): ").strip().lower()
            if upgrade in ['yes', 'y']:
                existing_user.role = UserRole.SUPER_ADMIN
                db.commit()
                print(f"\n✓ User '{email}' has been upgraded to superadmin!")
            return
        
        # Create superadmin user
        password_hash = hash_password(password)
        from app.modules.user.model import User
        import uuid
        
        superadmin = User(
            id=uuid.uuid4(),
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
            role=UserRole.SUPER_ADMIN
        )
        
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)
        
        print("\n" + "=" * 50)
        print("✓ SUPERADMIN CREATED SUCCESSFULLY!")
        print("=" * 50)
        print(f"ID: {superadmin.id}")
        print(f"Email: {superadmin.email}")
        print(f"Name: {superadmin.full_name}")
        print(f"Role: {superadmin.role.value}")
        print(f"Created: {superadmin.created_at}")
        print("=" * 50)
        
    except IntegrityError as e:
        db.rollback()
        print(f"\nError: Email address already registered")
    except Exception as e:
        db.rollback()
        print(f"\nError creating superadmin: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    create_superadmin()