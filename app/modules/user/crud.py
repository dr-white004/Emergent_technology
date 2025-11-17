from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from uuid import UUID
from app.modules.user.model import User, Vendor, UserRole, VendorStatus
from app.core.security import hash_password, verify_password
from app.modules.wallet.crud import create_wallet_for_user



def create_user(db: Session, email: str, password: str, full_name: str) -> User:
    """
    Create a new user with hashed password.
    Raises IntegrityError if email already exists.
    """
    password_hash = hash_password(password)
    user = User(
        email=email.lower(),
        password_hash=password_hash,
        full_name=full_name,
        role=UserRole.CUSTOMER
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_wallet_for_user(db, user.id)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email address."""
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate user by email and password.
    Returns user if credentials are valid, None otherwise.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def update_user_role(db: Session, user_id: UUID, role: UserRole) -> Optional[User]:
    """Update user's role."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.role = role
    db.commit()
    db.refresh(user)
    return user


# ===== Vendor CRUD Operations =====

def create_vendor_application(db: Session, user_id: UUID, business_name: str) -> Vendor:
    """
    Create a new vendor application.
    Raises IntegrityError if user already has a vendor record.
    """
    vendor = Vendor(
        user_id=user_id,
        business_name=business_name,
        status=VendorStatus.PENDING
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def get_vendor_by_user_id(db: Session, user_id: UUID) -> Optional[Vendor]:
    """Get vendor by user ID."""
    return db.query(Vendor).filter(Vendor.user_id == user_id).first()


def get_vendor_by_id(db: Session, vendor_id: UUID) -> Optional[Vendor]:
    """Get vendor by vendor ID."""
    return db.query(Vendor).filter(Vendor.id == vendor_id).first()


def get_pending_vendors(db: Session) -> List[Vendor]:
    """Get all vendors with pending status."""
    return db.query(Vendor).filter(Vendor.status == VendorStatus.PENDING).all()


def update_vendor_status(db: Session, vendor_id: UUID, status: VendorStatus) -> Optional[Vendor]:
    """Update vendor's application status."""
    vendor = get_vendor_by_id(db, vendor_id)
    if not vendor:
        return None
    vendor.status = status
    db.commit()
    db.refresh(vendor)
    return vendor


def approve_vendor_application(db: Session, vendor_id: UUID) -> Optional[Vendor]:
    """
    Approve vendor application and update user role to vendor.
    Uses transaction to ensure both updates succeed or both fail.
    """
    vendor = get_vendor_by_id(db, vendor_id)
    if not vendor:
        return None
    
    try:
        # Update vendor status
        vendor.status = VendorStatus.APPROVED
        
        # Update user role
        user = vendor.user
        user.role = UserRole.VENDOR
        
        # Commit transaction
        db.commit()
        db.refresh(vendor)
        return vendor
    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise e