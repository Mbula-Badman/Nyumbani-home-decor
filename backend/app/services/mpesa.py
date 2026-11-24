"""M-Pesa Daraja helpers (Phase 6). NOT connected to any route yet.

Credentials are read from .env through app.config.settings, never from the frontend.
"""
import base64
from datetime import datetime

import httpx

from app.config import settings

BASE_URL = "https://sandbox.safaricom.co.ke" if settings.mpesa_env == "sandbox" else "https://api.safaricom.co.ke"


def get_access_token() -> str:
    r = httpx.get(
        f"{BASE_URL}/oauth/v1/generate",
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

    # TODO (CLIENT): the values below depend on whether the client has a Till or a Paybill.
    #   Paybill: BusinessShortCode = PartyB = the Paybill number, TransactionType = CustomerPayBillOnline.
    #   Till:    BusinessShortCode = the Head Office / store number Safaricom gives for the Till,
    #            PartyB = the Till number, TransactionType = CustomerBuyGoodsOnline.
    # Confirm both numbers with the client before going live.
    payload = {
        "BusinessShortCode": settings.mpesa_shortcode,  # TODO (CLIENT): Till/Paybill shortcode
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": settings.mpesa_transaction_type,
        "Amount": amount,
        "PartyA": phone,
        "PartyB": settings.mpesa_shortcode,  # TODO (CLIENT): for a Till, put the Till number here
        "PhoneNumber": phone,
        "CallBackURL": settings.mpesa_callback_url,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }
    r = httpx.post(
        f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
