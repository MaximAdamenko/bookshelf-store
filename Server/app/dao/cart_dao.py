from psycopg import Connection

from app.schemas.cart import MAX_LINE_QUANTITY


class UnknownBookError(ValueError):
    """No such book, or it is soft-deleted. Router maps to 404."""


class LineLimitError(ValueError):
    """The line cannot hold the requested quantity. Router maps to 409."""

    def __init__(self, available: int):
        self.available = available
        super().__init__(f"only {available} available")


_LINE_COLS = """c.cart_item_id, c.book_id, c.quantity,
                b.title, b.cover_path,
                b.price_cents AS unit_price_cents,
                b.price_cents * c.quantity AS line_total_cents,
                b.quantity AS stock_remaining,
                (b.is_active AND b.quantity >= c.quantity) AS is_available"""


def list_items(conn: Connection, user_id: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            f"""SELECT {_LINE_COLS}
                  FROM cart_items c JOIN books b USING (book_id)
                 WHERE c.user_id = %s
                 ORDER BY c.added_at DESC, c.cart_item_id DESC""",
            (user_id,),
        )
        return cur.fetchall()


def add_item(conn: Connection, user_id: int, book_id: int, quantity: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT quantity FROM books WHERE book_id = %s AND is_active",
            (book_id,),
        )
        book = cur.fetchone()
        if book is None:
            raise UnknownBookError()

        cap = min(book["quantity"], MAX_LINE_QUANTITY)
        if quantity > cap:
            raise LineLimitError(cap)

        # The cap lives in the ON CONFLICT guard, not in a read-then-write in
        # Python: two concurrent adds from the same session can't both pass a
        # check and then both apply. No matching row means the guard refused.
        cur.execute(
            """INSERT INTO cart_items (user_id, book_id, quantity)
                    VALUES (%s, %s, %s)
               ON CONFLICT (user_id, book_id) DO UPDATE
                    SET quantity = cart_items.quantity + EXCLUDED.quantity
                  WHERE cart_items.quantity + EXCLUDED.quantity <= %s
               RETURNING cart_item_id""",
            (user_id, book_id, quantity, cap),
        )
        if cur.fetchone() is None:
            raise LineLimitError(cap)


def update_quantity(
    conn: Connection, user_id: int, cart_item_id: int, quantity: int
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT b.quantity AS stock, b.is_active
                 FROM cart_items c JOIN books b USING (book_id)
                WHERE c.cart_item_id = %s AND c.user_id = %s""",
            (cart_item_id, user_id),
        )
        row = cur.fetchone()
        if row is None:
            return False
        if not row["is_active"]:
            raise LineLimitError(0)

        cap = min(row["stock"], MAX_LINE_QUANTITY)
        if quantity > cap:
            raise LineLimitError(cap)

        # user_id repeats here even though the SELECT above already matched it:
        # ownership belongs in the mutating statement. (SECURITY.md 1.6)
        cur.execute(
            """UPDATE cart_items SET quantity = %s
                WHERE cart_item_id = %s AND user_id = %s
            RETURNING cart_item_id""",
            (quantity, cart_item_id, user_id),
        )
        return cur.fetchone() is not None


def remove_item(conn: Connection, user_id: int, cart_item_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """DELETE FROM cart_items
                WHERE cart_item_id = %s AND user_id = %s
            RETURNING cart_item_id""",
            (cart_item_id, user_id),
        )
        return cur.fetchone() is not None


def clear_items(conn: Connection, user_id: int, cart_item_ids: list[int]) -> None:
    # Only the charged lines: a line added from another tab mid-checkout
    # survives.
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM cart_items WHERE user_id = %s AND cart_item_id = ANY(%s)",
            (user_id, cart_item_ids),
        )
