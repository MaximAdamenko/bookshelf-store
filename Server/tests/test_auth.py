"""SECURITY.md 5 — authentication."""

import time
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import create_token
from tests.conftest import MARKER


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_password_is_argon2id_and_never_returned(client, customer, db):
    with db.cursor() as cur:
        cur.execute(
            "SELECT password_hash FROM users WHERE user_id = %s", (customer["user_id"],)
        )
        stored = cur.fetchone()["password_hash"]
    assert stored.startswith("$argon2id$")
    assert customer["password"] not in stored

    me = client.get("/auth/me", headers=customer["auth"])
    assert me.status_code == 200
    assert "password" not in me.text
    assert "argon2" not in me.text


def test_alg_none_token_is_rejected(client, customer):
    forged = jwt.encode(
        {"sub": str(customer["user_id"]), "role": "admin", "typ": "access",
         "iat": int(time.time()), "exp": int(time.time()) + 600},
        key="",
        algorithm="none",
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_token_signed_with_the_wrong_key_is_rejected(client, customer):
    forged = jwt.encode(
        {"sub": str(customer["user_id"]), "role": "admin", "typ": "access",
         "iat": int(time.time()), "exp": int(time.time()) + 600},
        key="an-attacker-controlled-key-of-sufficient-length",
        algorithm="HS256",
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_expired_token_is_rejected(client, customer):
    expired = create_token(
        user_id=customer["user_id"], role="customer", typ="access", minutes=-1
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_garbage_and_missing_tokens_are_rejected(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not.a.token"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_registration_is_case_insensitive_on_email(client):
    email = f"{MARKER}-{uuid.uuid4().hex[:10]}@example.com"
    body = {"password": "TestPassword12345", "first_name": "Case", "last_name": "Test"}
    assert client.post("/auth/register", json={**body, "email": email}).status_code == 201
    clash = client.post("/auth/register", json={**body, "email": email.upper()})
    assert clash.status_code == 409


def test_short_password_is_refused(client):
    response = client.post(
        "/auth/register",
        json={
            "email": f"{MARKER}-{uuid.uuid4().hex[:10]}@example.com",
            "password": "short",
            "first_name": "Weak",
            "last_name": "Pass",
        },
    )
    assert response.status_code == 422


def test_login_body_is_identical_for_unknown_and_wrong_password(client, customer):
    unknown = _login(client, f"{MARKER}-{uuid.uuid4().hex[:10]}@example.com", "WrongPassword123")
    wrong = _login(client, customer["email"], "WrongPassword123")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_forgot_is_always_202_and_identical(client, customer):
    known = client.post("/auth/forgot", json={"email": customer["email"]})
    unknown = client.post(
        "/auth/forgot", json={"email": f"{MARKER}-{uuid.uuid4().hex[:10]}@example.com"}
    )
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


def test_otp_is_hashed_at_rest_and_single_use(client, customer, db):
    response = _login(client, customer["email"], customer["password"])
    assert response.status_code == 200
    challenge = response.json()["challenge_token"]

    with db.cursor() as cur:
        cur.execute(
            "SELECT token_hash, used_at, attempts FROM email_tokens"
            " WHERE user_id = %s AND purpose = 'login_otp' ORDER BY created_at DESC LIMIT 1",
            (customer["user_id"],),
        )
        row = cur.fetchone()
    assert row is not None
    assert len(row["token_hash"]) == 64          # sha256 hex, not the raw code
    assert row["token_hash"].isalnum()
    assert row["used_at"] is None

    # A wrong code must not authenticate, and must burn an attempt.
    bad = client.post("/auth/login/verify", json={"challenge_token": challenge, "code": "000000"})
    assert bad.status_code == 401
    with db.cursor() as cur:
        cur.execute(
            "SELECT attempts FROM email_tokens WHERE user_id = %s AND purpose = 'login_otp'"
            " ORDER BY created_at DESC LIMIT 1",
            (customer["user_id"],),
        )
        assert cur.fetchone()["attempts"] >= 1


def test_access_token_is_refused_as_a_challenge_token(client, customer):
    response = client.post(
        "/auth/login/verify", json={"challenge_token": customer["token"], "code": "123456"}
    )
    assert response.status_code == 401


def test_lockout_after_repeated_failures(client, make_user, db):
    victim = make_user("customer")
    settings = get_settings()
    for _ in range(settings.max_failed_logins + 1):
        _login(client, victim["email"], "WrongPassword123")

    with db.cursor() as cur:
        cur.execute(
            "SELECT failed_logins, locked_until FROM users WHERE user_id = %s",
            (victim["user_id"],),
        )
        row = cur.fetchone()
    assert row["locked_until"] is not None, "account should be locked"

    # Even the correct password fails while locked.
    assert _login(client, victim["email"], victim["password"]).status_code == 401


@pytest.mark.parametrize("token", ["", "x", "../../etc/passwd", "' OR 1=1--"])
def test_reset_rejects_bad_tokens(client, token):
    response = client.post(
        "/auth/reset", json={"token": token, "new_password": "BrandNewPassword1"}
    )
    assert response.status_code in (400, 422, 429)
