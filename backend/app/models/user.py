from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("phone IS NULL OR (length(phone) = 12 AND substr(phone, 1, 3) = '254')", name="ck_users_phone_format"),
        CheckConstraint("role IN ('client','staff','admin')", name="ck_users_role_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(12), nullable=True)  # format 2547XXXXXXXX
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="client", server_default="client")
    is_admin: Mapped[bool] = mapped_column(Boolean, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[list["Order"]] = relationship(back_populates="user")  # noqa: F821
