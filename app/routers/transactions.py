from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionsPage,
    TransactionUpdate,
)

router = APIRouter()


def _parse_date(value: str) -> date:
    from datetime import datetime

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Data inválida. Use o formato AAAA-MM-DD.",
        ) from None


def _transaction_out(tx: Transaction) -> TransactionOut:
    return TransactionOut(
        id=tx.id,
        user_id=tx.user_id,
        account_id=tx.account_id,
        category_id=tx.category_id,
        type=tx.type,
        amount=str(tx.amount),
        date=tx.date.isoformat(),
        description=tx.description,
        created_at=tx.created_at.isoformat(),
        updated_at=tx.updated_at.isoformat(),
    )


def _get_owned_or_404(db: Session, model, obj_id: int, user_id: int, name: str):
    obj = db.query(model).filter(model.id == obj_id, model.user_id == user_id).first()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{name} não encontrado",
        )
    return obj


@router.post(
    "/transactions",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    tx_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _get_owned_or_404(db, Account, tx_in.account_id, current_user.id, "Conta")
    category = _get_owned_or_404(db, Category, tx_in.category_id, current_user.id, "Categoria")
    if category.type != tx_in.type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O tipo da transação deve ser igual ao tipo da categoria",
        )
    tx = Transaction(
        user_id=current_user.id,
        account_id=tx_in.account_id,
        category_id=tx_in.category_id,
        type=tx_in.type,
        amount=tx_in.amount,
        date=_parse_date(tx_in.date),
        description=tx_in.description,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return _transaction_out(tx)


@router.get("/transactions", response_model=TransactionsPage)
def list_transactions(
    account_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    min_amount: str | None = Query(default=None),
    max_amount: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if type:
        query = query.filter(Transaction.type == type)
    if date_from:
        query = query.filter(Transaction.date >= _parse_date(date_from))
    if date_to:
        query = query.filter(Transaction.date <= _parse_date(date_to))
    if min_amount is not None:
        from decimal import Decimal

        query = query.filter(Transaction.amount >= Decimal(min_amount))
    if max_amount is not None:
        from decimal import Decimal

        query = query.filter(Transaction.amount <= Decimal(max_amount))
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))

    total = query.count()
    items = (
        query.order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return TransactionsPage(
        items=[_transaction_out(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/transactions/{tx_id}", response_model=TransactionOut)
def get_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tx = _get_owned_or_404(db, Transaction, tx_id, current_user.id, "Transação")
    return _transaction_out(tx)


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(
    tx_id: int,
    tx_in: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tx = _get_owned_or_404(db, Transaction, tx_id, current_user.id, "Transação")
    if tx_in.account_id is not None:
        _get_owned_or_404(db, Account, tx_in.account_id, current_user.id, "Conta")
        tx.account_id = tx_in.account_id
    if tx_in.category_id is not None:
        category = _get_owned_or_404(db, Category, tx_in.category_id, current_user.id, "Categoria")
        tx.category_id = tx_in.category_id
    if tx_in.type is not None:
        tx.type = tx_in.type
    if tx_in.amount is not None:
        tx.amount = tx_in.amount
    if tx_in.date is not None:
        tx.date = _parse_date(tx_in.date)
    if tx_in.description is not None:
        tx.description = tx_in.description

    category = db.query(Category).filter(Category.id == tx.category_id).first()
    if category.type != tx.type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O tipo da transação deve ser igual ao tipo da categoria",
        )

    db.commit()
    db.refresh(tx)
    return _transaction_out(tx)


@router.delete("/transactions/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tx = _get_owned_or_404(db, Transaction, tx_id, current_user.id, "Transação")
    db.delete(tx)
    db.commit()
    return None
