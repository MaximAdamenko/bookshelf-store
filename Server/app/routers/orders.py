from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import Connection

from app.core.db import db_read, db_write
from app.core.deps import CurrentUser
from app.dao import order_dao
from app.schemas.orders import OrderCreate, OrderListParams, OrderListResponse, OrderPublic
from app.services import checkout
from app.services.payments import PaymentError, get_provider

router = APIRouter(prefix="/orders", tags=["orders"])

_not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: OrderCreate,
    user: CurrentUser,
    conn: Annotated[Connection, Depends(db_write)],
):
    try:
        order_id = checkout.place_order(conn, user["user_id"], payload, get_provider())
    except checkout.EmptyCartError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="cart is empty")
    except checkout.UnavailableItemsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="some items in your cart are no longer available")
    except PaymentError:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail="payment was declined")
    return order_dao.get_for_user(conn, order_id, user["user_id"])


@router.get("", response_model=OrderListResponse)
def list_orders(
    params: Annotated[OrderListParams, Query()],
    user: CurrentUser,
    conn: Annotated[Connection, Depends(db_read)],
):
    items, total = order_dao.list_for_user(
        conn, user["user_id"],
        status=params.status, limit=params.limit, offset=params.offset,
    )
    return OrderListResponse(items=items, total=total)


@router.get("/{order_id}", response_model=OrderPublic)
def get_order(
    order_id: int,
    user: CurrentUser,
    conn: Annotated[Connection, Depends(db_read)],
):
    order = order_dao.get_for_user(conn, order_id, user["user_id"])
    if order is None:
        raise _not_found  # someone else's order is indistinguishable from none (1.3)
    return order
