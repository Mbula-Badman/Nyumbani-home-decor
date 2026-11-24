from decimal import Decimal

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
