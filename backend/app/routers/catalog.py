from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, Product
from app.schemas import CategoryOut, ProductOut

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.get("/products", response_model=list[ProductOut])
def list_products(
    q: str | None = Query(None, max_length=100, description="Search by product name"),
    category: str | None = Query(None, description="Category slug"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Product).options(selectinload(Product.category)).where(Product.is_active.is_(True))
    if category:
        stmt = stmt.join(Category, Product.category_id == Category.id).where(Category.slug == category)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q.strip()}%"))
    return db.scalars(stmt.order_by(Product.id).limit(limit).offset(offset)).all()


@router.get("/products/{slug}", response_model=ProductOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    product = db.scalar(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.slug == slug, Product.is_active.is_(True))
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product
