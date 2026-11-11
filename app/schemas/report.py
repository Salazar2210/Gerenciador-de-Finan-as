from pydantic import BaseModel


class MonthlySummary(BaseModel):
    year: int
    month: int
    total_income: str
    total_expense: str
    balance: str


class CategoryReportItem(BaseModel):
    category_id: int
    category_name: str
    total: str
    percentage: str


class MonthlyEvolutionItem(BaseModel):
    year: int
    month: int
    total_income: str
    total_expense: str
    balance: str
