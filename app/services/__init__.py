from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User


def _money(value) -> str:
    """Formata um Decimal para string com duas casas decimais."""
    if value is None:
        return "0.00"
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, full_name: str, hashed_password: str) -> User:
    user = User(email=email.lower(), full_name=full_name, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    from app.core.security import verify_password

    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_account_or_404(db: Session, account_id: int, user_id: int) -> Account:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if account is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada",
        )
    return account


def get_category_or_404(db: Session, category_id: int, user_id: int) -> Category:
    category = (
        db.query(Category).filter(Category.id == category_id, Category.user_id == user_id).first()
    )
    if category is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    return category


def calculate_account_balance(db: Session, account: Account) -> Decimal:
    income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.account_id == account.id,
            Transaction.type == "INCOME",
        )
        .scalar()
    )
    expense = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.account_id == account.id,
            Transaction.type == "EXPENSE",
        )
        .scalar()
    )
    return Decimal(account.initial_balance) + Decimal(income or 0) - Decimal(expense or 0)
