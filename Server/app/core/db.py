import logging
from collections.abc import Generator, Iterator
from contextlib import contextmanager

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

log = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def init_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    if settings.uses_privileged_db_role:
        log.warning(
            "APP_DATABASE_URL is not set - the API is connecting with the schema "
            "OWNER role. Least privilege is not in effect (SECURITY.md 2.6)."
        )

    _pool = ConnectionPool(
        conninfo=settings.runtime_database_url,
        min_size=1,
        max_size=10,
        max_idle=300,
        kwargs={"row_factory": dict_row, "autocommit": False},
        open=True,
    )
    _pool.wait(timeout=10)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        return init_pool()
    return _pool


@contextmanager
def transaction() -> Generator[Connection]:
    with get_pool().connection() as conn:
        with conn.transaction():
            yield conn


@contextmanager
def read_connection() -> Generator[Connection]:
    with get_pool().connection() as conn:
        try:
            yield conn
        finally:
            conn.rollback()


def db_read() -> Iterator[Connection]:
    with read_connection() as conn:
        yield conn


def db_write() -> Iterator[Connection]:
    with transaction() as conn:
        yield conn
