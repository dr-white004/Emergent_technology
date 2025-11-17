from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.modules.user.model import User
from app.core.permissions import IsAuthenticated
from app.modules.wallet import schema
from app.modules.wallet import crud
import datetime

router = APIRouter(prefix="/api", tags=["Wallet"])


@router.get("/wallet/balance", response_model=schema.WalletBalanceResponse)
def get_wallet_balance(
    current_user: User = Depends(IsAuthenticated),
    db: Session = Depends(get_db)
):
    """
    Get current user's wallet balance
    """
    wallet = crud.get_user_wallet(db, current_user.id)
    
    return {
        "balance": wallet.balance,
        "currency": "NGN"
    }


@router.post("/wallet/fund", response_model=schema.FundWalletResponse)
def fund_wallet(
    request: schema.FundWalletRequest,
    current_user: User = Depends(IsAuthenticated),
    db: Session = Depends(get_db)
):
    """
    Fund wallet (simulated deposit)
    """
    transaction, new_balance = crud.fund_wallet(
        db=db,
        user_id=current_user.id,
        amount=request.amount
    )
    
    return {
        "message": "Wallet funded successfully",
        "transaction": transaction,
        "new_balance": new_balance
    }


@router.post("/wallet/transfer", response_model=schema.TransferResponse)
def transfer_funds(
    request: schema.TransferRequest,
    current_user: User = Depends(IsAuthenticated),
    db: Session = Depends(get_db)
):
    """
    Transfer funds to another user (P2P)
    """
    transaction, new_balance = crud.transfer_funds(
        db=db,
        sender_user_id=current_user.id,
        recipient_user_id=request.recipient_id,
        amount=request.amount,
        description=request.description
    )
    
    return {
        "message": "Transfer successful",
        "transaction": transaction,
        "new_balance": new_balance
    }


@router.get("/wallet/transactions", response_model=schema.TransactionHistoryResponse)
def get_transaction_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(IsAuthenticated),
    db: Session = Depends(get_db)
):
    """
    Get transaction history for current user
    """
    transactions, total = crud.get_transaction_history(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    return {
        "transactions": transactions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/vouchers/create", response_model=schema.CreateVoucherResponse, status_code=status.HTTP_201_CREATED)
def create_voucher(
    request: schema.CreateVoucherRequest,
    current_user: User = Depends(IsAuthenticated),
    db: Session = Depends(get_db)
):
    """
    Create a voucher by debiting wallet
    """
    voucher, new_balance = crud.create_voucher(
        db=db,
        user_id=current_user.id,
        amount=request.amount,
        expiry_days=request.expiry_days
    )
    
    return {
        "message": "Voucher created successfully",
        "voucher": voucher,
        "new_balance": new_balance
    }


@router.post("/vouchers/redeem", response_model=schema.RedeemVoucherResponse)
def redeem_voucher(
    request: schema.RedeemVoucherRequest,
    current_user: User = Depends(IsAuthenticated),
    db: Session = Depends(get_db)
):
    """
    Redeem a voucher to credit wallet
    """
    amount, new_balance = crud.redeem_voucher(
        db=db,
        user_id=current_user.id,
        code=request.code
    )
    
    return {
        "message": "Voucher redeemed successfully",
        "amount": amount,
        "new_balance": new_balance,
        "redeemed_at": datetime.now()
    }