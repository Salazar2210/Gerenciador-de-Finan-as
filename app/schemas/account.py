from decimal import Decimal

from pydantic import BaseModel, Field


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    initial_balance: Decimal = Field(default=Decimal("0.00"))


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    initial_balance: Decimal | None = None


class AccountOut(AccountBase):
    id: int
    user_id: int
    balance: str
    created_at: str

    model_config = {"from_attributes": True}
