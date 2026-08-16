from psycopg import Connection

from app.schemas.books import BookCreate, BookSearchParams


class UnknownIdError(ValueError):
    """A referenced author/category/publisher id does not exist. Router maps to 422."""

    def __init__(self, field: str):
        self.field = field
        super().__init__(f"unknown id in {field}")


# Server-owned constants, no user input. The one allowed f-string. (SECURITY.md 2)
_AUTHORS_JSON = """
    (SELECT COALESCE(json_agg(json_build_object(
                'author_id', a.author_id,
                'name', a.first_name || ' ' || a.last_name)
            ORDER BY a.author_id), '[]')
       FROM book_author ba JOIN authors a USING (author_id)
      WHERE ba.book_id = b.book_id) AS authors"""

_CATEGORIES_JSON = """
    (SELECT COALESCE(json_agg(json_build_object(
                'category_id', c.category_id, 'name', c.name)
            ORDER BY c.category_id), '[]')
       FROM book_category bc JOIN categories c USING (category_id)
      WHERE bc.book_id = b.book_id) AS categories"""

_BOOK_COLS = """b.book_id, b.title, b.description, b.price_cents, b.quantity,
                b.cover_path, b.is_active, b.created_at, b.updated_at,
                b.publisher_id, p.name AS publisher"""

# The user's input selects a key; it never supplies a fragment. (SECURITY.md 2.3)
_SORTS = {
    "newest":     "b.created_at DESC, b.book_id DESC",
    "price_asc":  "b.price_cents ASC,  b.book_id ASC",
    "price_desc": "b.price_cents DESC, b.book_id DESC",
    "relevance":  "rank DESC, b.book_id DESC",
}
_DEFAULT_SORT = "newest"

_FILTERS = {
    "q":               "(b.search_vector @@ websearch_to_tsquery('english', %s)"
                       " OR b.title ILIKE %s"
                       " OR EXISTS (SELECT 1 FROM book_author ba"
                       "            JOIN authors a USING (author_id)"
                       "            WHERE ba.book_id = b.book_id"
                       "              AND a.first_name || ' ' || a.last_name ILIKE %s))",
    "category_id":     "EXISTS (SELECT 1 FROM book_category bc "
                       "WHERE bc.book_id = b.book_id AND bc.category_id = %s)",
    "author_id":       "EXISTS (SELECT 1 FROM book_author ba "
                       "WHERE ba.book_id = b.book_id AND ba.author_id = %s)",
    "publisher_id":    "b.publisher_id = %s",
    "min_price_cents": "b.price_cents >= %s",
    "max_price_cents": "b.price_cents <= %s",
}


def _ilike_pattern(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _where(p: BookSearchParams, *, include_inactive: bool) -> tuple[str, list]:
    where, args = [], []
    if not include_inactive:
        where.append("b.is_active")
    if p.in_stock:
        where.append("b.quantity > 0")
    for field, sql in _FILTERS.items():
        value = getattr(p, field)
        if value is not None and value != "":
            where.append(sql)
            if field == "q":
                args.extend([value, _ilike_pattern(value), _ilike_pattern(value)])
            else:
                args.append(value)
    return " AND ".join(where) or "TRUE", args


def search(
    conn: Connection, params: BookSearchParams, *, include_inactive: bool = False
) -> tuple[list[dict], int]:
    where_sql, args = _where(params, include_inactive=include_inactive)

    sort = params.sort if (params.q or params.sort != "relevance") else _DEFAULT_SORT
    order_by = _SORTS[sort]
    rank_sql = (", ts_rank(b.search_vector, websearch_to_tsquery('english', %s)) AS rank"
                if params.q else "")

    query = f"""
        SELECT {_BOOK_COLS}{rank_sql}, {_AUTHORS_JSON}, {_CATEGORIES_JSON},
               COUNT(*) OVER () AS total
          FROM books b
          LEFT JOIN publishers p USING (publisher_id)
         WHERE {where_sql}
         ORDER BY {order_by}
         LIMIT %s OFFSET %s"""

    with conn.cursor() as cur:
        cur.execute(query, (*([params.q] if params.q else []), *args,
                            params.limit, params.offset))
        rows = cur.fetchall()

    total = rows[0]["total"] if rows else 0
    for row in rows:
        row.pop("total", None)
        row.pop("rank", None)
    return rows, total


def get_by_id(conn: Connection, book_id: int, *, include_inactive: bool = False) -> dict | None:
    active_sql = "" if include_inactive else " AND b.is_active"
    with conn.cursor() as cur:
        cur.execute(
            f"""SELECT {_BOOK_COLS}, {_AUTHORS_JSON}, {_CATEGORIES_JSON}
                  FROM books b
                  LEFT JOIN publishers p USING (publisher_id)
                 WHERE b.book_id = %s{active_sql}""",
            (book_id,),
        )
        return cur.fetchone()


def _check_ids(conn: Connection, table: str, id_col: str, ids: list[int], field: str) -> list[int]:
    ids = sorted(set(ids))
    if not ids:
        return ids
    assert table in {"authors", "categories", "publishers"}  # server-owned constants
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {id_col} = ANY(%s)", (ids,))
        if cur.fetchone()["n"] != len(ids):
            raise UnknownIdError(field)
    return ids


def _validate_refs(conn: Connection, changes: dict) -> dict:
    checks = {"author_ids":   ("authors", "author_id"),
              "category_ids": ("categories", "category_id")}
    for field, (table, col) in checks.items():
        if changes.get(field) is not None:
            changes[field] = _check_ids(conn, table, col, changes[field], field)
    if changes.get("publisher_id") is not None:
        _check_ids(conn, "publishers", "publisher_id", [changes["publisher_id"]], "publisher_id")
    return changes


def _replace_links(conn: Connection, book_id: int, *,
                   author_ids: list[int] | None, category_ids: list[int] | None) -> None:
    with conn.cursor() as cur:
        if author_ids is not None:
            cur.execute("DELETE FROM book_author WHERE book_id = %s", (book_id,))
            cur.executemany(
                "INSERT INTO book_author (book_id, author_id) VALUES (%s, %s)",
                [(book_id, a) for a in author_ids],
            )
        if category_ids is not None:
            cur.execute("DELETE FROM book_category WHERE book_id = %s", (book_id,))
            cur.executemany(
                "INSERT INTO book_category (book_id, category_id) VALUES (%s, %s)",
                [(book_id, c) for c in category_ids],
            )


def create(conn: Connection, data: BookCreate) -> dict:
    refs = _validate_refs(
        conn, data.model_dump(include={"author_ids", "category_ids", "publisher_id"})
    )
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO books (title, description, price_cents, quantity, publisher_id)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING book_id""",
            (data.title, data.description, data.price_cents, data.quantity,
             data.publisher_id),
        )
        book_id = cur.fetchone()["book_id"]

    _replace_links(conn, book_id,
                   author_ids=refs["author_ids"], category_ids=refs["category_ids"])
    return get_by_id(conn, book_id, include_inactive=True)


# Column names come from this literal set, never from the caller's keys. (SECURITY.md 3)
_PATCHABLE = frozenset(
    {"title", "description", "price_cents", "quantity", "publisher_id", "is_active"}
)


def patch(conn: Connection, book_id: int, changes: dict) -> dict | None:
    """`changes` is model_dump(exclude_unset=True) from a forbid-extra schema."""
    changes = _validate_refs(conn, dict(changes))
    cols = {k: v for k, v in changes.items() if k in _PATCHABLE}

    set_sql = "".join(f"{c} = %s, " for c in cols)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE books SET {set_sql}updated_at = now() "
            "WHERE book_id = %s RETURNING book_id",
            (*cols.values(), book_id),
        )
        if cur.fetchone() is None:
            return None

    _replace_links(conn, book_id,
                   author_ids=changes.get("author_ids"),
                   category_ids=changes.get("category_ids"))
    return get_by_id(conn, book_id, include_inactive=True)


def soft_delete(conn: Connection, book_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE books SET is_active = FALSE, updated_at = now() "
            "WHERE book_id = %s AND is_active RETURNING book_id",
            (book_id,),
        )
        return cur.fetchone() is not None


def hard_delete(conn: Connection, book_id: int) -> tuple[bool, str | None]:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM books WHERE book_id = %s RETURNING cover_path",
            (book_id,),
        )
        row = cur.fetchone()
        return (row is not None, row["cover_path"] if row else None)


def set_cover(conn: Connection, book_id: int, cover_path: str) -> str | None:
    """Returns the previous cover_path so the caller can delete the orphaned file."""
    with conn.cursor() as cur:
        cur.execute("SELECT cover_path FROM books WHERE book_id = %s FOR UPDATE", (book_id,))
        row = cur.fetchone()
        if row is None:
            raise UnknownIdError("book_id")
        cur.execute(
            "UPDATE books SET cover_path = %s, updated_at = now() WHERE book_id = %s",
            (cover_path, book_id),
        )
        return row["cover_path"]


def lock_books(conn: Connection, book_ids: list[int]) -> list[dict]:
    # ORDER BY makes the lock acquisition order canonical: two concurrent
    # checkouts can't deadlock by locking the same rows in opposite order.
    with conn.cursor() as cur:
        cur.execute(
            """SELECT book_id, title, price_cents, quantity, is_active
                 FROM books WHERE book_id = ANY(%s)
                ORDER BY book_id
                  FOR UPDATE""",
            (sorted(set(book_ids)),),
        )
        return cur.fetchall()


def author_names(conn: Connection, book_ids: list[int]) -> dict[int, str]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT ba.book_id,
                      string_agg(a.first_name || ' ' || a.last_name, ', '
                                 ORDER BY a.author_id) AS names
                 FROM book_author ba JOIN authors a USING (author_id)
                WHERE ba.book_id = ANY(%s)
                GROUP BY ba.book_id""",
            (book_ids,),
        )
        return {r["book_id"]: r["names"] for r in cur.fetchall()}


def decrement_stock(conn: Connection, amounts: list[tuple[int, int]]) -> None:
    """(book_id, quantity) pairs; rows already held by lock_books.
    CHECK (quantity >= 0) is the backstop if a caller ever forgets."""
    with conn.cursor() as cur:
        cur.executemany(
            "UPDATE books SET quantity = quantity - %s WHERE book_id = %s",
            [(qty, book_id) for book_id, qty in amounts],
        )


def restock_order(conn: Connection, order_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT book_id, quantity FROM order_items
                WHERE order_id = %s AND book_id IS NOT NULL""",
            (order_id,),
        )
        rows = cur.fetchall()
    if not rows:
        return
    # Same canonical lock order as checkout, so cancel and a concurrent
    # checkout can't deadlock.
    lock_books(conn, [r["book_id"] for r in rows])
    with conn.cursor() as cur:
        cur.executemany(
            "UPDATE books SET quantity = quantity + %s WHERE book_id = %s",
            [(r["quantity"], r["book_id"]) for r in rows],
        )


def list_categories(conn: Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT category_id, name FROM categories ORDER BY name")
        return cur.fetchall()


def list_authors(conn: Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT author_id, first_name || ' ' || last_name AS name "
            "FROM authors ORDER BY last_name, first_name"
        )
        return cur.fetchall()


def create_author(conn: Connection, *, first_name: str, last_name: str) -> tuple[dict, bool]:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO authors (first_name, last_name) VALUES (%s, %s) "
            "ON CONFLICT (first_name, last_name) DO NOTHING "
            "RETURNING author_id, first_name || ' ' || last_name AS name",
            (first_name, last_name),
        )
        row = cur.fetchone()
        if row is not None:
            return row, True
        cur.execute(
            "SELECT author_id, first_name || ' ' || last_name AS name "
            "FROM authors WHERE first_name = %s AND last_name = %s",
            (first_name, last_name),
        )
        return cur.fetchone(), False


def list_publishers(conn: Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT publisher_id, name FROM publishers ORDER BY name")
        return cur.fetchall()
