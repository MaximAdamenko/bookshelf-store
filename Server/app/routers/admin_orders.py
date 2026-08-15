import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import Connection

from app.core.db import db_read, db_write
from app.core.deps import require_admin
from app.dao import book_dao, order_dao
from app.schemas.orders import (
    AdminOrderListResponse,
    AdminOrderSummary,
    AdminStatusPatch,
    OrderListParams,
)

log = logging.getLogger(__name__)

# Guard on the router, not per-endpoint. (SECURITY.md 1.5)
router = APIRouter(
    prefix="/admin/orders",
    tags=["admin:orders"],
    dependencies=[Depends(require_admin)],
)

_not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

# The client's input selects a target status; what it may move FROM is
# server-owned. (Same whitelist shape as the sort map — SECURITY.md 2.3)
_ALLOWED_FROM = {
    "paid": ("pending",),
    "shipped": ("paid",),
    "cancelled": ("pending", "paid"),
}


@router.get("", response_model=AdminOrderListResponse)
def list_orders_admin(
    params: Annotated[OrderListParams, Query()],
    conn: Annotated[Connection, Depends(db_read)],
):
    items, total = order_dao.list_all(
        conn, status=params.status, limit=params.limit, offset=params.offset
    )
    return AdminOrderListResponse(items=items, total=total)


@router.patch("/{order_id}/status", response_model=AdminOrderSummary)
def set_order_status(
    order_id: int,
    payload: AdminStatusPatch,
    conn: Annotated[Connection, Depends(db_write)],
):
    changed = order_dao.update_status(
        conn, order_id, payload.status, _ALLOWED_FROM[payload.status]
    )
    if not changed:
        row = order_dao.admin_row(conn, order_id)
        if row is None:
            raise _not_found
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"cannot move a {row['status']} order to {payload.status}",
        )
    if payload.status == "cancelled":
        book_dao.restock_order(conn, order_id)  # cancelled is terminal: runs once
    log.info("order %d status -> %s", order_id, payload.status)
    return order_dao.admin_row(conn, order_id)
