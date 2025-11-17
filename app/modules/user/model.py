from sqlalchemy import Column, String, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.modules.wallet.model import Wallet



class UserRole(str, enum.Enum):
    """User role enumeration."""
    CUSTOMER = "customer"
    VENDOR = "vendor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class VendorStatus(str, enum.Enum):
    """Vendor application status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    """User model for authentication and user management."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole, name="user_role", create_type=True),default=UserRole.CUSTOMER,nullable=False,index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    vendor = relationship("Vendor", back_populates="user", uselist=False)
    wallet: Mapped[Optional["Wallet"]] = relationship("Wallet", back_populates="user", uselist=False)
    
    
    def __repr__(self):
        return f"<User {self.email}>"


class Vendor(Base):
    """Vendor model for vendor applications and management."""
    __tablename__ = "vendors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = Column(String, nullable=False)
    status = Column( Enum(VendorStatus, name="vendor_status", create_type=True),default=VendorStatus.PENDING,nullable=False,index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user = relationship("User", back_populates="vendor")
    
    def __repr__(self):
        return f"<Vendor {self.business_name} - {self.status}>"