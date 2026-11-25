from decimal import Decimal
from datetime import datetime
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Order, OrderItem, Payment, Product, User
from app.schemas import CheckoutOut, CheckoutRequest
from app.services.mpesa import stk_push

router = APIRouter(prefix="/api", tags=["checkout"])

DELIVERY_FEES = {"town": Decimal("150"), "kenya": Decimal("350"), "pickup": Decimal("0")}
logger = logging.getLogger(__name__)


def _restore_order_stock(db: Session, order: Order) -> None:
    for item in order.items:
        if item.product_id is not None:
            product = db.get(Product, item.product_id)
            if product:
                product.stock_quantity += item.quantity


def _fail_payment(db: Session, payment: Payment, description: str, status: str = "failed") -> None:
    if payment.status != "pending":
        return
    payment.status = status
    payment.result_desc = description[:255]
    payment.order.status = "cancelled" if status == "cancelled" else "failed"
    _restore_order_stock(db, payment.order)
    db.commit()


def _callback_items(callback: dict) -> dict[str, object]:
    metadata = callback.get("CallbackMetadata")
    if not isinstance(metadata, dict):
        return {}
    items = metadata.get("Item", [])
    if not isinstance(items, list):
        return {}
    return {
        item["Name"]: item.get("Value")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("Name"), str)
    }


def _apply_mpesa_callback(db: Session, callback: dict) -> None:
    checkout_request_id = callback.get("CheckoutRequestID")
    if not isinstance(checkout_request_id, str) or not checkout_request_id:
        raise HTTPException(status_code=400, detail="M-Pesa callback is missing its checkout request ID.")

    payment = db.scalar(
        select(Payment)
        .where(Payment.checkout_request_id == checkout_request_id)
        .with_for_update()
    )
    if not payment:
        logger.warning("Received M-Pesa callback for an unknown checkout request.")
        return
    if payment.status != "pending":
        return

    result_code = callback.get("ResultCode")
    if not isinstance(result_code, int):
        raise HTTPException(status_code=400, detail="M-Pesa callback has an invalid result code.")
    payment.result_code = result_code
    payment.result_desc = str(callback.get("ResultDesc", ""))[:255]

    if result_code != 0:
        status = "cancelled" if result_code == 1032 else "timeout" if result_code == 1037 else "failed"
        _fail_payment(db, payment, payment.result_desc or "M-Pesa payment was not completed.", status)
        return

    metadata = _callback_items(callback)
    try:
        callback_amount = Decimal(str(metadata["Amount"]))
        receipt = str(metadata["MpesaReceiptNumber"])
        callback_phone = str(metadata["PhoneNumber"]).removesuffix(".0")
    except (KeyError, ArithmeticError, ValueError):
        raise HTTPException(status_code=400, detail="Successful M-Pesa callback is missing payment details.") from None

    if callback_amount != payment.amount or callback_phone != payment.customer_phone or not receipt:
        logger.warning("M-Pesa callback payment details did not match the stored order.")
        raise HTTPException(status_code=400, detail="M-Pesa callback payment details did not match the order.")

    payment.status = "success"
    payment.mpesa_receipt_number = receipt[:30]
    payment.order.status = "paid"
    db.commit()


@router.post("/checkout", response_model=CheckoutOut)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if settings.mpesa_missing_variables:
        missing = ", ".join(settings.mpesa_missing_variables)
        raise HTTPException(
            status_code=503,
            detail=f"M-Pesa is not configured. Add these values to backend/.env: {missing}.",
        )

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
    if total <= 0:
        raise HTTPException(status_code=422, detail="M-Pesa checkout total must be greater than zero.")
    if total != total.to_integral_value():
        raise HTTPException(status_code=422, detail="M-Pesa checkout totals must be whole Kenyan shillings.")

    order_number = f"NH-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"
    order = Order(
        order_number=order_number,
        user_id=user.id,
        customer_name=name,
        customer_phone=phone,
        delivery_address=payload.delivery,
        total_amount=total,
        status="pending",
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

    payment = Payment(
        order_id=order.id,
        provider="mpesa",
        status="pending",
        amount=total,
        customer_phone=phone,
        result_desc="Waiting for customer to complete M-Pesa payment.",
    )
    db.add(payment)
    db.commit()

    try:
        response = stk_push(phone, int(total), order.order_number, "Nyumbani Home order")
    except (httpx.HTTPError, KeyError, ValueError) as error:
        logger.exception("Could not start M-Pesa STK push.")
        _fail_payment(db, payment, "Could not start M-Pesa payment. Please try again.")
        raise HTTPException(
            status_code=502,
            detail="Could not start the M-Pesa payment. Check your sandbox settings and try again.",
        ) from error

    if not isinstance(response, dict):
        _fail_payment(db, payment, "M-Pesa returned an invalid payment response.")
        raise HTTPException(status_code=502, detail="M-Pesa returned an invalid payment response.")

    if str(response.get("ResponseCode")) != "0":
        description = str(response.get("ResponseDescription") or response.get("errorMessage") or "M-Pesa rejected the payment request.")
        _fail_payment(db, payment, description)
        raise HTTPException(status_code=502, detail=description)

    checkout_request_id = response.get("CheckoutRequestID")
    merchant_request_id = response.get("MerchantRequestID")
    if not isinstance(checkout_request_id, str) or not isinstance(merchant_request_id, str):
        _fail_payment(db, payment, "M-Pesa returned an incomplete payment response.")
        raise HTTPException(status_code=502, detail="M-Pesa returned an incomplete payment response.")

    payment.checkout_request_id = checkout_request_id
    payment.merchant_request_id = merchant_request_id
    payment.result_desc = str(response.get("CustomerMessage") or "Check your phone and enter your M-Pesa PIN.")[:255]
    db.commit()
    db.refresh(order)
    return CheckoutOut(
        order_id=order.id,
        order_number=order.order_number,
        status=payment.status,
        checkout_request_id=checkout_request_id,
        total=total,
        message=payment.result_desc,
    )


@router.get("/payments/{checkout_request_id}")
def get_payment_status(
    checkout_request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payment = db.scalar(
        select(Payment)
        .join(Order)
        .where(Payment.checkout_request_id == checkout_request_id, Order.user_id == user.id)
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found.")
    return {
        "order_number": payment.order.order_number,
        "order_status": payment.order.status,
        "status": payment.status,
        "receipt": payment.mpesa_receipt_number,
        "message": payment.result_desc,
    }


@router.post("/mpesa/callback")
def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    body = payload.get("Body") if isinstance(payload, dict) else None
    callback = body.get("stkCallback") if isinstance(body, dict) else None
    if not isinstance(callback, dict):
        raise HTTPException(status_code=400, detail="Invalid M-Pesa callback payload.")
    _apply_mpesa_callback(db, callback)
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
