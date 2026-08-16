from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from psycopg import Connection

from app.core.config import get_settings
from app.core.db import db_read
from app.dao import book_dao
from app.schemas.books import (
    AuthorRef,
    BookListResponse,
    BookPublic,
    BookSearchParams,
    CategoryRef,
    PublisherRef,
)
from app.services.storage import LocalDiskStorage

router = APIRouter(prefix="/books", tags=["catalog"])

media_router = APIRouter(prefix="/media", tags=["catalog"])

_MEDIA_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@media_router.get("/covers/{filename}")
def get_cover(filename: str):
    path = LocalDiskStorage(get_settings().upload_path).resolve(filename)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    # A replaced cover always gets a new UUID name, so a URL's bytes never
    # change and immutable caching is safe.
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES[filename.rsplit(".", 1)[-1]],
        headers={"Content-Disposition": "inline",
                 "Cache-Control": "public, max-age=86400, immutable"},
    )


@router.get("", response_model=BookListResponse)
def list_books(
    params: Annotated[BookSearchParams, Query()],
    conn: Annotated[Connection, Depends(db_read)],
):
    items, total = book_dao.search(conn, params)
    return BookListResponse(items=items, total=total)


@router.get("/{book_id}", response_model=BookPublic)
def get_book(book_id: int, conn: Annotated[Connection, Depends(db_read)]):
    book = book_dao.get_by_id(conn, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return book


categories_router = APIRouter(prefix="/categories", tags=["catalog"])


@categories_router.get("", response_model=list[CategoryRef])
def list_categories(conn: Annotated[Connection, Depends(db_read)]):
    return book_dao.list_categories(conn)


refs_router = APIRouter(tags=["catalog"])


@refs_router.get("/authors", response_model=list[AuthorRef])
def list_authors(conn: Annotated[Connection, Depends(db_read)]):
    return book_dao.list_authors(conn)


@refs_router.get("/publishers", response_model=list[PublisherRef])
def list_publishers(conn: Annotated[Connection, Depends(db_read)]):
    return book_dao.list_publishers(conn)
