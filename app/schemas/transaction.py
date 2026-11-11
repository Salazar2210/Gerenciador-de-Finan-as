from decimal import Decimal

from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    account_id: int
    category_id: int
    type: str
    amount: Decimal = Field(gt=0)
    date: str
    description: str | None = Field(default=None, max_length=255)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: int | None = None
    category_id: int | None = None
    type: str | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    date: str | None = None
    description: str | None = Field(default=None, max_length=255)


class TransactionOut(TransactionBase):
    id: int
    user_id: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class TransactionsPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int
