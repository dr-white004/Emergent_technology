from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.modules.user.model import UserRole, VendorStatus



class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe"
            }
        }


class UserLoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123!"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response (without sensitive data)."""
    id: UUID
    email: str
    full_name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "role": "customer",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class LoginResponse(BaseModel):
    """Schema for login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "john.doe@example.com",
                    "full_name": "John Doe",
                    "role": "customer",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00"
                }
            }
        }


# ===== Vendor Schemas =====

class VendorApplicationRequest(BaseModel):
    """Schema for vendor application request."""
    business_name: str = Field(..., min_length=2, max_length=200)
    
    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Acme Events Ltd"
            }
        }


class VendorResponse(BaseModel):
    """Schema for vendor response."""
    id: UUID
    user_id: UUID
    business_name: str
    status: VendorStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "business_name": "Acme Events Ltd",
                "status": "pending",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class VendorWithUserResponse(BaseModel):
    """Schema for vendor with user information."""
    id: UUID
    user_id: UUID
    business_name: str
    status: VendorStatus
    created_at: datetime
    updated_at: datetime
    user: UserResponse
    
    class Config:
        from_attributes = True


# ===== Generic Response Schemas =====

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response."""
    detail: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "An error occurred"
            }
        }