"""Pydantic input models - API-level validation. [SSDLC: input validation layer]
MongoDB $jsonSchema validators remain the second line of defence."""
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(default="", max_length=60)
    email: EmailStr
    phone: str = Field(min_length=9, max_length=20)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if not any(c.isdigit() for c in v) or not any(c.isalpha() for c in v):
            raise ValueError("Password needs letters and numbers")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CartAddIn(BaseModel):
    product_id: str = Field(min_length=24, max_length=24)
    quantity: int = Field(ge=1, le=99, default=1)


class CartQtyIn(BaseModel):
    quantity: int = Field(ge=0, le=99)


class AddressIn(BaseModel):
    address_line_1: str = Field(min_length=3, max_length=120)
    address_line_2: str | None = None
    city: str = Field(min_length=2, max_length=60)
    province: str = Field(min_length=2, max_length=60)
    postal_code: str | None = Field(default=None, max_length=10)
    latitude: float | None = None
    longitude: float | None = None


class CheckoutIn(BaseModel):
    address: AddressIn
    delivery_option: str = Field(pattern="^(BASE|DOOR_TO_DOOR)$")
    save_address: bool = False
    idempotency_key: str = Field(min_length=8, max_length=64)


class TopUpIn(BaseModel):
    amount: Decimal = Field(ge=Decimal("10"), le=Decimal("5000"))


class MerchantStatusIn(BaseModel):
    order_id: str = Field(min_length=24, max_length=24)
    status: str


class DeliveryStatusIn(BaseModel):
    status: str