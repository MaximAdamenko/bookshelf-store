from datetime import date

from psycopg import Connection

# Server-owned constant, no user input. The one allowed f-string. (SECURITY.md 2)
_PUBLIC = """user_id, email, first_name, last_name, birth_date, phone, role,
             is_active, email_verified, failed_logins, locked_until, created_at"""


def get_by_id(conn: Connection, user_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM users WHERE user_id = %s", (user_id,))
        return cur.fetchone()


def get_by_email(conn: Connection, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM users WHERE email = %s", (email,))
        return cur.fetchone()


def get_auth_record(conn: Connection, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_PUBLIC}, password_hash FROM users WHERE email = %s",
            (email,),
        )
        return cur.fetchone()


def create(
    conn: Connection,
    *,
    email: str,
    password_hash: str,
    first_name: str,
    last_name: str,
    birth_date: date | None = None,
    phone: str | None = None,
) -> dict | None:
    # Explicit keywords, no **payload: a field the caller cannot name is a
    # field the caller cannot set. role is not a parameter at all. (SECURITY.md 3.3/3.4)
    #
    # ON CONFLICT rather than catching UniqueViolation: a raised constraint
    # error aborts the surrounding transaction, and we would then fail on commit.
    with conn.cursor() as cur:
        cur.execute(
            f"""INSERT INTO users (email, password_hash, first_name, last_name,
                                   birth_date, phone)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING {_PUBLIC}""",
            (email, password_hash, first_name, last_name, birth_date, phone),
        )
        return cur.fetchone()


def register_failed_login(
    conn: Connection, user_id: int, *, max_failed: int, lockout_minutes: int
) -> None:
    # LEAST caps the counter: failed_logins is SMALLINT and an unbounded
    # attacker would otherwise overflow it at 32767.
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE users
                  SET failed_logins = LEAST(failed_logins + 1, 999),
                      locked_until  = CASE WHEN failed_logins + 1 >= %s
                                           THEN now() + make_interval(mins => %s)
                                           ELSE locked_until END
                WHERE user_id = %s""",
            (max_failed, lockout_minutes, user_id),
        )


def clear_failed_logins(conn: Connection, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET failed_logins = 0, locked_until = NULL WHERE user_id = %s",
            (user_id,),
        )


def mark_email_verified(conn: Connection, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET email_verified = TRUE WHERE user_id = %s", (user_id,)
        )


def set_password(conn: Connection, user_id: int, password_hash: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE users
                  SET password_hash = %s, failed_logins = 0, locked_until = NULL
                WHERE user_id = %s""",
            (password_hash, user_id),
        )
