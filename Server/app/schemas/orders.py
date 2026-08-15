from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints

from app.schemas.auth import InputModel, Name, Phone

Street = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
City = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PostalCode = Annotated[str, StringConstraints(strip_whitespace=True,
                                              pattern=r"^[A-Za-z0-9 \-]{3,12}$")]

OrderStatus = Literal["pending", "paid", "shipped", "cancelled"]


class OrderCreate(InputModel):
    first_name: Name
    last_name: Name
    street: Street
    city: City
    apartment: str | None = Field(None, max_length=40)
    postal_code: PostalCode
    phone: Phone | None = None


class ShippingSnapshot(BaseModel):
    first_name: str
    last_name: str
    street: str
    city: str
    apartment: str | None
    postal_code: str
    phone: str | None


class OrderItemPublic(BaseModel):
    order_item_id: int
    book_id: int | None
    title: str
    authors: str
    unit_price_cents: int
    quantity: int
    total_price_cents: int


class OrderPublic(BaseModel):
    order_id: int
    status: OrderStatus
    amount_cents: int
    order_date: datetime
    shipping: ShippingSnapshot
    items: list[OrderItemPublic]


class OrderSummary(BaseModel):
    order_id: int
    status: OrderStatus
    amount_cents: int
    item_count: int
    order_date: datetime


class OrderListParams(InputModel):
    status: OrderStatus | None = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class OrderListResponse(BaseModel):
    items: list[OrderSummary]
    total: int


class AdminOrderSummary(OrderSummary):
    user_id: int
    email: EmailStr


class AdminOrderListResponse(BaseModel):
    items: list[AdminOrderSummary]
    total: int


class AdminStatusPatch(InputModel):
    # 'pending' is deliberately absent: no route leads back to it.
    status: Literal["paid", "shipped", "cancelled"]
