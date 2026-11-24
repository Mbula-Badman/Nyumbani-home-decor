from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Enter your full name.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: Literal["client", "staff", "admin"]


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int
    category_name: str
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None
    price: Decimal
    stock_quantity: int


class CheckoutItem(BaseModel):
    id: int
    qty: int


class CheckoutRequest(BaseModel):
    name: str
    phone: str
    delivery: str = "Nakuru town"
    items: list[CheckoutItem]


class CheckoutOut(BaseModel):
    order_id: int
    order_number: str
    status: str
    receipt: str
    total: Decimal


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category_id: int = Field(ge=1)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    category_id: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "paid", "processing", "shipped", "delivered", "cancelled", "failed"]


class UserRoleUpdate(BaseModel):
    role: Literal["client", "staff"]


class ClientProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
