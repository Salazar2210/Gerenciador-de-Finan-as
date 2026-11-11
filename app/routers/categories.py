from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter()


def _category_out(category: Category) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        user_id=category.user_id,
        name=category.name,
        type=category.type,
        created_at=category.created_at.isoformat(),
    )


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if category_in.type not in ("INCOME", "EXPENSE"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo inválido. Use INCOME ou EXPENSE.",
        )
    existing = (
        db.query(Category)
        .filter(
            Category.user_id == current_user.id,
            Category.type == category_in.type,
            func.lower(Category.name) == func.lower(category_in.name),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma categoria com este nome e tipo",
        )
    category = Category(
        user_id=current_user.id,
        name=category_in.name,
        type=category_in.type,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return _category_out(category)


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Category).filter(Category.user_id == current_user.id)
    if type:
        if type not in ("INCOME", "EXPENSE"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo inválido. Use INCOME ou EXPENSE.",
            )
        query = query.filter(Category.type == type)
    categories = query.order_by(Category.id.asc()).all()
    return [_category_out(c) for c in categories]


@router.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == current_user.id)
        .first()
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    return _category_out(category)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == current_user.id)
        .first()
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    if category_in.name is not None:
        existing = (
            db.query(Category)
            .filter(
                Category.user_id == current_user.id,
                Category.id != category_id,
                Category.type == category.type,
                func.lower(Category.name) == func.lower(category_in.name),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma categoria com este nome e tipo",
            )
        category.name = category_in.name
    db.commit()
    db.refresh(category)
    return _category_out(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == current_user.id)
        .first()
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
    from app.models.transaction import Transaction

    has_tx = db.query(Transaction.id).filter(Transaction.category_id == category_id).first()
    if has_tx:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir uma categoria que possui transações",
        )
    from app.models.budget import Budget

    db.query(Budget).filter(Budget.category_id == category_id).delete()
    db.delete(category)
    db.commit()
    return None
