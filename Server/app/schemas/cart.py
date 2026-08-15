from pydantic import BaseModel, Field

from app.schemas.auth import InputModel

# Mirrors CHECK (quantity > 0 AND quantity <= 99) in schema.sql.
MAX_LINE_QUANTITY = 99


class CartItemAdd(InputModel):
    book_id: int = Field(ge=1)
    quantity: int = Field(1, ge=1, le=MAX_LINE_QUANTITY)


class CartItemUpdate(InputModel):
    quantity: int = Field(ge=1, le=MAX_LINE_QUANTITY)


class CartLine(BaseModel):
    cart_item_id: int
    book_id: int
    title: str
    cover_path: str | None
    unit_price_cents: int
    quantity: int
    line_total_cents: int
    stock_remaining: int
    is_available: bool


class CartResponse(BaseModel):
    items: list[CartLine]
    item_count: int
    subtotal_cents: int
    has_unavailable_lines: bool
