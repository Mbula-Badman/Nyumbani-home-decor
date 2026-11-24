from getpass import getpass

from sqlalchemy import func, select

from app.auth import hash_password
from app.config import settings
from app.database import SessionLocal
from app.models import User


def main() -> None:
    email = settings.admin_email.strip().lower()
    if not email:
        raise SystemExit("Set ADMIN_EMAIL in the backend environment before creating the administrator.")

    full_name = input("Administrator name: ").strip()
    if len(full_name) < 2:
        raise SystemExit("Enter a name with at least two characters.")
    password = getpass("Administrator password (8+ characters): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least eight characters.")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            user = User(full_name=full_name, email=email, password_hash=hash_password(password))
            db.add(user)
        else:
            user.full_name = full_name
            user.password_hash = hash_password(password)
            user.is_active = True
        user.role = "admin"
        user.is_admin = True
        db.commit()
    print(f"Administrator account provisioned for {email}.")


if __name__ == "__main__":
    main()
