"""SECURITY.md 6 — race conditions. The oversell test."""

from concurrent.futures import ThreadPoolExecutor

from tests.conftest import SHIPPING


def test_two_buyers_one_copy_exactly_one_wins(client, make_user, make_book, db):
    last_copy = make_book(price_cents=2500, quantity=1)
    buyers = [make_user("customer"), make_user("customer")]

    for buyer in buyers:
        added = client.post(
            "/cart/items",
            json={"book_id": last_copy["book_id"], "quantity": 1},
            headers=buyer["auth"],
        )
        assert added.status_code == 201, added.text

    def place(buyer):
        return client.post("/orders", json=SHIPPING, headers=buyer["auth"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result() for f in [pool.submit(place, b) for b in buyers]]

    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409], f"expected exactly one winner, got {codes}"

    with db.cursor() as cur:
        cur.execute("SELECT quantity FROM books WHERE book_id = %s", (last_copy["book_id"],))
        assert cur.fetchone()["quantity"] == 0, "stock must not go negative or stay at 1"

        cur.execute(
            "SELECT count(*) AS n FROM order_items WHERE book_id = %s", (last_copy["book_id"],)
        )
        assert cur.fetchone()["n"] == 1, "exactly one order line may exist for the last copy"


def test_database_check_constraint_refuses_negative_stock(db, make_book):
    """Defence in depth: even if the application logic were wrong, the DB says no."""
    import psycopg

    book = make_book(quantity=1)
    with db.cursor() as cur:
        try:
            cur.execute(
                "UPDATE books SET quantity = quantity - 5 WHERE book_id = %s",
                (book["book_id"],),
            )
        except psycopg.errors.CheckViolation:
            pass
        else:
            raise AssertionError("CHECK (quantity >= 0) did not fire")
