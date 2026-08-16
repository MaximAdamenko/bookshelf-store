"""SECURITY.md 2 — SQL injection."""

import pytest

PAYLOADS = [
    "' OR 1=1--",
    "'; DROP TABLE books;--",
    "%' UNION SELECT password_hash FROM users--",
    "1' OR '1'='1",
    "\\'; DELETE FROM users WHERE 't'='t",
    "' OR ''='",
    "'||(SELECT password_hash FROM users LIMIT 1)||'",
]


def _tables_intact(db) -> None:
    with db.cursor() as cur:
        for table in ("users", "books", "orders", "cart_items", "authors"):
            cur.execute(f"SELECT count(*) AS n FROM {table}")  # server-controlled name
            assert cur.fetchone()["n"] >= 0


@pytest.mark.parametrize("payload", PAYLOADS)
def test_search_query_is_data_not_code(client, db, payload):
    response = client.get("/books", params={"q": payload})
    assert response.status_code == 200
    body = response.json()
    # No password hash may ever appear in a catalog response.
    assert "$argon2" not in response.text
    assert isinstance(body["items"], list)
    _tables_intact(db)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_sort_is_whitelisted_not_interpolated(client, db, payload):
    response = client.get("/books", params={"sort": payload})
    assert response.status_code == 422
    _tables_intact(db)


@pytest.mark.parametrize("field", ["category_id", "author_id", "publisher_id", "min_price_cents"])
def test_numeric_filters_reject_injection(client, db, field):
    response = client.get("/books", params={field: "1 OR 1=1"})
    assert response.status_code == 422
    _tables_intact(db)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_path_ids_reject_injection(client, db, payload):
    assert client.get(f"/books/{payload}").status_code == 422
    _tables_intact(db)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_login_email_rejects_injection(client, db, payload):
    response = client.post("/auth/login", json={"email": payload, "password": "x" * 16})
    # Not a valid email address, so it never reaches the query at all.
    assert response.status_code in (401, 422, 429)
    assert "$argon2" not in response.text
    _tables_intact(db)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_reset_token_rejects_injection(client, db, payload):
    response = client.post(
        "/auth/reset", json={"token": payload, "new_password": "ReplacementPass123"}
    )
    assert response.status_code in (400, 422, 429)
    _tables_intact(db)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_cart_fields_reject_injection(client, db, customer, payload):
    response = client.post(
        "/cart/items", json={"book_id": payload, "quantity": 1}, headers=customer["auth"]
    )
    assert response.status_code == 422
    response = client.post(
        "/cart/items", json={"book_id": 1, "quantity": payload}, headers=customer["auth"]
    )
    assert response.status_code == 422
    _tables_intact(db)


def test_injection_in_author_name_is_stored_literally(client, db, admin):
    hostile = "Robert'); DROP TABLE books;--"
    response = client.post(
        "/admin/authors",
        json={"first_name": "pytest-bookshelf", "last_name": hostile},
        headers=admin["auth"],
    )
    assert response.status_code in (200, 201)
    assert response.json()["name"].endswith(hostile)
    _tables_intact(db)


def test_search_still_finds_a_real_book(client, book):
    """A control: the injection tests above must not pass merely because search is broken."""
    response = client.get("/books", params={"q": book["title"]})
    assert response.status_code == 200
    assert any(item["book_id"] == book["book_id"] for item in response.json()["items"])
