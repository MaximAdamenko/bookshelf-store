"""SECURITY.md 3 — mass assignment."""

import uuid

import pytest

from tests.conftest import MARKER, SHIPPING


def test_register_cannot_set_role(client, db):
    email = f"{MARKER}-{uuid.uuid4().hex[:12]}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword12345",
            "first_name": "Mass",
            "last_name": "Assign",
            "role": "admin",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"

    with db.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM users WHERE email = %s", (email,))
        assert cur.fetchone()["n"] == 0, "the rejected registration must not have been created"


def test_register_without_role_creates_a_customer(client, db):
    email = f"{MARKER}-{uuid.uuid4().hex[:12]}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword12345",
            "first_name": "Plain",
            "last_name": "Customer",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "customer"


@pytest.mark.parametrize(
    "extra",
    [
        {"book_id": 99},
        {"is_active": True, "created_at": "2020-01-01T00:00:00Z"},
        {"search_vector": "x"},
        {"cover_path": "../../etc/passwd"},
    ],
)
def test_book_patch_rejects_server_owned_fields(client, admin, book, extra):
    response = client.patch(
        f"/admin/books/{book['book_id']}", json={"title": "x", **extra}, headers=admin["auth"]
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "extra", [{"amount_cents": 0}, {"status": "paid"}, {"user_id": 1}, {"order_id": 1}]
)
def test_checkout_rejects_server_owned_fields(client, customer, book, extra):
    client.post(
        "/cart/items",
        json={"book_id": book["book_id"], "quantity": 1},
        headers=customer["auth"],
    )
    response = client.post("/orders", json={**SHIPPING, **extra}, headers=customer["auth"])
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"


def test_order_total_is_computed_from_the_database(client, customer, make_book, db):
    priced = make_book(price_cents=4321, quantity=3)
    client.post(
        "/cart/items",
        json={"book_id": priced["book_id"], "quantity": 2},
        headers=customer["auth"],
    )
    placed = client.post("/orders", json=SHIPPING, headers=customer["auth"])
    assert placed.status_code == 201, placed.text
    assert placed.json()["amount_cents"] == 4321 * 2

    with db.cursor() as cur:
        cur.execute(
            "SELECT amount_cents FROM orders WHERE order_id = %s", (placed.json()["order_id"],)
        )
        assert cur.fetchone()["amount_cents"] == 4321 * 2


def test_cart_add_rejects_price_and_ownership_fields(client, customer, book):
    for extra in ({"price_cents": 1}, {"user_id": 1}, {"cart_item_id": 1}):
        response = client.post(
            "/cart/items",
            json={"book_id": book["book_id"], "quantity": 1, **extra},
            headers=customer["auth"],
        )
        assert response.status_code == 422, extra


def test_author_create_rejects_id(client, admin):
    response = client.post(
        "/admin/authors",
        json={"first_name": "pytest-bookshelf", "last_name": "Ignored", "author_id": 99},
        headers=admin["auth"],
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"


def test_admin_order_status_rejects_pending_and_extras(client, admin, customer, book):
    client.post(
        "/cart/items",
        json={"book_id": book["book_id"], "quantity": 1},
        headers=customer["auth"],
    )
    order_id = client.post("/orders", json=SHIPPING, headers=customer["auth"]).json()["order_id"]

    # 'pending' is not a settable target — the server owns that transition.
    assert (
        client.patch(
            f"/admin/orders/{order_id}/status", json={"status": "pending"}, headers=admin["auth"]
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/admin/orders/{order_id}/status",
            json={"status": "shipped", "amount_cents": 0},
            headers=admin["auth"],
        ).status_code
        == 422
    )
