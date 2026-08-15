from psycopg import Connection

_SHIP_FIELDS = ("first_name", "last_name", "street", "city",
                "apartment", "postal_code", "phone")

_SUMMARY_COLS = "o.order_id, o.status, o.amount_cents, o.order_date"

_ITEM_COUNT = """(SELECT COALESCE(SUM(oi.quantity), 0)
                    FROM order_items oi WHERE oi.order_id = o.order_id) AS item_count"""

_ITEM_COLS = """order_item_id, book_id, title_snapshot AS title,
                authors_snapshot AS authors, unit_price_cents, quantity,
                total_price_cents"""


def _nest_shipping(order: dict) -> dict:
    order["shipping"] = {f: order.pop(f"ship_{f}") for f in _SHIP_FIELDS}
    return order


def _fetch_page(conn: Connection, query: str, args: tuple) -> tuple[list[dict], int]:
    with conn.cursor() as cur:
        cur.execute(query, args)
        rows = cur.fetchall()
    total = rows[0]["total"] if rows else 0
    for row in rows:
        row.pop("total")
    return rows, total


def create(conn: Connection, user_id: int, amount_cents: int, shipping: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO orders (user_id, amount_cents, ship_first_name,
                                   ship_last_name, ship_street, ship_city,
                                   ship_apartment, ship_postal_code, ship_phone)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING order_id""",
            (user_id, amount_cents, *[shipping[f] for f in _SHIP_FIELDS]),
        )
        return cur.fetchone()["order_id"]


def add_items(conn: Connection, order_id: int, lines: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO order_items (order_id, book_id, title_snapshot,
                                        authors_snapshot, unit_price_cents, quantity)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(order_id, l["book_id"], l["title"], l["authors"],
              l["unit_price_cents"], l["quantity"]) for l in lines],
        )


def mark_paid(conn: Connection, order_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE orders SET status = 'paid' WHERE order_id = %s AND status = 'pending'",
            (order_id,),
        )


def get_for_user(conn: Connection, order_id: int, user_id: int) -> dict | None:
    # Ownership lives in the WHERE, not in a Python check. (SECURITY.md 1.2)
    with conn.cursor() as cur:
        cur.execute(
            f"""SELECT {_SUMMARY_COLS},
                       o.ship_first_name, o.ship_last_name, o.ship_street,
                       o.ship_city, o.ship_apartment, o.ship_postal_code, o.ship_phone
                  FROM orders o
                 WHERE o.order_id = %s AND o.user_id = %s""",
            (order_id, user_id),
        )
        order = cur.fetchone()
        if order is None:
            return None
        cur.execute(
            f"SELECT {_ITEM_COLS} FROM order_items WHERE order_id = %s ORDER BY order_item_id",
            (order_id,),
        )
        order["items"] = cur.fetchall()
    return _nest_shipping(order)


def list_for_user(conn: Connection, user_id: int, *,
                  status: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
    # Server-owned fragments only; every value is a parameter. (SECURITY.md 2)
    status_sql = "" if status is None else " AND o.status = %s"
    args = (user_id, *([] if status is None else [status]), limit, offset)
    query = f"""
        SELECT {_SUMMARY_COLS}, {_ITEM_COUNT}, COUNT(*) OVER () AS total
          FROM orders o
         WHERE o.user_id = %s{status_sql}
         ORDER BY o.order_date DESC, o.order_id DESC
         LIMIT %s OFFSET %s"""
    return _fetch_page(conn, query, args)


def list_all(conn: Connection, *,
             status: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
    status_sql = "TRUE" if status is None else "o.status = %s"
    args = (*([] if status is None else [status]), limit, offset)
    query = f"""
        SELECT {_SUMMARY_COLS}, o.user_id, u.email, {_ITEM_COUNT},
               COUNT(*) OVER () AS total
          FROM orders o JOIN users u USING (user_id)
         WHERE {status_sql}
         ORDER BY o.order_date DESC, o.order_id DESC
         LIMIT %s OFFSET %s"""
    return _fetch_page(conn, query, args)


def admin_row(conn: Connection, order_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            f"""SELECT {_SUMMARY_COLS}, o.user_id, u.email, {_ITEM_COUNT}
                  FROM orders o JOIN users u USING (user_id)
                 WHERE o.order_id = %s""",
            (order_id,),
        )
        return cur.fetchone()


def update_status(conn: Connection, order_id: int, new_status: str,
                  allowed_from: tuple[str, ...]) -> bool:
    # The transition guard lives in the WHERE, same shape as the cart cap:
    # two concurrent PATCHes can't both pass a Python check and then apply.
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE orders SET status = %s
                WHERE order_id = %s AND status = ANY(%s::order_status[])
            RETURNING order_id""",
            (new_status, order_id, list(allowed_from)),
        )
        return cur.fetchone() is not None
