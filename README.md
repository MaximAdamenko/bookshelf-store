# Book Shelf

A small online bookstore — FastAPI + React (Vite) + PostgreSQL — built as a worked
example of defending five vulnerability classes: broken access control, SQL injection,
mass assignment, malicious file upload, and authentication.

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
Client/   React + Vite frontend
docs/     design, security and workflow docs
```

## Requirements

- Python 3.12+ (developed on 3.14)
- Node 20+ (frontend, from Phase 7)
- A PostgreSQL 16 database reachable by connection URL

## Backend setup

```bash
cd Server
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt

cp .env.example .env      # then fill it in — see below
```

### Filling in `.env`

| Variable | Notes |
|---|---|
| `DATABASE_URL` | **Owner** URL. Runs DDL. Used only by `db/init_db.py`. |
| `APP_DATABASE_URL` | **App** URL — DML only, no DDL. Used by the running API. Leave blank to fall back to the owner URL (the app logs a warning). |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | The first admin. Hashed with argon2id before it reaches the database. |
| `MAIL_BACKEND` | `console` prints login codes to the terminal. `gmail` sends real mail. |

`.env` is gitignored. Never commit it.

### Creating the database

```bash
cd Server
./.venv/bin/python -m db.init_db
```

This applies `db/schema.sql`, loads the sample catalog from `db/seed.sql`, creates the
admin account, and grants the app role DML-only privileges.

> **Destructive.** `schema.sql` drops and recreates every table. The script refuses to
> run when `ENV=production` unless you pass `--force`.

Options: `--no-seed` (schema only), `--force` (override the production guard).

## Security notes

- All SQL lives in `Server/app/dao/` — nothing else in the application builds a query.
- The API connects with a restricted database role that cannot run DDL.
- Secrets come from the environment only; `.env.example` ships with blank values.

See [SECURITY.md](docs/SECURITY.md) for the full control list.
