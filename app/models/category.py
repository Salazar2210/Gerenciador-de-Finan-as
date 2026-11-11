from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class CategoryType(str):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class Category(BaseModel):
    __tablename__ = "categories"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("INCOME", "EXPENSE", name="category_type"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", backref="categories")

    __table_args__ = (text("UNIQUE (user_id, lower(name), type)"),)
