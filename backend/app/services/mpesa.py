"""M-Pesa Daraja STK Push client."""
import base64
from datetime import datetime

import httpx

from app.config import settings


def _base_url() -> str:
    if settings.mpesa_env == "sandbox":
        return "https://sandbox.safaricom.co.ke"
    if settings.mpesa_env == "production":
        return "https://api.safaricom.co.ke"
    raise ValueError("MPESA_ENV must be sandbox or production.")


def get_access_token() -> str:
    r = httpx.get(
        f"{_base_url()}/oauth/v1/generate",
        params={"grant_type": "client_credentials"},
        auth=(settings.mpesa_consumer_key, settings.mpesa_consumer_secret),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def stk_push(phone: str, amount: int, account_reference: str, description: str) -> dict:
    """phone must be 2547XXXXXXXX. amount is a whole number of shillings."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{settings.mpesa_shortcode}{settings.mpesa_passkey}{timestamp}".encode()).decode()
    payload = {
        "BusinessShortCode": settings.mpesa_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": settings.mpesa_transaction_type,
        "Amount": amount,
        "PartyA": phone,
        "PartyB": settings.mpesa_party_b or settings.mpesa_shortcode,
        "PhoneNumber": phone,
        "CallBackURL": settings.mpesa_callback_url,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }
    r = httpx.post(
        f"{_base_url()}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
