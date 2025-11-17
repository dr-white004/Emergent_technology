from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status
import string
import secrets

from app.modules.user.model import User 
from app.modules.wallet.model import Wallet, Transaction, Voucher, TransactionType, TransactionStatus


def generate_transaction_reference() -> str:
    """Generate unique transaction reference: TXN-YYYYMMDD-XXXXX"""
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(secrets.choice(string.digits) for _ in range(6))
    return f"TXN-{date_str}-{random_str}"


def generate_voucher_code() -> str:
    """Generate unique 12-character voucher code: VCH-XXXXXXXX"""
    chars = string.ascii_uppercase + string.digits
    # Remove ambiguous characters: 0, O, 1, I
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    random_str = ''.join(secrets.choice(chars) for _ in range(8))
    return f"VCH-{random_str}"


def create_wallet_for_user(db: Session, user_id: UUID) -> Wallet:
    """Create a wallet for a new user with initial balance of 0.00"""
    wallet = Wallet(
        user_id=user_id,
        balance=Decimal("0.00")
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def get_user_wallet(db: Session, user_id: UUID) -> Wallet:
    """Get user's wallet or raise 404"""
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    return wallet


def get_wallet_by_id(db: Session, wallet_id: UUID) -> Wallet:
    """Get wallet by ID or raise 404"""
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    return wallet


def create_transaction_record(
    db: Session,
    transaction_type: TransactionType,
    amount: Decimal,
    sender_id: Optional[UUID] = None,
    recipient_id: Optional[UUID] = None,
    description: Optional[str] = None,
    status: TransactionStatus = TransactionStatus.COMPLETED
) -> Transaction:
    """Create a transaction record with unique reference"""
    reference = generate_transaction_reference()
    
    # CRITICAL: Ensure reference is unique
    while db.query(Transaction).filter(Transaction.reference == reference).first():
        reference = generate_transaction_reference()
    
    transaction = Transaction(
        reference=reference,
        transaction_type=transaction_type,
        amount=amount,
        sender_id=sender_id,
        recipient_id=recipient_id,
        description=description,
        status=status
    )
    db.add(transaction)
    return transaction


def fund_wallet(db: Session, user_id: UUID, amount: Decimal) -> Tuple[Transaction, Decimal]:
    """
    Fund user wallet (simulated deposit)
    Returns: (transaction, new_balance)
    """
    # CRITICAL: Validation as per requirements
    if amount < Decimal("100"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum funding amount is ₦100"
        )
    if amount > Decimal("500000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum funding amount is ₦500,000"
        )
    
    try:
        wallet = get_user_wallet(db, user_id)
        
        # Update balance
        wallet.balance += amount
        
        transaction = create_transaction_record(
            db=db,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            recipient_id=wallet.id,
            description="Wallet funding (simulated)"
        )
        
        db.commit()
        db.refresh(wallet)
        db.refresh(transaction)
        
        return transaction, wallet.balance
    
    except Exception as e:
        db.rollback()
        failed_txn = create_transaction_record(
            db=db,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            recipient_id=None,  
            description="Wallet funding failed",
            status=TransactionStatus.FAILED
        )
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Funding failed: {str(e)}"
        )


def transfer_funds(
    db: Session, 
    sender_user_id: UUID, 
    recipient_email: str, 
    amount: Decimal,
    description: Optional[str] = None
) -> Tuple[Transaction, Decimal]:
    """
    CRITICAL: Transfer funds with proper locking and atomic operations
    Returns: (transaction, new_sender_balance)
    """
   
    if amount < Decimal("50"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum transfer amount is ₦50"
        )
    if amount > Decimal("100000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum transfer amount is ₦100,000"
        )
    
    try:
        
        sender_wallet = db.query(Wallet).filter(
            Wallet.user_id == sender_user_id
        ).with_for_update().first()
        
        if not sender_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sender wallet not found"
            )
        
        recipient_user = db.query(User).filter(
            User.email == recipient_email.lower()
        ).first()
        
        if not recipient_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient not found"
            )
        
        if sender_user_id == recipient_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transfer to yourself"
            )
        
        recipient_wallet = db.query(Wallet).filter(
            Wallet.user_id == recipient_user.id
        ).with_for_update().first()
        
        if not recipient_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient wallet not found"
            )
        
        if sender_wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance"
            )
        
        sender_wallet.balance -= amount
        recipient_wallet.balance += amount
        
        transaction = create_transaction_record(
            db=db,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            sender_id=sender_wallet.id,
            recipient_id=recipient_wallet.id,
            description=description or f"Transfer to {recipient_email}"
        )
        
        db.commit()
        db.refresh(sender_wallet)
        db.refresh(transaction)
        
        return transaction, sender_wallet.balance
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        failed_txn = create_transaction_record(
            db=db,
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            description="Transfer failed",
            status=TransactionStatus.FAILED
        )
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer failed: {str(e)}"
        )


def get_transaction_history(
    db: Session, 
    user_id: UUID, 
    limit: int = 20, 
    offset: int = 0
) -> Tuple[List[dict], int]:
    """
    Get user's transaction history (sent or received)
    Returns: (transactions_with_details, total_count)
    """
    wallet = get_user_wallet(db, user_id)
    
    query = db.query(Transaction).filter(
        or_(
            Transaction.sender_id == wallet.id,
            Transaction.recipient_id == wallet.id
        )
    ).order_by(Transaction.created_at.desc())
    
    total = query.count()
    transactions = query.offset(offset).limit(limit).all()
    
    result = []
    for txn in transactions:
        # Determine transaction direction and safely handle counterparty info
        if txn.sender_id == wallet.id:
            direction = "sent"
            # For sent transactions, show recipient info if available
            counterparty_info = "Another user"
            if txn.recipient and txn.recipient.user:
                counterparty_info = txn.recipient.user.email
        else:
            direction = "received"
            # For received transactions, show sender info if available
            counterparty_info = "Another user"
            if txn.sender and txn.sender.user:
                counterparty_info = txn.sender.user.email
        
        txn_dict = {
            "id": txn.id,
            "reference": txn.reference,
            "transaction_type": txn.transaction_type.value,
            "amount": txn.amount,
            "direction": direction,
            "counterparty": counterparty_info,
            "status": txn.status.value,
            "description": txn.description,
            "created_at": txn.created_at,
        }
        result.append(txn_dict)
    
    return result, total


def create_voucher(
    db: Session, 
    user_id: UUID, 
    amount: Decimal, 
    expiry_days: int = 90
) -> Tuple[Voucher, Decimal]:
    """
    Create a voucher by debiting user's wallet
    Returns: (voucher, new_balance)
    """
    # CRITICAL: Validation as per requirements
    if amount < Decimal("100"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum voucher amount is ₦100"
        )
    if amount > Decimal("50000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum voucher amount is ₦50,000"
        )
    
    try:
        wallet = get_user_wallet(db, user_id)
        
        # CRITICAL: Check sufficient balance
        if wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance"
            )
        
        # CRITICAL: Generate unique voucher code
        code = generate_voucher_code()
        while db.query(Voucher).filter(Voucher.code == code).first():
            code = generate_voucher_code()
        
        # Debit wallet
        wallet.balance -= amount
        
        # Create voucher
        voucher = Voucher(
            code=code,
            creator_id=wallet.id,
            amount=amount,
            expiry_date=datetime.now() + timedelta(days=expiry_days)
        )
        db.add(voucher)
        
        # CRITICAL: Create transaction record
        create_transaction_record(
            db=db,
            transaction_type=TransactionType.VOUCHER_CREATE,
            amount=amount,
            sender_id=wallet.id,
            description=f"Voucher created: {code}"
        )
        
        db.commit()
        db.refresh(wallet)
        db.refresh(voucher)
        
        return voucher, wallet.balance
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voucher creation failed: {str(e)}"
        )


def redeem_voucher(db: Session, user_id: UUID, code: str) -> Tuple[Decimal, Decimal]:
    """
    Redeem a voucher and credit user's wallet
    Returns: (voucher_amount, new_balance)
    """
    try:
        wallet = get_user_wallet(db, user_id)
        
        # CRITICAL: Get voucher with lock to prevent double redemption
        voucher = db.query(Voucher).filter(
            Voucher.code == code
        ).with_for_update().first()
        
        if not voucher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voucher not found"
            )
        
        # CRITICAL: Validations as per requirements
        if voucher.is_redeemed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Voucher already redeemed"
            )
        
        if datetime.now() > voucher.expiry_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Voucher has expired"
            )
        
        if voucher.creator_id == wallet.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot redeem your own voucher"
            )
        
        wallet.balance += voucher.amount
        
        # Mark voucher as redeemed
        voucher.is_redeemed = True
        voucher.redeemer_id = wallet.id
        voucher.redeemed_at = datetime.now()
        
        # CRITICAL: Create transaction record
        create_transaction_record(
            db=db,
            transaction_type=TransactionType.VOUCHER_REDEEM,
            amount=voucher.amount,
            recipient_id=wallet.id,
            description=f"Voucher redeemed: {code}"
        )
        
        db.commit()
        db.refresh(wallet)
        
        return voucher.amount, wallet.balance
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voucher redemption failed: {str(e)}"
        )