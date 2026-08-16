import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

SERVER_DIR = Path(__file__).resolve().parents[1]

# Every row this suite creates is marked with this prefix, and only marked rows are
# ever deleted. Nothing here resets schema or truncates, so the suite is safe to run
# against the development database and safe to re-run.
MARKER = "pytest-bookshelf"


def _load_dotenv() -> dict[str, str]:
    values: dict[str, str] = {}
    env_file = SERVER_DIR / ".env"
    if not env_file.exists():
        return values
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


_dotenv = _load_dotenv()

# Point the app at a dedicated test branch when one is configured. Without it the
# suite falls back to the development database, which the marker discipline above
# makes safe.
for _target, _source in (
    ("DATABASE_URL", "TEST_DATABASE_URL"),
    ("APP_DATABASE_URL", "TEST_APP_DATABASE_URL"),
):
    _override = os.environ.get(_source) or _dotenv.get(_source, "")
    if _override:
        os.environ[_target] = _override

if (os.environ.get("ENV") or _dotenv.get("ENV", "dev")) == "production":
    raise RuntimeError("refusing to run the test suite against ENV=production")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.security import create_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402


def _purge(conn) -> None:
    like = f"{MARKER}%"
    users = "SELECT user_id FROM users WHERE email LIKE %s"
    books = "SELECT book_id FROM books WHERE title LIKE %s"
    with conn.cursor() as cur:
        # Covers first: deleting the book row would strand the file on disk, and the
        # upload tests write a new one on every run.
        cur.execute(
            "SELECT cover_path FROM books WHERE title LIKE %s AND cover_path IS NOT NULL",
            (like,),
        )
        upload_dir = get_settings().upload_path
        for row in cur.fetchall():
            (upload_dir / row["cover_path"]).unlink(missing_ok=True)

        cur.execute(f"DELETE FROM cart_items WHERE user_id IN ({users})", (like,))
        cur.execute(
            f"DELETE FROM order_items WHERE order_id IN "
            f"(SELECT order_id FROM orders WHERE user_id IN ({users}))",
            (like,),
        )
        cur.execute(f"DELETE FROM orders WHERE user_id IN ({users})", (like,))
        cur.execute(f"DELETE FROM email_tokens WHERE user_id IN ({users})", (like,))
        cur.execute(f"DELETE FROM addresses WHERE user_id IN ({users})", (like,))
        cur.execute("DELETE FROM users WHERE email LIKE %s", (like,))

        cur.execute(f"DELETE FROM cart_items WHERE book_id IN ({books})", (like,))
        cur.execute(f"DELETE FROM book_author WHERE book_id IN ({books})", (like,))
        cur.execute(f"DELETE FROM book_category WHERE book_id IN ({books})", (like,))
        cur.execute("DELETE FROM books WHERE title LIKE %s", (like,))
        cur.execute("DELETE FROM authors WHERE first_name LIKE %s", (like,))


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def db(settings):
    with psycopg.connect(
        settings.database_url, row_factory=dict_row, autocommit=True
    ) as conn:
        _purge(conn)
        yield conn
        _purge(conn)


@pytest.fixture(scope="session")
def client(db):
    with TestClient(app) as test_client:
        yield test_client


SHIPPING = {
    "first_name": "Test",
    "last_name": "User",
    "street": "1 Test Way",
    "city": "Testville",
    "postal_code": "12345",
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(db):
    def _make(role: str = "customer", password: str = "TestPassword12345"):
        email = f"{MARKER}-{uuid.uuid4().hex[:12]}@example.com"
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash, first_name, last_name, role,"
                " email_verified) VALUES (%s, %s, 'Test', 'User', %s, true)"
                " RETURNING user_id, email, role",
                (email, hash_password(password), role),
            )
            user = cur.fetchone()
        user["password"] = password
        user["token"] = create_token(
            user_id=user["user_id"], role=role, typ="access", minutes=30
        )
        user["challenge"] = create_token(
            user_id=user["user_id"], role=role, typ="challenge", minutes=30
        )
        user["auth"] = _auth(user["token"])
        return user

    return _make


@pytest.fixture
def customer(make_user):
    return make_user("customer")


@pytest.fixture
def other_customer(make_user):
    return make_user("customer")


@pytest.fixture
def admin(make_user):
    return make_user("admin")


@pytest.fixture
def make_book(db):
    def _make(price_cents: int = 1999, quantity: int = 5, is_active: bool = True):
        title = f"{MARKER} {uuid.uuid4().hex[:12]}"
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO books (title, description, price_cents, quantity, is_active)"
                " VALUES (%s, 'test fixture', %s, %s, %s)"
                " RETURNING book_id, title, price_cents, quantity, is_active",
                (title, price_cents, quantity, is_active),
            )
            book = cur.fetchone()
            cur.execute(
                "INSERT INTO book_author (book_id, author_id)"
                " SELECT %s, author_id FROM authors ORDER BY author_id LIMIT 1",
                (book["book_id"],),
            )
            cur.execute(
                "INSERT INTO book_category (book_id, category_id)"
                " SELECT %s, category_id FROM categories ORDER BY category_id LIMIT 1",
                (book["book_id"],),
            )
        return book

    return _make


@pytest.fixture
def book(make_book):
    return make_book()
