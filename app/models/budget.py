from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Budget(BaseModel):
    __tablename__ = "budgets"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[int] = mapped_column(nullable=False)
    limit_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", backref="budgets")
    category = relationship("Category", backref="budgets")

    __table_args__ = (
        CheckConstraint("year >= 2000 AND year <= 2100", name="chk_budget_year"),
        CheckConstraint("month >= 1 AND month <= 12", name="chk_budget_month"),
        CheckConstraint("limit_amount > 0", name="chk_budget_limit_amount"),
        text("UNIQUE (user_id, category_id, year, month)"),
    )
