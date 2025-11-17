from decimal import Decimal
from sqlalchemy import CheckConstraint, Index, ForeignKey, func, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base
from datetime import datetime
from typing import Optional, List
import enum
from app.modules.user.model import User

class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    WITHDRAWAL = "withdrawal"
    VOUCHER_CREATE = "voucher_create"
    VOUCHER_REDEEM = "voucher_redeem"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Wallet(Base):
    __tablename__ = "wallets"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),  # Increased precision for larger amounts
        default=Decimal("0.00"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallet")
    sent_transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", 
        foreign_keys="Transaction.sender_id",
        back_populates="sender"
    )
    received_transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.recipient_id",
        back_populates="recipient"
    )
    created_vouchers: Mapped[List["Voucher"]] = relationship(
        "Voucher",
        foreign_keys="Voucher.creator_id",
        back_populates="creator"
    )
    redeemed_vouchers: Mapped[List["Voucher"]] = relationship(
        "Voucher",
        foreign_keys="Voucher.redeemer_id",
        back_populates="redeemer"
    )
    
    # CRITICAL: Database-level constraint to prevent negative balance
    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_balance_non_negative'),
        Index('idx_wallet_user', 'user_id'),
    )


class Transaction(Base):
    __tablename__ = "transactions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    reference: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=2), nullable=False)
    sender_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    recipient_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(default=TransactionStatus.COMPLETED, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True, nullable=False)
    
    # Relationships
    sender: Mapped[Optional["Wallet"]] = relationship(
        "Wallet",
        foreign_keys=[sender_id],
        back_populates="sent_transactions"
    )
    recipient: Mapped[Optional["Wallet"]] = relationship(
        "Wallet",
        foreign_keys=[recipient_id],
        back_populates="received_transactions"
    )
    
    # CRITICAL: Indexes for optimal query performance
    __table_args__ = (
        Index('idx_transaction_sender_created', 'sender_id', 'created_at'),
        Index('idx_transaction_recipient_created', 'recipient_id', 'created_at'),
        Index('idx_transaction_type_status', 'transaction_type', 'status'),
        Index('idx_transaction_reference', 'reference'),
        Index('idx_transaction_created_at', 'created_at'),
    )


class Voucher(Base):
    __tablename__ = "vouchers"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    creator_id: Mapped[UUID] = mapped_column(ForeignKey("wallets.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=2), nullable=False)
    is_redeemed: Mapped[bool] = mapped_column(default=False, nullable=False)
    redeemer_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    expiry_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    redeemed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    creator: Mapped["Wallet"] = relationship(
        "Wallet",
        foreign_keys=[creator_id],
        back_populates="created_vouchers"
    )
    redeemer: Mapped[Optional["Wallet"]] = relationship(
        "Wallet",
        foreign_keys=[redeemer_id],
        back_populates="redeemed_vouchers"
    )
    
    # CRITICAL: Indexes for voucher operations
    __table_args__ = (
        Index('idx_voucher_code_redeemed', 'code', 'is_redeemed'),
        Index('idx_voucher_creator_expiry', 'creator_id', 'expiry_date'),
        Index('idx_voucher_expiry', 'expiry_date'),
        CheckConstraint('amount > 0', name='check_voucher_amount_positive'),
    )