import logging
import time
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from psycopg import Connection

from app.core.config import get_settings
from app.core.db import db_write, read_connection, transaction
from app.core.deps import CurrentUser
from app.core.ratelimit import rate_limit
from app.core.security import (
    constant_time_equal,
    create_token,
    decode_token,
    hash_otp,
    hash_password,
    hash_reset_token,
    new_otp_code,
    new_reset_token,
    verify_password,
)
from app.dao import token_dao, user_dao
from app.schemas.auth import (
    ChallengeResponse,
    ForgotRequest,
    ForgotResponse,
    LoginRequest,
    ResetRequest,
    ResetResponse,
    TokenResponse,
    UserPublic,
    UserRegister,
    VerifyRequest,
)
from app.services.mailer import send_login_code, send_reset_token

log = logging.getLogger("bookshelf.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

_login_limit = rate_limit(10, 300)
_verify_limit = rate_limit(20, 300)
_forgot_limit = rate_limit(5, 300)
_reset_limit = rate_limit(10, 300)

# Both branches of /forgot are padded to this floor, so "we emailed a token"
# and "we did nothing" take observably the same wall-clock time. Cheaper and
# more robust than trying to match the cost of the DB write and the send.
_FORGOT_FLOOR_SECONDS = 0.3


def _invalid_credentials() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


# Sending happens after the response, never inside it. With MAIL_BACKEND=gmail a
# send is a full SMTP round trip — far larger and more variable than the timing
# floor above, and it only occurs on the branch where the account exists. Left
# inline it would reopen the enumeration gap the floor exists to close.
# (SECURITY.md 5.6)
def _send_login_code_safely(email: str, code: str, user_id: int) -> None:
    try:
        send_login_code(email, code)
    except Exception:
        # Logged, never surfaced. A 503 here would mean "we tried to email you",
        # which tells a prober the account exists.
        log.exception("could not send the login code for user_id=%s", user_id)


def _send_reset_token_safely(email: str, token: str, user_id: int) -> None:
    try:
        send_reset_token(email, token)
    except Exception:
        log.exception("could not send the reset email for user_id=%s", user_id)


def _is_locked(record: dict) -> bool:
    locked_until = record["locked_until"]
    return locked_until is not None and locked_until > datetime.now(UTC)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, conn: Annotated[Connection, Depends(db_write)]):
    user = user_dao.create(
        conn,
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        birth_date=payload.birth_date,
        phone=payload.phone,
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Registration failed")
    return user


@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser):
    return user


@router.post("/login", response_model=ChallengeResponse, dependencies=[Depends(_login_limit)])
def login(payload: LoginRequest, background: BackgroundTasks):
    settings = get_settings()

    with read_connection() as conn:
        record = user_dao.get_auth_record(conn, payload.email)

    # Runs argon2 either way — against a dummy hash when the email is unknown —
    # so an unknown address and a wrong password cost the same. (SECURITY.md 5.6)
    password_ok = verify_password(record["password_hash"] if record else None, payload.password)

    if record is None or not password_ok or not record["is_active"] or _is_locked(record):
        if record is not None and record["is_active"] and not password_ok:
            # Its own transaction, committed before the 401 is raised. Inside the
            # request's transaction the raise would roll the counter back and the
            # lockout would never trigger.
            with transaction() as conn:
                user_dao.register_failed_login(
                    conn, record["user_id"],
                    max_failed=settings.max_failed_logins,
                    lockout_minutes=settings.lockout_minutes,
                )
        else:
            # Matches the round trip above. Both branches answer 401, so an
            # unknown email must cost the same as a known one with a wrong
            # password. (SECURITY.md 5.6)
            with transaction() as conn:
                conn.execute("SELECT 1")
        raise _invalid_credentials()

    code = new_otp_code()
    with transaction() as conn:
        # One live code per user: a second login attempt kills the first code.
        token_dao.invalidate_open(conn, user_id=record["user_id"], purpose="login_otp")
        token_id = token_dao.issue(
            conn,
            user_id=record["user_id"],
            token_hash=hash_otp(record["user_id"], code),
            purpose="login_otp",
            ttl_minutes=settings.otp_ttl_minutes,
        )
        user_dao.clear_failed_logins(conn, record["user_id"])

    background.add_task(_send_login_code_safely, record["email"], code, record["user_id"])

    return ChallengeResponse(
        challenge_token=create_token(
            user_id=record["user_id"], role=record["role"], typ="challenge",
            minutes=settings.challenge_token_minutes, extra={"tid": token_id},
        ),
        expires_in=settings.challenge_token_minutes * 60,
    )


@router.post("/login/verify", response_model=TokenResponse, dependencies=[Depends(_verify_limit)])
def login_verify(payload: VerifyRequest):
    settings = get_settings()

    claims = decode_token(payload.challenge_token, expected_typ="challenge")
    if claims is None:
        raise _invalid_credentials()
    try:
        user_id = int(claims["sub"])
        token_id = int(claims["tid"])
    except (KeyError, TypeError, ValueError):
        raise _invalid_credentials()

    with read_connection() as conn:
        row = token_dao.get_open(conn, token_id=token_id, user_id=user_id, purpose="login_otp")
        user = user_dao.get_by_id(conn, user_id)

    if row is None or user is None or not user["is_active"]:
        raise _invalid_credentials()

    if row["attempts"] >= settings.otp_max_attempts:
        with transaction() as conn:
            token_dao.consume(conn, token_id)
        raise _invalid_credentials()

    if not constant_time_equal(row["token_hash"], hash_otp(user_id, payload.code)):
        with transaction() as conn:
            token_dao.record_attempt(conn, token_id)
        raise _invalid_credentials()

    with transaction() as conn:
        # consume() is conditional on used_at IS NULL, so this is also the
        # single-use check: losing a race returns False, not a second session.
        if not token_dao.consume(conn, token_id):
            raise _invalid_credentials()
        user_dao.mark_email_verified(conn, user_id)
        user_dao.clear_failed_logins(conn, user_id)

    return TokenResponse(
        access_token=create_token(
            user_id=user_id, role=user["role"], typ="access",
            minutes=settings.access_token_minutes,
        ),
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/forgot", response_model=ForgotResponse, status_code=status.HTTP_202_ACCEPTED,
             dependencies=[Depends(_forgot_limit)])
def forgot(payload: ForgotRequest, background: BackgroundTasks):
    settings = get_settings()
    started = time.monotonic()

    with read_connection() as conn:
        record = user_dao.get_by_email(conn, payload.email)

    if record is not None and record["is_active"]:
        token = new_reset_token()
        with transaction() as conn:
            token_dao.invalidate_open(conn, user_id=record["user_id"], purpose="reset_password")
            token_dao.issue(
                conn,
                user_id=record["user_id"],
                token_hash=hash_reset_token(token),
                purpose="reset_password",
                ttl_minutes=settings.reset_token_ttl_minutes,
            )
        background.add_task(
            _send_reset_token_safely, record["email"], token, record["user_id"]
        )
    else:
        # Matches the found branch's two round trips (invalidate + issue).
        # A remote DB's network RTT is bigger than the timing floor below, so
        # without this the floor cannot absorb the gap and the branches stay
        # distinguishable by timing even though both return the same body.
        with transaction() as conn:
            conn.execute("SELECT 1")
            conn.execute("SELECT 1")

    elapsed = time.monotonic() - started
    if elapsed < _FORGOT_FLOOR_SECONDS:
        time.sleep(_FORGOT_FLOOR_SECONDS - elapsed)

    return ForgotResponse()


@router.post("/reset", response_model=ResetResponse, dependencies=[Depends(_reset_limit)])
def reset(payload: ResetRequest):
    token_hash = hash_reset_token(payload.token)

    with read_connection() as conn:
        row = token_dao.get_open_by_hash(conn, token_hash=token_hash, purpose="reset_password")
        user = user_dao.get_by_id(conn, row["user_id"]) if row else None

    if row is None or user is None or not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    with transaction() as conn:
        # consume() is the single-use check: a race on the same token has one winner.
        if not token_dao.consume(conn, row["token_id"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
        user_dao.set_password(conn, user["user_id"], hash_password(payload.new_password))
        # Defensive close of any other open reset token for this user — forgot
        # already invalidates the previous one before issuing a new one, so in
        # practice there is only ever one, but this makes it an invariant.
        token_dao.invalidate_open(conn, user_id=user["user_id"], purpose="reset_password")

    return ResetResponse()
