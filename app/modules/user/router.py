from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.permissions import IsAuthenticated, IsAdmin
from app.core.security import (
    validate_password_strength,
    create_access_token,
    create_refresh_token
)
from app.modules.user import crud
from app.modules.user.model import User, VendorStatus
from app.modules.user.schema import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    LoginResponse,
    VendorApplicationRequest,
    VendorResponse,
    VendorWithUserResponse
)

router = APIRouter()


# ===== Authentication Endpoints =====

@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password"
)
def register_user(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    - **email**: Must be unique and valid
    - **password**: Must meet security requirements (8+ chars, uppercase, number, special char)
    - **full_name**: User's full name
    
    Returns the created user (without password).
    """
    # Validate password strength
    is_valid, error_message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Check if user already exists
    existing_user = crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )
    
    # Create user
    try:
        user = crud.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and receive access and refresh tokens"
)
def login_user(
    credentials: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns access token (15 min), refresh token (30 days), and user info.
    """
    # Authenticate user
    user = crud.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens
    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user
    )


# ===== User Profile Endpoints =====

@router.get(
    "/user/profile",
    response_model=UserResponse,
    summary="Get user profile",
    description="Retrieve the authenticated user's profile information"
)
def get_user_profile(
    current_user: User = Depends(IsAuthenticated)
):
    """
    Get current user's profile.
    
    Requires valid authentication token.
    Returns user information without sensitive data.
    """
    return current_user


# ===== Vendor Endpoints =====

@router.post(
    "/vendor/apply",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to become a vendor",
    description="Submit a vendor application"
)
def apply_as_vendor(
    application: VendorApplicationRequest,
    current_user: User = Depends(IsAuthenticated),
    db: Session = Depends(get_db)
):
    """
    Submit vendor application.
    
    - **business_name**: Name of the business
    
    User must be authenticated and cannot already be a vendor.
    """
    # Check if user is already a vendor
    if current_user.role == "vendor":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a vendor"
        )
    
    # Check if user has existing vendor application
    existing_vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if existing_vendor:
        if existing_vendor.status == VendorStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pending vendor application"
            )
        elif existing_vendor.status == VendorStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your vendor application has already been approved"
            )
    
    # Create vendor application
    try:
        vendor = crud.create_vendor_application(
            db=db,
            user_id=current_user.id,
            business_name=application.business_name
        )
        return vendor
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a vendor application"
        )


# ===== Admin Endpoints =====

@router.get(
    "/admin/vendors/pending",
    response_model=List[VendorWithUserResponse],
    summary="List pending vendor applications",
    description="Get all vendor applications awaiting approval (Admin only)"
)
def list_pending_vendors(
    current_user: User = Depends(IsAdmin),
    db: Session = Depends(get_db)
):
    """
    List all pending vendor applications.
    
    Requires admin or super_admin role.
    Returns vendors with status 'pending' and their user information.
    """
    vendors = crud.get_pending_vendors(db)
    return vendors


@router.post(
    "/admin/vendors/{vendor_id}/approve",
    response_model=VendorResponse,
    summary="Approve vendor application",
    description="Approve a vendor application and grant vendor role (Admin only)"
)
def approve_vendor(
    vendor_id: UUID,
    current_user: User = Depends(IsAdmin),
    db: Session = Depends(get_db)
):
    """
    Approve a vendor application.
    
    - **vendor_id**: ID of the vendor application to approve
    
    Requires admin or super_admin role.
    Updates vendor status to 'approved' and changes user role to 'vendor'.
    Both updates are atomic (transaction).
    """
    # Get vendor
    vendor = crud.get_vendor_by_id(db, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor application not found"
        )
    
    # Check if already approved
    if vendor.status == VendorStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor application has already been approved"
        )
    
    # Approve vendor (atomic transaction)
    try:
        vendor = crud.approve_vendor_application(db, vendor_id)
        return vendor
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve vendor application"
        )