import logging

from psycopg import Connection

from app.dao import book_dao, cart_dao, order_dao
from app.schemas.orders import OrderCreate
from app.services.payments import PaymentProvider

log = logging.getLogger(__name__)


class EmptyCartError(ValueError):
    """Nothing to order. Router maps to 409."""


class UnavailableItemsError(ValueError):
    """A line fails the post-lock stock/active check. Router maps to 409;
    GET /cart shows the client which lines."""


def place_order(conn: Connection, user_id: int, shipping: OrderCreate,
                provider: PaymentProvider) -> int:
    cart = cart_dao.list_items(conn, user_id)
    if not cart:
        raise EmptyCartError()

    locked = {b["book_id"]: b
              for b in book_dao.lock_books(conn, [l["book_id"] for l in cart])}
    # Availability is re-checked against the locked rows: the cart's
    # is_available flags were computed before the locks and are advisory.
    for line in cart:
        book = locked.get(line["book_id"])
        if book is None or not book["is_active"] or line["quantity"] > book["quantity"]:
            raise UnavailableItemsError()

    amount_cents = sum(locked[l["book_id"]]["price_cents"] * l["quantity"] for l in cart)
    order_id = order_dao.create(conn, user_id, amount_cents, shipping.model_dump())

    authors = book_dao.author_names(conn, [l["book_id"] for l in cart])
    order_dao.add_items(conn, order_id, [
        {"book_id": l["book_id"],
         "title": locked[l["book_id"]]["title"],
         "authors": authors.get(l["book_id"], ""),
         "unit_price_cents": locked[l["book_id"]]["price_cents"],
         "quantity": l["quantity"]}
        for l in cart
    ])
    book_dao.decrement_stock(conn, [(l["book_id"], l["quantity"]) for l in cart])

    # Local call for the mock. A real provider must not run inside a
    # transaction holding row locks — it arrives with its own intent+webhook
    # flow behind this same interface (DESIGN §8).
    ref = provider.charge(user_id=user_id, order_id=order_id, amount_cents=amount_cents)
    order_dao.mark_paid(conn, order_id)
    log.info("order %d placed by user %d, amount %d, payment %s",
             order_id, user_id, amount_cents, ref)

    cart_dao.clear_items(conn, user_id, [l["cart_item_id"] for l in cart])
    return order_id
