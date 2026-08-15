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
from urllib.parse import urlparse

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402

DB_DIR = Path(__file__).resolve().parent


def _run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    print(f"  applying {path.name} ...", end=" ", flush=True)
    conn.execute(path.read_text(encoding="utf-8"))
    print("ok")


def _app_role_name(app_url: str) -> str | None:
    if not app_url:
        return None
    user = urlparse(app_url).username
    return user or None


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
    args = parser.parse_args()

    settings = get_settings()

    if settings.env == "production" and not args.force:
        print("REFUSING: ENV=production. This drops every table. Re-run with --force "
              "only if you are certain.", file=sys.stderr)
        return 2

    target = urlparse(settings.database_url)
    print(f"Target: {target.hostname}/{(target.path or '').lstrip('/')} as {target.username}")

    with psycopg.connect(settings.database_url, autocommit=True,
                         row_factory=psycopg.rows.dict_row) as conn:
        _run_sql_file(conn, DB_DIR / "schema.sql")

        if not args.no_seed:
            _run_sql_file(conn, DB_DIR / "seed.sql")

        create_admin(conn, settings)

        role = _app_role_name(settings.app_database_url)
        if role:
            try:
                grant_app_role(conn, role)
            except psycopg.errors.UndefinedObject:
                print(f"  grants: SKIPPED - role '{role}' does not exist yet.\n"
                      f"          Create it on the provider, then re-run.")
        else:
            print("  grants: skipped (APP_DATABASE_URL not set - the API will run "
                  "with the owner role; see SECURITY.md 2.6)")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
