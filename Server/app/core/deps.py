from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Connection

from app.core.db import db_read
from app.core.security import decode_token
from app.dao import user_dao

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    conn: Annotated[Connection, Depends(db_read)],
) -> dict:
    if credentials is None:
        raise _unauthorized()

    # expected_typ is the whole point: a challenge token is a valid signed JWT
    # and would sail through without it. (SECURITY.md 5.5)
    claims = decode_token(credentials.credentials, expected_typ="access")
    if claims is None:
        raise _unauthorized()

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise _unauthorized()

    # Reloaded per request, not trusted from the token: a deactivated account or
    # a demoted admin loses access immediately, not at token expiry.
    user = user_dao.get_by_id(conn, user_id)
    if user is None or not user["is_active"]:
        raise _unauthorized()
    return user


def require_admin(user: Annotated[dict, Depends(current_user)]) -> dict:
    # 404, not 403: a 403 tells a customer the admin surface is there.
    # (SECURITY.md 1.3)
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return user


CurrentUser = Annotated[dict, Depends(current_user)]
AdminUser = Annotated[dict, Depends(require_admin)]
