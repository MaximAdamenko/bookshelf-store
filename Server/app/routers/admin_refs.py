from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from psycopg import Connection

from app.core.db import db_write
from app.core.deps import require_admin
from app.dao import book_dao
from app.schemas.books import AuthorCreate, AuthorRef

# Guard on the router, not per-endpoint. (SECURITY.md 1.5)
router = APIRouter(
    prefix="/admin",
    tags=["admin:catalog"],
    dependencies=[Depends(require_admin)],
)


@router.post("/authors", response_model=AuthorRef, status_code=status.HTTP_201_CREATED)
def create_author(
    payload: AuthorCreate,
    response: Response,
    conn: Annotated[Connection, Depends(db_write)],
):
    author, created = book_dao.create_author(
        conn, first_name=payload.first_name, last_name=payload.last_name
    )
    # UNIQUE (first_name, last_name) already declares that the pair identifies an
    # author here, so a repeat is the same author, not an error. 200 says it
    # existed; the body is identical either way.
    if not created:
        response.status_code = status.HTTP_200_OK
    return author
