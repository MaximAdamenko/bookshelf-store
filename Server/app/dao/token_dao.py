from psycopg import Connection

# The DB caps attempts at 5 (schema.sql CHECK). LEAST keeps a misconfigured
# OTP_MAX_ATTEMPTS from turning a wrong code into a constraint violation.
_ATTEMPT_CEILING = 5


def issue(conn: Connection, *, user_id: int, token_hash: str, purpose: str,
          ttl_minutes: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO email_tokens (user_id, token_hash, purpose, expires_at)
               VALUES (%s, %s, %s::token_purpose, now() + make_interval(mins => %s))
               RETURNING token_id""",
            (user_id, token_hash, purpose, ttl_minutes),
        )
        return cur.fetchone()["token_id"]


def invalidate_open(conn: Connection, *, user_id: int, purpose: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE email_tokens SET used_at = now()
                WHERE user_id = %s AND purpose = %s::token_purpose AND used_at IS NULL""",
            (user_id, purpose),
        )
        return cur.rowcount


def get_open(conn: Connection, *, token_id: int, user_id: int, purpose: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT token_id, user_id, token_hash, attempts, expires_at
                 FROM email_tokens
                WHERE token_id = %s AND user_id = %s AND purpose = %s::token_purpose
                  AND used_at IS NULL AND expires_at > now()""",
            (token_id, user_id, purpose),
        )
        return cur.fetchone()


def get_open_by_hash(conn: Connection, *, token_hash: str, purpose: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT token_id, user_id, token_hash, attempts, expires_at
                 FROM email_tokens
                WHERE token_hash = %s AND purpose = %s::token_purpose
                  AND used_at IS NULL AND expires_at > now()""",
            (token_hash, purpose),
        )
        return cur.fetchone()


def record_attempt(conn: Connection, token_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE email_tokens SET attempts = LEAST(attempts + 1, %s) WHERE token_id = %s",
            (_ATTEMPT_CEILING, token_id),
        )


def consume(conn: Connection, token_id: int) -> bool:
    # Conditional on used_at IS NULL, so two requests racing with the same valid
    # code cannot both win. The loser gets rowcount 0 and a 401.
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE email_tokens SET used_at = now() WHERE token_id = %s AND used_at IS NULL",
            (token_id,),
        )
        return cur.rowcount == 1
