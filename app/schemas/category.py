from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    type: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)


class CategoryOut(CategoryBase):
    id: int
    user_id: int
    created_at: str

    model_config = {"from_attributes": True}
