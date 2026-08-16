import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.bodylimit import BodySizeLimit
from app.core.config import get_settings
from app.core.db import close_pool, get_pool, init_pool
from app.dao.book_dao import UnknownIdError
from app.routers import admin_books, admin_orders, admin_refs, auth, books, cart, orders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("bookshelf")

settings = get_settings()
_is_prod = settings.env == "production"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_pool()
    log.info("db pool ready (env=%s)", settings.env)
    yield
    close_pool()


app = FastAPI(
    title="Book Shelf API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    openapi_url=None if _is_prod else "/openapi.json",
    redoc_url=None,
)

# Added before CORS so it ends up inside it: a 413 still travels back out through
# the CORS and security-header layers instead of reaching the browser bare.
app.add_middleware(
    BodySizeLimit,
    json_limit=64 * 1024,
    upload_limit=settings.max_upload_bytes + 64 * 1024,  # slack for multipart framing
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Swagger UI pulls its JS from a CDN, so the lockdown CSP would break /docs.
    # Everything else is JSON and needs no resources at all.
    if not request.url.path.startswith(("/docs", "/openapi.json")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    if _is_prod:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(psycopg.Error)
async def _database_error(request: Request, exc: psycopg.Error):
    # Driver text can carry SQL fragments and column names. It goes to the log,
    # never to the client. (SECURITY.md 2.7)
    log.exception("database error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.exception_handler(UnknownIdError)
async def _unknown_id(request: Request, exc: UnknownIdError):
    return JSONResponse(status_code=422, content={"detail": f"unknown id in {exc.field}"})


app.include_router(auth.router)
app.include_router(books.router)
app.include_router(books.media_router)
app.include_router(books.categories_router)
app.include_router(books.refs_router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(admin_books.router)
app.include_router(admin_orders.router)
app.include_router(admin_refs.router)


@app.get("/health", tags=["meta"])
def health():
    with get_pool().connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "env": settings.env}
