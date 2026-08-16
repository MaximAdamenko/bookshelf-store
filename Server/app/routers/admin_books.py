from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from psycopg import Connection

from app.core.config import get_settings
from app.core.db import db_read, db_write
from app.core.deps import require_admin
from app.dao import book_dao
from app.services.storage import LocalDiskStorage, UploadRejected, process_cover
from app.schemas.books import (
    BookCreate,
    BookListResponse,
    BookPatch,
    BookPublic,
    BookSearchParams,
)

# Guard on the router, not per-endpoint: a new route here is admin-only by
# default. (SECURITY.md 1.5)
router = APIRouter(
    prefix="/admin/books",
    tags=["admin:catalog"],
    dependencies=[Depends(require_admin)],
)

_not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("", response_model=BookListResponse)
def list_books_admin(
    params: Annotated[BookSearchParams, Query()],
    conn: Annotated[Connection, Depends(db_read)],
):
    items, total = book_dao.search(conn, params, include_inactive=True)
    return BookListResponse(items=items, total=total)


@router.get("/{book_id}", response_model=BookPublic)
def get_book_admin(book_id: int, conn: Annotated[Connection, Depends(db_read)]):
    book = book_dao.get_by_id(conn, book_id, include_inactive=True)
    if book is None:
        raise _not_found
    return book


@router.post("", response_model=BookPublic, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, conn: Annotated[Connection, Depends(db_write)]):
    return book_dao.create(conn, payload)


@router.patch("/{book_id}", response_model=BookPublic)
def patch_book(
    book_id: int, payload: BookPatch, conn: Annotated[Connection, Depends(db_write)]
):
    book = book_dao.patch(conn, book_id, payload.model_dump(exclude_unset=True))
    if book is None:
        raise _not_found
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, conn: Annotated[Connection, Depends(db_write)]):
    if not book_dao.soft_delete(conn, book_id):
        raise _not_found


@router.post("/{book_id}/cover", response_model=BookPublic)
def upload_cover(book_id: int, file: UploadFile,
                 conn: Annotated[Connection, Depends(db_write)]):
    settings = get_settings()
    try:
        data, ext = process_cover(
            file.file, file.filename or "",
            max_bytes=settings.max_upload_bytes,
            max_pixels=settings.max_image_pixels,
        )
    except UploadRejected as e:
        code = (status.HTTP_413_CONTENT_TOO_LARGE if e.too_large
                else status.HTTP_422_UNPROCESSABLE_CONTENT)
        raise HTTPException(status_code=code, detail=str(e))

    storage = LocalDiskStorage(settings.upload_path)
    new_name = storage.save(data, ext)
    try:
        old_name = book_dao.set_cover(conn, book_id, new_name)
    except book_dao.UnknownIdError:
        # book_id comes from the path: missing book is a 404 here, not the
        # global 422 that body-supplied reference ids get.
        storage.delete(new_name)
        raise _not_found
    if old_name and old_name != new_name:
        storage.delete(old_name)  # (SECURITY.md 4.9)
    return book_dao.get_by_id(conn, book_id, include_inactive=True)
