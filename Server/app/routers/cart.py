from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from app.core.db import db_read, db_write
from app.core.deps import CurrentUser
from app.dao import cart_dao
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse

router = APIRouter(prefix="/cart", tags=["cart"])

_not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _conflict(e: cart_dao.LineLimitError) -> HTTPException:
    detail = f"only {e.available} available" if e.available else "no longer available"
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _cart(conn: Connection, user_id: int) -> CartResponse:
    items = cart_dao.list_items(conn, user_id)
    return CartResponse(
        items=items,
        item_count=sum(i["quantity"] for i in items),
        # Unavailable lines are excluded: the subtotal must match what checkout
        # would actually charge.
        subtotal_cents=sum(i["line_total_cents"] for i in items if i["is_available"]),
        has_unavailable_lines=any(not i["is_available"] for i in items),
    )


@router.get("", response_model=CartResponse)
def get_cart(user: CurrentUser, conn: Annotated[Connection, Depends(db_read)]):
    return _cart(conn, user["user_id"])


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartItemAdd,
    user: CurrentUser,
    conn: Annotated[Connection, Depends(db_write)],
):
    try:
        cart_dao.add_item(conn, user["user_id"], payload.book_id, payload.quantity)
    except cart_dao.UnknownBookError:
        raise _not_found
    except cart_dao.LineLimitError as e:
        raise _conflict(e)
    return _cart(conn, user["user_id"])


@router.patch("/items/{cart_item_id}", response_model=CartResponse)
def update_cart_item(
    cart_item_id: int,
    payload: CartItemUpdate,
    user: CurrentUser,
    conn: Annotated[Connection, Depends(db_write)],
):
    try:
        found = cart_dao.update_quantity(
            conn, user["user_id"], cart_item_id, payload.quantity
        )
    except cart_dao.LineLimitError as e:
        raise _conflict(e)
    if not found:
        raise _not_found
    return _cart(conn, user["user_id"])


@router.delete("/items/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(
    cart_item_id: int,
    user: CurrentUser,
    conn: Annotated[Connection, Depends(db_write)],
):
    if not cart_dao.remove_item(conn, user["user_id"], cart_item_id):
        raise _not_found
