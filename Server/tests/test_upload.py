"""SECURITY.md 4 — malicious file upload."""

import io
import zlib

import pytest
from PIL import Image


def _png(size=(40, 60)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (120, 90, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(client, admin, book, name, data, content_type="image/png"):
    return client.post(
        f"/admin/books/{book['book_id']}/cover",
        files={"file": (name, data, content_type)},
        headers=admin["auth"],
    )


def test_a_real_image_is_accepted_and_renamed(client, admin, book):
    response = _upload(client, admin, book, "my holiday photo.png", _png())
    assert response.status_code == 200, response.text
    cover = response.json()["cover_path"]
    # The client filename is discarded, never sanitized. (SECURITY.md 4.4)
    assert "holiday" not in cover
    import re

    assert re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp)", cover), cover
    assert client.get(f"/media/covers/{cover}").status_code == 200


def test_php_payload_renamed_as_image_is_rejected(client, admin, book):
    payload = b"<?php system($_GET['c']); ?>"
    assert _upload(client, admin, book, "shell.php.png", payload).status_code == 422


def test_svg_with_script_is_rejected(client, admin, book):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert _upload(client, admin, book, "x.svg", svg, "image/svg+xml").status_code == 422
    # ... and renaming it does not help
    assert _upload(client, admin, book, "x.png", svg).status_code == 422


def test_traversal_filename_cannot_escape(client, admin, book):
    response = _upload(client, admin, book, "../../../../etc/passwd.png", _png())
    assert response.status_code == 200
    assert "/" not in response.json()["cover_path"]
    assert ".." not in response.json()["cover_path"]


def test_oversized_upload_is_refused(client, admin, book):
    huge = b"\x89PNG\r\n\x1a\n" + b"\x00" * (3 * 1024 * 1024)
    assert _upload(client, admin, book, "huge.png", huge).status_code == 413


def test_polyglot_image_with_appended_payload_is_reencoded(client, admin, book):
    """A valid PNG with a ZIP glued on: stored, but re-encoded so the payload is gone."""
    poly = _png() + b"PK\x03\x04" + zlib.compress(b"<?php echo 'pwned'; ?>" * 20)
    response = _upload(client, admin, book, "poly.png", poly)
    assert response.status_code == 200

    from app.core.config import get_settings

    stored = (get_settings().upload_path / response.json()["cover_path"]).read_bytes()
    assert b"PK\x03\x04" not in stored, "appended archive survived re-encoding"
    assert b"<?php" not in stored


@pytest.mark.parametrize(
    "name", ["../../.env", "..%2f..%2f.env", "%2e%2e%2f.env", "not-a-uuid.png", "abc.txt"]
)
def test_media_route_rejects_anything_but_a_uuid_name(client, name):
    assert client.get(f"/media/covers/{name}").status_code in (400, 404)


def test_media_route_pins_content_type_and_nosniff(client, admin, book):
    cover = _upload(client, admin, book, "ok.png", _png()).json()["cover_path"]
    response = client.get(f"/media/covers/{cover}")
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_customer_cannot_upload_anything(client, customer, book):
    response = client.post(
        f"/admin/books/{book['book_id']}/cover",
        files={"file": ("x.png", _png(), "image/png")},
        headers=customer["auth"],
    )
    assert response.status_code == 404
