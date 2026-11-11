from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.transaction import Transaction
from app.schemas.report import (
    CategoryReportItem,
    MonthlyEvolutionItem,
    MonthlySummary,
)

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


@router.get("/reports/monthly-summary", response_model=MonthlySummary)
def monthly_summary(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "INCOME",
            Transaction.date >= start,
            Transaction.date < end,
        )
        .scalar()
    )
    expense = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "EXPENSE",
            Transaction.date >= start,
            Transaction.date < end,
        )
        .scalar()
    )
    income_dec = Decimal(income or 0)
    expense_dec = Decimal(expense or 0)
    return MonthlySummary(
        year=year,
        month=month,
        total_income=_money(income_dec),
        total_expense=_money(expense_dec),
        balance=_money(income_dec - expense_dec),
    )


@router.get("/reports/by-category", response_model=list[CategoryReportItem])
def by_category(
    year: int = Query(...),
    month: int = Query(...),
    type: str = Query(default="EXPENSE"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if type not in ("INCOME", "EXPENSE"):
        type = "EXPENSE"
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    rows = (
        db.query(
            Transaction.category_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == type,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category_id)
        .all()
    )

    total_all = sum((Decimal(r.total or 0) for r in rows), Decimal(0))

    # buscar nomes das categorias
    cat_ids = [r.category_id for r in rows]
    categories = {}
    if cat_ids:
        from app.models.category import Category

        cats = db.query(Category).filter(Category.id.in_(cat_ids)).all()
        categories = {c.id: c.name for c in cats}

    items = []
    for r in rows:
        total_dec = Decimal(r.total or 0)
        items.append(
            CategoryReportItem(
                category_id=r.category_id,
                category_name=categories.get(r.category_id, ""),
                total=_money(total_dec),
                percentage=_percentage(total_dec, total_all),
            )
        )
    items.sort(key=lambda x: Decimal(x.total), reverse=True)
    return items


@router.get("/reports/monthly-evolution", response_model=list[MonthlyEvolutionItem])
def monthly_evolution(
    months: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    now = datetime.now(UTC)
    # monta lista dos últimos N meses terminando no mês atual, mais antigo primeiro
    base_year = now.year
    base_month = now.month
    items_out = []
    for i in range(months - 1, -1, -1):
        total_months = i
        y = base_year
        m = base_month - total_months
        while m <= 0:
            m += 12
            y -= 1
        start = date(y, m, 1)
        if m == 12:
            end = date(y + 1, 1, 1)
        else:
            end = date(y, m + 1, 1)

        income = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.type == "INCOME",
                Transaction.date >= start,
                Transaction.date < end,
            )
            .scalar()
        )
        expense = (
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.type == "EXPENSE",
                Transaction.date >= start,
                Transaction.date < end,
            )
            .scalar()
        )
        income_dec = Decimal(income or 0)
        expense_dec = Decimal(expense or 0)
        items_out.append(
            MonthlyEvolutionItem(
                year=y,
                month=m,
                total_income=_money(income_dec),
                total_expense=_money(expense_dec),
                balance=_money(income_dec - expense_dec),
            )
        )
    return items_out
