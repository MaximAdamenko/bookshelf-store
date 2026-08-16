# Book Shelf

A small online bookstore — FastAPI + React (Vite) + PostgreSQL — built as a worked
example of defending five vulnerability classes: broken access control, SQL injection,
mass assignment, malicious file upload, and authentication.

No ORM: every query is hand-written parameterized SQL in a DAO layer. The API runs as a
database role that cannot execute DDL. Login is two-step (password, then a 6-digit code
by email).

Documentation lives in [`docs/`](docs/):

| Doc | What it covers |
|---|---|
| [DESIGN.md](docs/DESIGN.md) | Vision, scope, stack, data model, API surface, auth design |
| [SECURITY.md](docs/SECURITY.md) | The five threat classes → controls → the tests that prove them |
| [WORKFLOW.md](docs/WORKFLOW.md) | Development loop and the phase-by-phase task list |
| [LOGS.md](docs/LOGS.md) | Session log index |

---

## Layout

```
Server/   FastAPI backend — raw SQL + DAO layer, no ORM
  app/      core/ dao/ routers/ schemas/ services/
  db/       schema.sql, seed.sql, init_db.py
  tests/    101-test attack suite
  uploads/  cover images (gitignored)
Client/   React + Vite frontend
docs/     design, security and workflow docs
```

## Requirements

- Python 3.12+ (developed on 3.14)
- Node 20+ (developed on 25)
- A PostgreSQL 16+ database reachable by connection URL (developed against Neon, 18.4)

## Quick start

```bash
# backend — http://localhost:8000
cd Server
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env                       # fill it in, see below
./.venv/bin/python -m db.init_db           # destructive: drops and recreates
./.venv/bin/python -m uvicorn app.main:app --reload

# frontend — http://localhost:5173
cd Client
npm install
npm run dev
```

Swagger UI is at `http://localhost:8000/docs`, health at `/health`.

---

## Backend

### Environment

Every variable read by `app/core/config.py`. Only `DATABASE_URL` and `JWT_SECRET` have
no default — the app refuses to boot without them.

**Database**

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | *required* | **Owner** URL. Runs DDL. Used only by `db/init_db.py`. |
| `APP_DATABASE_URL` | falls back to owner | **App** URL — DML only. Used by the running API. Falling back logs a warning; see [SECURITY.md §2.6](docs/SECURITY.md). |

**First admin** — seeded by `init_db.py`, password argon2-hashed before it reaches the DB.

| Variable | Default |
|---|---|
| `ADMIN_EMAIL` | — |
| `ADMIN_PASSWORD` | — |
| `ADMIN_FIRST_NAME` | `Admin` |
| `ADMIN_LAST_NAME` | `User` |

**Security**

| Variable | Default | Notes |
|---|---|---|
| `JWT_SECRET` | *required* | ≥32 chars; placeholder values are rejected at boot. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_ALGORITHM` | `HS256` | `HS256` / `HS384` / `HS512` only |
| `ACCESS_TOKEN_MINUTES` | `60` | |
| `CHALLENGE_TOKEN_MINUTES` | `10` | Lifetime of the post-password, pre-OTP token |
| `OTP_TTL_MINUTES` | `10` | |
| `OTP_MAX_ATTEMPTS` | `5` | Wrong codes before the challenge dies |
| `RESET_TOKEN_TTL_MINUTES` | `30` | |
| `MAX_FAILED_LOGINS` | `5` | |
| `LOCKOUT_MINUTES` | `15` | |
| `PASSWORD_MIN_LENGTH` | `12` | Floor of 12; lower values are rejected at boot |

**Mail**

| Variable | Default | Notes |
|---|---|---|
| `MAIL_BACKEND` | `console` | `console` prints codes to the terminal; `gmail` sends real mail. `console` refuses to run when `ENV=production`. |
| `MAIL_FROM` | `GMAIL_USER` | |
| `GMAIL_USER` | — | Gmail address |
| `GMAIL_APP_PASSWORD` | — | A Google *app password*, not the account password |
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | STARTTLS |

**Uploads**

| Variable | Default | Notes |
|---|---|---|
| `UPLOAD_DIR` | `uploads` | |
| `MAX_UPLOAD_BYTES` | `2097152` | 2 MB; oversize uploads get 413 |
| `MAX_IMAGE_PIXELS` | `40000000` | Decompression-bomb guard |

**App**

| Variable | Default | Notes |
|---|---|---|
| `ENV` | `dev` | `dev` / `staging` / `production` |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated. Under `ENV=production` the app refuses to boot on a wildcard, an empty list, or any `http://` origin. |

**Tests** — optional; point the suite at an isolated database.

| Variable | Notes |
|---|---|
| `TEST_DATABASE_URL` | Overrides `DATABASE_URL` when running pytest |
| `TEST_APP_DATABASE_URL` | Overrides `APP_DATABASE_URL` when running pytest |

`.env` is gitignored. Never commit it. `.env.example` ships with blank values.

### Creating the database

```bash
cd Server
./.venv/bin/python -m db.init_db
```

Applies `db/schema.sql`, loads the sample catalog from `db/seed.sql` (9 categories,
18 authors, 13 publishers, 16 books), creates the admin, and grants the app role
DML-only privileges.

> **Destructive.** `schema.sql` drops and recreates every table. The script refuses to
> run when `ENV=production` unless you pass `--force`.

| Flag | Effect |
|---|---|
| `--no-seed` | Schema only, no sample catalog |
| `--grants-only` | Just (re)grant the app role — no DDL, no data loss |
| `--force` | Override the production guard |

### Running

```bash
cd Server
./.venv/bin/python -m uvicorn app.main:app --reload
```

### Tests

101 tests, run against a **live** database — they are additive and self-cleaning, never
reset schema and never truncate. Every row they create is marked `pytest-bookshelf…`
and only marked rows are deleted, on both setup and teardown. Safe to run against the
development database and safe to re-run. The suite refuses to run when `ENV=production`.

```bash
cd Server
./.venv/bin/python -m pytest              # ~74s
./.venv/bin/python -m pytest tests/test_injection.py -v
```

| Module | Covers |
|---|---|
| `test_access_control.py` | IDOR, privilege escalation, admin route guards |
| `test_injection.py` | 7 SQL payloads across every user-controlled field |
| `test_mass_assignment.py` | `extra="forbid"` on every input schema |
| `test_upload.py` | Polyglots, SVG/PHP payloads, traversal filenames, oversize |
| `test_auth.py` | `alg:none`, forged keys, lockout, OTP reuse, enumeration |
| `test_concurrency.py` | Oversell race, `CHECK (quantity >= 0)` |

---

## Frontend

```bash
cd Client
npm install
npm run dev        # http://localhost:5173
```

| Script | Effect |
|---|---|
| `npm run dev` | Vite dev server |
| `npm run build` | `tsc -b && vite build` |
| `npm run preview` | Serve the production build |
| `npm run lint` | oxlint |

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend origin. Set it in `Client/.env.local` if the API is elsewhere; that origin must also appear in the backend's `CORS_ORIGINS`. |

The access token is held in `sessionStorage` — it survives a refresh and dies with the
tab. A 401 from any call clears it and bounces the user to `/login`.

---

## Security notes

- All SQL lives in `Server/app/dao/` — nothing else in the application builds a query.
- The API connects with a restricted database role that cannot run DDL.
- Secrets come from the environment only; `.env.example` ships with blank values.
- Cross-user access returns **404, never 403** — a 403 confirms the row exists.

See [SECURITY.md](docs/SECURITY.md) for the full control list and the verification table.
