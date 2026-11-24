from decimal import Decimal
from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Order, OrderItem, Payment, Product, User
from app.schemas import CheckoutOut, CheckoutRequest

router = APIRouter(prefix="/api", tags=["checkout"])

DELIVERY_FEES = {"town": Decimal("150"), "kenya": Decimal("350"), "pickup": Decimal("0")}


@router.post("/checkout", response_model=CheckoutOut)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = payload.name.strip()
    phone = payload.phone.strip().replace(" ", "").replace("-", "")
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Enter a valid customer name.")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not (phone.startswith("254") and len(phone) == 12 and phone.isdigit()):
        raise HTTPException(status_code=422, detail="Enter a valid Kenyan M-Pesa phone number.")
    if not payload.items:
        raise HTTPException(status_code=422, detail="Cart is empty.")

    subtotal = Decimal("0")
    lines: list[tuple[Product, int]] = []
    for line in payload.items:
        if line.qty < 1:
            raise HTTPException(status_code=422, detail="Quantity must be at least one.")
        product = db.get(Product, line.id)
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail=f"Product {line.id} was not found.")
        if product.stock_quantity < line.qty:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}.")
        subtotal += product.price * line.qty
        lines.append((product, line.qty))

    delivery_key = payload.delivery if payload.delivery in DELIVERY_FEES else "town"
    total = subtotal + DELIVERY_FEES[delivery_key]
    order_number = f"NH-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"
    order = Order(
        order_number=order_number,
        user_id=user.id,
        customer_name=name,
        customer_phone=phone,
        delivery_address=payload.delivery,
        total_amount=total,
        status="paid",
    )
    db.add(order)
    db.flush()

    for product, qty in lines:
        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=qty,
            unit_price=product.price,
        ))
        product.stock_quantity -= qty

    receipt = f"DEMO-{secrets.token_hex(4).upper()}"
    db.add(Payment(
        order_id=order.id,
        provider="demo-mpesa",
        status="success",
        amount=total,
        customer_phone=phone,
        mpesa_receipt_number=receipt,
        result_code=0,
        result_desc="Demo payment completed.",
    ))
    db.commit()
    db.refresh(order)
    return CheckoutOut(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status,
        receipt=receipt,
        total=total,
    )
