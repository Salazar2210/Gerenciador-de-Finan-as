from fastapi import FastAPI

from app.routers import accounts, auth, budgets, categories, reports, transactions, users

app = FastAPI(title="Gerenciador de Finanças Pessoais", version="1.0.0")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
