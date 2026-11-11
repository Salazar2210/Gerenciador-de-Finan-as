from decimal import Decimal

from pydantic import BaseModel, Field


class BudgetBase(BaseModel):
    category_id: int
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    limit_amount: Decimal = Field(gt=0)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    limit_amount: Decimal = Field(gt=0)


class BudgetOut(BudgetBase):
    id: int
    user_id: int
    created_at: str

    model_config = {"from_attributes": True}


class BudgetStatusItem(BaseModel):
    category_id: int
    category_name: str
    limit_amount: str
    spent: str
    percentage_used: str
    status: str
