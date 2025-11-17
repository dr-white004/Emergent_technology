# Add these to app/schemas.py
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


# Wallet Schemas
class WalletBase(BaseModel):
    balance: Decimal = Field(..., decimal_places=2)

class WalletResponse(WalletBase):
    id: int
    user_id: int
    currency: str = "NGN"
    created_at: datetime
    
    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)

class FundWalletRequest(TransactionBase):
    amount: Decimal = Field(..., ge=100, le=500000, decimal_places=2)

class TransferRequest(TransactionBase):
    recipient_id: int
    amount: Decimal = Field(..., ge=50, le=100000, decimal_places=2)
    description: Optional[str] = Field(None, max_length=500)

class TransactionResponse(BaseModel):
    id: int
    reference: str
    transaction_type: str
    amount: Decimal
    sender_id: Optional[int]
    recipient_id: Optional[int]
    status: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TransactionDetailResponse(TransactionResponse):
    sender_username: Optional[str] = None
    recipient_username: Optional[str] = None

class TransactionHistoryResponse(BaseModel):
    transactions: List[TransactionDetailResponse]
    total: int
    limit: int
    offset: int


# Voucher Schemas
class CreateVoucherRequest(BaseModel):
    amount: Decimal = Field(..., ge=100, le=50000, decimal_places=2)
    expiry_days: int = Field(default=90, ge=1, le=365)

class RedeemVoucherRequest(BaseModel):
    code: str = Field(..., min_length=12, max_length=12)

class VoucherResponse(BaseModel):
    id: int
    code: str
    amount: Decimal
    is_redeemed: bool
    expiry_date: datetime
    created_at: datetime
    redeemed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Response Wrappers
class WalletBalanceResponse(BaseModel):
    balance: Decimal
    currency: str = "NGN"

class FundWalletResponse(BaseModel):
    message: str
    transaction: TransactionResponse
    new_balance: Decimal

class TransferResponse(BaseModel):
    message: str
    transaction: TransactionResponse
    new_balance: Decimal

class CreateVoucherResponse(BaseModel):
    message: str
    voucher: VoucherResponse
    new_balance: Decimal

class RedeemVoucherResponse(BaseModel):
    message: str
    amount: Decimal
    new_balance: Decimal
    redeemed_at: datetime