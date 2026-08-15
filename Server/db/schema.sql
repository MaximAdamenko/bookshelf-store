BEGIN;

CREATE EXTENSION IF NOT EXISTS citext;

DROP TABLE IF EXISTS order_items, orders, cart_items, book_category, book_author,
                     books, categories, authors, publishers, email_tokens,
                     addresses, users CASCADE;
DROP TYPE  IF EXISTS user_role, order_status, token_purpose CASCADE;

CREATE TYPE user_role     AS ENUM ('admin', 'customer');
CREATE TYPE order_status  AS ENUM ('pending', 'paid', 'shipped', 'cancelled');
CREATE TYPE token_purpose AS ENUM ('login_otp', 'reset_password');


CREATE TABLE users (
    user_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email          CITEXT      NOT NULL UNIQUE,
    password_hash  TEXT        NOT NULL,
    first_name     TEXT        NOT NULL CHECK (length(first_name) BETWEEN 1 AND 60),
    last_name      TEXT        NOT NULL CHECK (length(last_name)  BETWEEN 1 AND 60),
    birth_date     DATE        CHECK (birth_date BETWEEN DATE '1900-01-01' AND DATE '2015-01-01'),
    phone          TEXT        CHECK (phone ~ '^\+?[0-9 \-]{6,20}$'),
    role           user_role   NOT NULL DEFAULT 'customer',
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN     NOT NULL DEFAULT FALSE,
    failed_logins  SMALLINT    NOT NULL DEFAULT 0,
    locked_until   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- birth_date can't be checked against CURRENT_DATE here: Postgres rejects
-- non-IMMUTABLE functions in CHECK. Pydantic enforces it.


CREATE TABLE addresses (
    address_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT  NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    street      TEXT    NOT NULL CHECK (length(street) BETWEEN 1 AND 200),
    city        TEXT    NOT NULL CHECK (length(city)   BETWEEN 1 AND 100),
    apartment   TEXT    CHECK (length(apartment) <= 40),
    postal_code TEXT    NOT NULL CHECK (postal_code ~ '^[A-Za-z0-9 \-]{3,12}$'),
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX        addresses_user_idx    ON addresses (user_id);
CREATE UNIQUE INDEX addresses_one_default ON addresses (user_id) WHERE is_default;


-- token_hash is deliberately not UNIQUE: a 6-digit OTP has only 1e6 possible
-- values, so two users can hold the same code at once. A unique index would
-- turn that collision into a 500 on login.
CREATE TABLE email_tokens (
    token_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT          NOT NULL,
    purpose    token_purpose NOT NULL,
    attempts   SMALLINT      NOT NULL DEFAULT 0 CHECK (attempts <= 5),
    expires_at TIMESTAMPTZ   NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX email_tokens_open_idx ON email_tokens (user_id, purpose) WHERE used_at IS NULL;
CREATE INDEX email_tokens_hash_idx ON email_tokens (token_hash);


CREATE TABLE publishers (
    publisher_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 1 AND 150)
);

CREATE TABLE authors (
    author_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name TEXT NOT NULL CHECK (length(first_name) BETWEEN 1 AND 60),
    last_name  TEXT NOT NULL CHECK (length(last_name)  BETWEEN 1 AND 60),
    UNIQUE (first_name, last_name)
);

CREATE TABLE categories (
    category_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        CITEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 1 AND 60)
);


CREATE TABLE books (
    book_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        TEXT    NOT NULL CHECK (length(title) BETWEEN 1 AND 300),
    description  TEXT    NOT NULL DEFAULT '',
    price_cents  INTEGER NOT NULL CHECK (price_cents >= 0),
    quantity     INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    publisher_id BIGINT  REFERENCES publishers(publisher_id) ON DELETE SET NULL,
    -- Only a server-generated UUID filename passes, so path traversal is
    -- impossible even if the upload handler is wrong.
    cover_path   TEXT    CHECK (cover_path ~ '^[0-9a-f]{32}\.(jpg|png|webp)$'),
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')),       'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'D')
    ) STORED
);
CREATE INDEX books_search_idx ON books USING GIN (search_vector);
CREATE INDEX books_active_idx ON books (created_at DESC) WHERE is_active;


CREATE TABLE book_author (
    book_id   BIGINT NOT NULL REFERENCES books(book_id)     ON DELETE CASCADE,
    author_id BIGINT NOT NULL REFERENCES authors(author_id) ON DELETE RESTRICT,
    PRIMARY KEY (book_id, author_id)
);
CREATE INDEX book_author_author_idx ON book_author (author_id);

CREATE TABLE book_category (
    book_id     BIGINT NOT NULL REFERENCES books(book_id)          ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    PRIMARY KEY (book_id, category_id)
);
CREATE INDEX book_category_category_idx ON book_category (category_id);


CREATE TABLE cart_items (
    cart_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      BIGINT  NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    book_id      BIGINT  NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    quantity     INTEGER NOT NULL CHECK (quantity > 0 AND quantity <= 99),
    added_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, book_id)
);


CREATE TABLE orders (
    order_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          BIGINT       NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    status           order_status NOT NULL DEFAULT 'pending',
    amount_cents     INTEGER      NOT NULL CHECK (amount_cents >= 0),
    -- Shipping is a snapshot, not a FK to addresses: editing a saved address
    -- must never rewrite where a past order was sent.
    ship_first_name  TEXT NOT NULL,
    ship_last_name   TEXT NOT NULL,
    ship_street      TEXT NOT NULL,
    ship_city        TEXT NOT NULL,
    ship_apartment   TEXT,
    ship_postal_code TEXT NOT NULL,
    ship_phone       TEXT,
    order_date       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX orders_user_idx ON orders (user_id, order_date DESC);


CREATE TABLE order_items (
    order_item_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id          BIGINT  NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    book_id           BIGINT  REFERENCES books(book_id) ON DELETE SET NULL,
    title_snapshot    TEXT    NOT NULL,
    authors_snapshot  TEXT    NOT NULL DEFAULT '',
    unit_price_cents  INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    quantity          INTEGER NOT NULL CHECK (quantity > 0),
    total_price_cents INTEGER GENERATED ALWAYS AS (unit_price_cents * quantity) STORED,
    UNIQUE (order_id, book_id)
);
CREATE INDEX order_items_order_idx ON order_items (order_id);


CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER books_touch BEFORE UPDATE ON books
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

COMMIT;
