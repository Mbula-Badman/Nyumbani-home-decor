from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

PAYMENT_STATUSES = ("pending", "success", "failed", "cancelled", "timeout")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("status IN ('pending','success','failed','cancelled','timeout')", name="ck_payments_status_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20), server_default="mpesa")
    status: Mapped[str] = mapped_column(String(20), server_default="pending", index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    customer_phone: Mapped[str] = mapped_column(String(12))
    merchant_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Unique so a callback can never be applied to two payments, or twice (duplicate protection).
    checkout_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    mpesa_receipt_number: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True, index=True)
    result_code: Mapped[int | None] = mapped_column(nullable=True)
    result_desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    order: Mapped["Order"] = relationship(back_populates="payments")  # noqa: F821
