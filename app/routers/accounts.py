from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate
from app.services import calculate_account_balance, get_account_or_404

router = APIRouter()


def _account_out(db: Session, account: Account) -> AccountOut:
    balance = calculate_account_balance(db, account)
    return AccountOut(
        id=account.id,
        user_id=account.user_id,
        name=account.name,
        initial_balance=account.initial_balance,
        balance=_money(balance),
        created_at=account.created_at.isoformat(),
    )


def _money(value) -> str:
    from decimal import ROUND_HALF_UP

    if value is None:
        return "0.00"
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    account_in: AccountCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = (
        db.query(Account)
        .filter(
            Account.user_id == current_user.id,
            func.lower(Account.name) == func.lower(account_in.name),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este nome",
        )
    account = Account(
        user_id=current_user.id,
        name=account_in.name,
        initial_balance=account_in.initial_balance,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _account_out(db, account)


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    accounts = (
        db.query(Account)
        .filter(Account.user_id == current_user.id)
        .order_by(Account.id.asc())
        .all()
    )
    return [_account_out(db, a) for a in accounts]


@router.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = get_account_or_404(db, account_id, current_user.id)
    return _account_out(db, account)


@router.patch("/accounts/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    account_in: AccountUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = get_account_or_404(db, account_id, current_user.id)
    if account_in.name is not None:
        if account_in.name != account.name:
            existing = (
                db.query(Account)
                .filter(
                    Account.user_id == current_user.id,
                    Account.id != account_id,
                    func.lower(Account.name) == func.lower(account_in.name),
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Já existe uma conta com este nome",
                )
        account.name = account_in.name
    if account_in.initial_balance is not None:
        account.initial_balance = account_in.initial_balance
    db.commit()
    db.refresh(account)
    return _account_out(db, account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    account = get_account_or_404(db, account_id, current_user.id)
    has_tx = db.query(Transaction.id).filter(Transaction.account_id == account_id).first()
    if has_tx:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir uma conta que possui transações",
        )
    db.delete(account)
    db.commit()
    return None
