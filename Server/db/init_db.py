#!/usr/bin/env python3
"""Initialise the Book Shelf database.

    python -m db.init_db            # schema + seed + admin + grants
    python -m db.init_db --no-seed  # schema only

Run from the Server/ directory.

DESTRUCTIVE: schema.sql drops and recreates every table.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402

DB_DIR = Path(__file__).resolve().parent


def _run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    print(f"  applying {path.name} ...", end=" ", flush=True)
    conn.execute(path.read_text(encoding="utf-8"))
    print("ok")


def _app_role_credentials(app_url: str) -> tuple[str, str] | None:
    if not app_url:
        return None
    parsed = urlparse(app_url)
    if not parsed.username or not parsed.password:
        return None
    return parsed.username, unquote(parsed.password)


def create_app_role(conn: psycopg.Connection, role: str, password: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        if cur.fetchone():
            print(f"  role: {role} already exists")
            return
    # Identifier/Literal composition: role names can't be %s-parameterized.
    conn.execute(
        sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE")
        .format(sql.Identifier(role), sql.Literal(password))
    )
    print(f"  role: {role} created (LOGIN only, no superuser/createdb/createrole)")


def create_admin(conn: psycopg.Connection, settings) -> None:
    from argon2 import PasswordHasher

    email = settings.admin_email.strip()
    password = settings.admin_password

    if not email or not password:
        print("  admin: skipped (ADMIN_EMAIL / ADMIN_PASSWORD not set in .env)")
        return
    if len(password) < settings.password_min_length:
        raise SystemExit(
            f"ADMIN_PASSWORD must be at least {settings.password_min_length} characters"
        )

    password_hash = PasswordHasher().hash(password)

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO users (email, password_hash, first_name, last_name,
                                  role, email_verified)
               VALUES (%s, %s, %s, %s, 'admin', TRUE)
               ON CONFLICT (email) DO UPDATE
                   SET password_hash = EXCLUDED.password_hash,
                       role          = 'admin'
               RETURNING user_id""",
            (email, password_hash, settings.admin_first_name, settings.admin_last_name),
        )
        row = cur.fetchone()
    print(f"  admin: {email} ready (user_id={row['user_id']})")


def grant_app_role(conn: psycopg.Connection, role: str) -> None:
    ident = sql.Identifier(role)
    statements = [
        sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(ident),
        sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(ident),
        sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(ident),
        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(ident),
        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT USAGE, SELECT ON SEQUENCES TO {}").format(ident),
    ]
    for stmt in statements:
        conn.execute(stmt)
    print(f"  grants: {role} has DML only (no DDL)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise the Book Shelf database")
    parser.add_argument("--no-seed", action="store_true", help="schema only, no sample catalog")
    parser.add_argument("--force", action="store_true", help="allow running when ENV=production")
    parser.add_argument("--grants-only", action="store_true",
                        help="create the app role + grants only; no schema, seed, or admin")
    args = parser.parse_args()

    settings = get_settings()
    creds = _app_role_credentials(settings.app_database_url)

    target = urlparse(settings.database_url)
    print(f"Target: {target.hostname}/{(target.path or '').lstrip('/')} as {target.username}")

    if args.grants_only:
        if creds is None:
            print("APP_DATABASE_URL with user+password must be set for --grants-only",
                  file=sys.stderr)
            return 2
        with psycopg.connect(settings.database_url, autocommit=True,
                             row_factory=psycopg.rows.dict_row) as conn:
            create_app_role(conn, *creds)
            grant_app_role(conn, creds[0])
        print("\nDone.")
        return 0

    if settings.env == "production" and not args.force:
        print("REFUSING: ENV=production. This drops every table. Re-run with --force "
              "only if you are certain.", file=sys.stderr)
        return 2

    with psycopg.connect(settings.database_url, autocommit=True,
                         row_factory=psycopg.rows.dict_row) as conn:
        _run_sql_file(conn, DB_DIR / "schema.sql")

        if not args.no_seed:
            _run_sql_file(conn, DB_DIR / "seed.sql")

        create_admin(conn, settings)

        if creds:
            create_app_role(conn, *creds)
            grant_app_role(conn, creds[0])
        else:
            print("  grants: skipped (APP_DATABASE_URL not set - the API will run "
                  "with the owner role; see SECURITY.md 2.6)")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
