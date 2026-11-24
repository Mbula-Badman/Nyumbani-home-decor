import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

COOKIE_NAME = "nyumbani_session"
SESSION_SECONDS = 60 * 60 * 24 * 7
PASSWORD_ITERATIONS = 310_000
_SESSION_KEY = settings.auth_secret.encode() if settings.auth_secret else secrets.token_bytes(32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"{PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def create_session(user_id: int) -> str:
    payload = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + SESSION_SECONDS}).encode())
    signature = _b64(hmac.new(_SESSION_KEY, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def _session_user_id(token: str) -> int | None:
    try:
        payload, signature = token.split(".")
        expected = _b64(hmac.new(_SESSION_KEY, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        decoded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(decoded))
        if data["exp"] <= int(time.time()):
            return None
        return int(data["sub"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, binascii.Error):
        return None


def set_session_cookie(response: Response, user_id: int) -> None:
    if settings.app_env == "production" and not settings.auth_secret:
        raise RuntimeError("AUTH_SECRET must be configured in production.")
    response.set_cookie(
        COOKIE_NAME,
        create_session(user_id),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )


def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(COOKIE_NAME, "")
    user_id = _session_user_id(token)
    user = db.get(User, user_id) if user_id else None
    return user if user and user.is_active else None


def get_current_user(user: User | None = Depends(get_optional_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user


def require_roles(*roles: str) -> Callable:
    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to access this dashboard.")
        return user

    return check_role


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")
