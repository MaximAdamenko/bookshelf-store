"""SECURITY.md 1 — broken access control."""

from tests.conftest import SHIPPING


def test_customer_cannot_read_another_users_order(client, customer, other_customer, book):
    client.post(
        "/cart/items",
        json={"book_id": book["book_id"], "quantity": 1},
        headers=customer["auth"],
    )
    placed = client.post("/orders", json=SHIPPING, headers=customer["auth"])
    assert placed.status_code == 201, placed.text
    order_id = placed.json()["order_id"]

    # 404 rather than 403: a 403 would confirm the order exists. (SECURITY.md 1.3)
    stolen = client.get(f"/orders/{order_id}", headers=other_customer["auth"])
    assert stolen.status_code == 404
    assert stolen.json() == {"detail": "Not found"}

    assert client.get(f"/orders/{order_id}", headers=customer["auth"]).status_code == 200


def test_customer_cannot_patch_another_users_cart_line(client, customer, other_customer, book):
    added = client.post(
        "/cart/items",
        json={"book_id": book["book_id"], "quantity": 1},
        headers=customer["auth"],
    )
    assert added.status_code == 201, added.text
    line_id = added.json()["items"][0]["cart_item_id"]

    assert (
        client.patch(
            f"/cart/items/{line_id}", json={"quantity": 2}, headers=other_customer["auth"]
        ).status_code
        == 404
    )
    assert client.delete(f"/cart/items/{line_id}", headers=other_customer["auth"]).status_code == 404
    # still the owner's, untouched
    assert client.patch(
        f"/cart/items/{line_id}", json={"quantity": 2}, headers=customer["auth"]
    ).status_code == 200


ADMIN_ROUTES = [
    ("get", "/admin/books"),
    ("get", "/admin/orders"),
    ("post", "/admin/books"),
    ("post", "/admin/authors"),
]


def test_customer_is_refused_every_admin_route(client, customer):
    for method, path in ADMIN_ROUTES:
        response = client.request(method, path, headers=customer["auth"])
        assert response.status_code == 404, f"{method.upper()} {path} -> {response.status_code}"


def test_anonymous_is_refused_every_admin_route(client):
    for method, path in ADMIN_ROUTES:
        response = client.request(method, path)
        assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"


def test_forged_role_header_is_ignored(client, customer):
    response = client.get(
        "/admin/books", headers={**customer["auth"], "X-Role": "admin", "Role": "admin"}
    )
    assert response.status_code == 404


def test_role_comes_from_the_database_not_the_token(client, customer, db):
    """A token minted with role=admin still loses: the role is reloaded per request."""
    from app.core.security import create_token

    forged = create_token(
        user_id=customer["user_id"], role="admin", typ="access", minutes=5
    )
    assert client.get("/admin/books", headers={"Authorization": f"Bearer {forged}"}).status_code == 404


def test_challenge_token_cannot_reach_resources(client, customer):
    for path in ("/cart", "/orders", "/auth/me"):
        response = client.get(path, headers={"Authorization": f"Bearer {customer['challenge']}"})
        assert response.status_code == 401, f"{path} -> {response.status_code}"


def test_inactive_book_hidden_from_public_but_visible_to_admin(client, admin, make_book):
    hidden = make_book(is_active=False)
    assert client.get(f"/books/{hidden['book_id']}").status_code == 404
    visible = client.get(f"/admin/books/{hidden['book_id']}", headers=admin["auth"])
    assert visible.status_code == 200
    assert visible.json()["is_active"] is False
