from datetime import date, datetime, time, timedelta
from decimal import Decimal
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_roles
from app.config import settings
from app.database import get_db
from app.models import Category, Order, Product, User
from app.schemas import ClientProfileUpdate, OrderStatusUpdate, ProductCreate, ProductUpdate, UserRoleUpdate

router = APIRouter(prefix="/api/dashboard", tags=["dashboards"])
MANAGED_ORDER_STATUSES = ("pending", "paid", "processing", "shipped", "delivered", "cancelled", "failed")
REVENUE_STATUSES = ("paid", "processing", "shipped", "delivered")
LOW_STOCK_LIMIT = 5


def _product_row(product: Product) -> dict:
    return {
        "id": product.id,
        "category_id": product.category_id,
        "category_name": product.category.name,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "image_url": product.image_url,
        "price": product.price,
        "stock_quantity": product.stock_quantity,
        "is_active": product.is_active,
    }


def _order_row(order: Order) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "user_id": order.user_id,
        "customer_name": order.customer_name,
        "customer_email": order.user.email if order.user else None,
        "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address,
        "total_amount": order.total_amount,
        "status": order.status,
        "created_at": order.created_at,
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in order.items
        ],
    }


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "product"


def _unique_slug(name: str, db: Session, product_id: int | None = None) -> str:
    base = _slugify(name)
    slug, suffix = base, 2
    while True:
        query = select(Product.id).where(Product.slug == slug)
        if product_id is not None:
            query = query.where(Product.id != product_id)
        if not db.scalar(query):
            return slug
        slug = f"{base}-{suffix}"
        suffix += 1


def _load_orders(db: Session, limit: int = 100) -> list[Order]:
    return db.scalars(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
    ).all()


def _load_products(db: Session, include_inactive: bool = True) -> list[Product]:
    query = select(Product).options(selectinload(Product.category)).order_by(Product.name)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    return db.scalars(query).all()


@router.get("/admin")
def admin_overview(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    eligible = Order.status.in_(REVENUE_STATUSES)
    revenue = db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0)).where(eligible)) or Decimal("0")
    total_orders = db.scalar(select(func.count(Order.id))) or 0
    open_orders = db.scalar(select(func.count(Order.id)).where(Order.status.in_(("pending", "paid", "processing")))) or 0
    customer_count = db.scalar(select(func.count(User.id)).where(User.role == "client", User.is_active.is_(True))) or 0
    staff_count = db.scalar(select(func.count(User.id)).where(User.role == "staff", User.is_active.is_(True))) or 0
    product_count = db.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True))) or 0
    low_stock_count = db.scalar(
        select(func.count(Product.id)).where(Product.is_active.is_(True), Product.stock_quantity <= LOW_STOCK_LIMIT)
    ) or 0

    start_day = date.today() - timedelta(days=6)
    revenue_rows = db.execute(
        select(func.date(Order.created_at), func.sum(Order.total_amount))
        .where(eligible, Order.created_at >= datetime.combine(start_day, time.min))
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    ).all()
    revenue_by_date = {str(day): amount for day, amount in revenue_rows}
    sales_by_day = [
        {
            "date": (start_day + timedelta(days=index)).isoformat(),
            "revenue": revenue_by_date.get((start_day + timedelta(days=index)).isoformat(), Decimal("0")),
        }
        for index in range(7)
    ]
    status_rows = db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all()
    low_stock = db.scalars(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.is_active.is_(True), Product.stock_quantity <= LOW_STOCK_LIMIT)
        .order_by(Product.stock_quantity, Product.name)
        .limit(10)
    ).all()

    return {
        "metrics": {
            "revenue": revenue,
            "orders": total_orders,
            "open_orders": open_orders,
            "customers": customer_count,
            "staff": staff_count,
            "products": product_count,
            "low_stock": low_stock_count,
        },
        "sales_by_day": sales_by_day,
        "orders_by_status": [{"status": status, "count": count} for status, count in status_rows],
        "recent_orders": [_order_row(order) for order in _load_orders(db, 8)],
        "low_stock_products": [_product_row(product) for product in low_stock],
    }


@router.get("/staff")
def staff_overview(
    db: Session = Depends(get_db),
    _staff: User = Depends(require_roles("admin", "staff")),
):
    orders = _load_orders(db)
    new_orders = db.scalar(
        select(func.count(Order.id)).where(Order.status.in_(("pending", "paid")))
    ) or 0
    processing_orders = db.scalar(
        select(func.count(Order.id)).where(Order.status == "processing")
    ) or 0
    shipped_orders = db.scalar(
        select(func.count(Order.id)).where(Order.status == "shipped")
    ) or 0
    low_stock_count = db.scalar(
        select(func.count(Product.id)).where(
            Product.is_active.is_(True),
            Product.stock_quantity <= LOW_STOCK_LIMIT,
        )
    ) or 0
    low_stock = db.scalars(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.is_active.is_(True), Product.stock_quantity <= LOW_STOCK_LIMIT)
        .order_by(Product.stock_quantity, Product.name)
        .limit(20)
    ).all()
    return {
        "metrics": {
            "new_orders": new_orders,
            "processing": processing_orders,
            "ready_to_ship": shipped_orders,
            "low_stock": low_stock_count,
        },
        "orders": [_order_row(order) for order in orders if order.status not in ("delivered", "cancelled", "failed")],
        "low_stock_products": [_product_row(product) for product in low_stock],
    }


@router.get("/orders")
def list_dashboard_orders(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "staff")),
):
    return [_order_row(order) for order in _load_orders(db)]


@router.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "staff")),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if payload.status not in MANAGED_ORDER_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid order status.")
    order.status = payload.status
    db.commit()
    return {"id": order.id, "status": order.status}


@router.get("/products")
def list_dashboard_products(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "staff")),
):
    return [_product_row(product) for product in _load_products(db)]


@router.post("/products", status_code=201)
def create_dashboard_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "staff")),
):
    if not db.get(Category, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found.")
    product = Product(
        **payload.model_dump(exclude={"name"}),
        name=payload.name.strip(),
        slug=_unique_slug(payload.name, db),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _product_row(product)


@router.patch("/products/{product_id}")
def update_dashboard_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "staff")),
):
    product = db.scalar(
        select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and not db.get(Category, changes["category_id"]):
        raise HTTPException(status_code=404, detail="Category not found.")
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        changes["slug"] = _unique_slug(changes["name"], db, product.id)
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return _product_row(product)


@router.delete("/products/{product_id}", status_code=204)
def deactivate_dashboard_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "staff")),
) -> None:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    product.is_active = False
    db.commit()


@router.get("/team")
def list_dashboard_team(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc()).limit(200)).all()
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.patch("/team/{user_id}/role")
def update_team_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    if user_id == admin.id:
        raise HTTPException(status_code=409, detail="You cannot change your own administrator role.")
    member = db.get(User, user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Account not found.")
    if member.role == "admin" or (
        settings.admin_email and member.email.lower() == settings.admin_email.strip().lower()
    ):
        raise HTTPException(status_code=409, detail="The configured administrator account cannot be reassigned.")
    member.role = payload.role
    member.is_admin = False
    db.commit()
    return {"id": member.id, "role": member.role}


@router.get("/client")
def client_overview(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()
    paid_orders = [order for order in orders if order.status in REVENUE_STATUSES]
    return {
        "profile": {"id": user.id, "full_name": user.full_name, "email": user.email, "phone": user.phone},
        "metrics": {
            "orders": len(orders),
            "total_spent": sum((order.total_amount for order in paid_orders), Decimal("0")),
        },
        "orders": [_order_row(order) for order in orders],
    }


@router.patch("/client/profile")
def update_client_profile(
    payload: ClientProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    changes = payload.model_dump(exclude_unset=True)
    if "full_name" in changes:
        full_name = changes["full_name"].strip()
        if len(full_name) < 2:
            raise HTTPException(status_code=422, detail="Enter your full name.")
        user.full_name = full_name
    if "phone" in changes:
        phone = (changes["phone"] or "").strip().replace(" ", "").replace("-", "").replace("+", "")
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        if phone and not re.fullmatch(r"254[17]\d{8}", phone):
            raise HTTPException(status_code=422, detail="Enter a valid Kenyan mobile number.")
        user.phone = phone or None
    db.commit()
    db.refresh(user)
    return {"id": user.id, "full_name": user.full_name, "email": user.email, "phone": user.phone}
