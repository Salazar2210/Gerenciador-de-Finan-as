from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budget import (
    BudgetCreate,
    BudgetOut,
    BudgetStatusItem,
    BudgetUpdate,
)
from app.services import get_category_or_404

router = APIRouter()


def _money(value) -> str:
    if value is None:
        return "0.00"
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _percentage(part, whole) -> str:
    if not whole or whole == 0:
        return "0.00"
    return str(
        (Decimal(part) / Decimal(whole) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


@router.post("/budgets", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_in: BudgetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    category = get_category_or_404(db, budget_in.category_id, current_user.id)
    if category.type != "EXPENSE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Orçamento só pode ser criado para categoria do tipo EXPENSE",
        )
    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.category_id == budget_in.category_id,
            Budget.year == budget_in.year,
            Budget.month == budget_in.month,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe orçamento para esta categoria neste mês/ano",
        )
    budget = Budget(
        user_id=current_user.id,
        category_id=budget_in.category_id,
        year=budget_in.year,
        month=budget_in.month,
        limit_amount=budget_in.limit_amount,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return BudgetOut(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        year=budget.year,
        month=budget.month,
        limit_amount=budget.limit_amount,
        created_at=budget.created_at.isoformat(),
    )


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Budget).filter(Budget.user_id == current_user.id)
    if year is not None:
        query = query.filter(Budget.year == year)
    if month is not None:
        query = query.filter(Budget.month == month)
    budgets = query.order_by(Budget.year, Budget.month, Budget.id).all()
    return [
        BudgetOut(
            id=b.id,
            user_id=b.user_id,
            category_id=b.category_id,
            year=b.year,
            month=b.month,
            limit_amount=b.limit_amount,
            created_at=b.created_at.isoformat(),
        )
        for b in budgets
    ]


@router.patch("/budgets/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    budget_in: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    budget = (
        db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    )
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orçamento não encontrado",
        )
    budget.limit_amount = budget_in.limit_amount
    db.commit()
    db.refresh(budget)
    return BudgetOut(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        year=budget.year,
        month=budget.month,
        limit_amount=budget.limit_amount,
        created_at=budget.created_at.isoformat(),
    )


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    budget = (
        db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    )
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orçamento não encontrado",
        )
    db.delete(budget)
    db.commit()
    return None


@router.get("/budgets/status", response_model=list[BudgetStatusItem])
def budgets_status(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    budgets = (
        db.query(Budget, Category)
        .join(Category, Budget.category_id == Category.id)
        .filter(
            Budget.user_id == current_user.id,
            Budget.year == year,
            Budget.month == month,
        )
        .all()
    )
    result = []
    for budget, category in budgets:
        spent = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.category_id == category.id,
                Transaction.type == "EXPENSE",
                func.extract("year", Transaction.date) == year,
                func.extract("month", Transaction.date) == month,
            )
            .scalar()
        )
        spent_dec = Decimal(spent or 0)
        pct = _percentage(spent_dec, budget.limit_amount)
        if spent_dec > budget.limit_amount:
            status_str = "EXCEEDED"
        elif spent_dec <= budget.limit_amount and Decimal(pct) >= 80:
            status_str = "WARNING"
        else:
            status_str = "OK"
        result.append(
            BudgetStatusItem(
                category_id=category.id,
                category_name=category.name,
                limit_amount=_money(budget.limit_amount),
                spent=_money(spent_dec),
                percentage_used=pct,
                status=status_str,
            )
        )
    return result
