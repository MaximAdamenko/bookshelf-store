BEGIN;

INSERT INTO categories (name) VALUES
    ('Fiction'), ('Science Fiction'), ('Fantasy'), ('Dystopian'),
    ('Classics'), ('Non-fiction'), ('History'), ('Psychology'), ('Programming')
ON CONFLICT (name) DO NOTHING;

INSERT INTO authors (first_name, last_name) VALUES
    ('Frank', 'Herbert'),
    ('William', 'Gibson'),
    ('J.R.R.', 'Tolkien'),
    ('George', 'Orwell'),
    ('Aldous', 'Huxley'),
    ('J.K.', 'Rowling'),
    ('F. Scott', 'Fitzgerald'),
    ('Toni', 'Morrison'),
    ('Margaret', 'Atwood'),
    ('Yuval Noah', 'Harari'),
    ('Daniel', 'Kahneman'),
    ('Ursula K.', 'Le Guin'),
    ('George R. R.', 'Martin'),
    ('Robert C.', 'Martin'),
    ('Andrew', 'Hunt'),
    ('David', 'Thomas'),
    ('Neil', 'Gaiman'),
    ('Terry', 'Pratchett')
ON CONFLICT (first_name, last_name) DO NOTHING;

INSERT INTO publishers (name) VALUES
    ('Ace Books'), ('HarperCollins'), ('Penguin Random House'), ('Bloomsbury'),
    ('Scribner'), ('Alfred A. Knopf'), ('Vintage'), ('Harper'),
    ('Farrar, Straus and Giroux'), ('Bantam'), ('Prentice Hall'),
    ('Addison-Wesley'), ('Gollancz')
ON CONFLICT (name) DO NOTHING;

CREATE TEMP TABLE seed_books (
    title       TEXT,
    description TEXT,
    price_cents INTEGER,
    quantity    INTEGER,
    publisher   TEXT,
    authors     TEXT[],
    categories  TEXT[]
) ON COMMIT DROP;

INSERT INTO seed_books VALUES
 ('Dune',
  'Paul Atreides and his family are handed stewardship of Arrakis, the desert world that is the only source of the spice melange.',
  1899, 12, 'Ace Books', ARRAY['Frank|Herbert'], ARRAY['Science Fiction','Fiction']),

 ('Neuromancer',
  'A burned-out console cowboy is hired for one last run against an artificial intelligence.',
  1650, 7, 'Ace Books', ARRAY['William|Gibson'], ARRAY['Science Fiction','Fiction']),

 ('The Hobbit',
  'Bilbo Baggins is swept into a quest to reclaim a treasure guarded by the dragon Smaug.',
  1450, 20, 'HarperCollins', ARRAY['J.R.R.|Tolkien'], ARRAY['Fantasy','Fiction','Classics']),

 ('Nineteen Eighty-Four',
  'Winston Smith works in the Ministry of Truth, rewriting the past for a Party that watches everything.',
  1299, 15, 'Penguin Random House', ARRAY['George|Orwell'], ARRAY['Dystopian','Fiction','Classics']),

 ('Brave New World',
  'A society engineered for stability, comfort and conditioned contentment - and the man who cannot accept it.',
  1350, 9, 'HarperCollins', ARRAY['Aldous|Huxley'], ARRAY['Dystopian','Fiction','Classics']),

 ('Harry Potter and the Philosopher''s Stone',
  'An orphan discovers on his eleventh birthday that he is a wizard.',
  1599, 25, 'Bloomsbury', ARRAY['J.K.|Rowling'], ARRAY['Fantasy','Fiction']),

 ('The Great Gatsby',
  'Jay Gatsby throws lavish parties in pursuit of a green light across the bay.',
  1199, 0, 'Scribner', ARRAY['F. Scott|Fitzgerald'], ARRAY['Classics','Fiction']),

 ('Beloved',
  'Sethe, an escaped slave, is haunted by the daughter she lost.',
  1499, 6, 'Alfred A. Knopf', ARRAY['Toni|Morrison'], ARRAY['Classics','Fiction']),

 ('The Handmaid''s Tale',
  'In the Republic of Gilead, Offred is valued only for her fertility.',
  1399, 11, 'Vintage', ARRAY['Margaret|Atwood'], ARRAY['Dystopian','Fiction']),

 ('Sapiens: A Brief History of Humankind',
  'How an unremarkable ape came to dominate the planet.',
  2199, 14, 'Harper', ARRAY['Yuval Noah|Harari'], ARRAY['Non-fiction','History']),

 ('Thinking, Fast and Slow',
  'The two systems that drive the way we think, and where each one fails.',
  2050, 8, 'Farrar, Straus and Giroux', ARRAY['Daniel|Kahneman'], ARRAY['Non-fiction','Psychology']),

 ('The Left Hand of Darkness',
  'An envoy arrives on a world whose inhabitants have no fixed sex.',
  1550, 5, 'Ace Books', ARRAY['Ursula K.|Le Guin'], ARRAY['Science Fiction','Fiction']),

 ('A Game of Thrones',
  'Summer spanned decades. Winter can last a lifetime. And the struggle for the Iron Throne has begun.',
  1799, 10, 'Bantam', ARRAY['George R. R.|Martin'], ARRAY['Fantasy','Fiction']),

 ('Good Omens',
  'An angel and a demon have grown rather fond of life on Earth and would prefer the apocalypse be cancelled.',
  1450, 13, 'Gollancz', ARRAY['Neil|Gaiman','Terry|Pratchett'], ARRAY['Fantasy','Fiction']),

 ('Clean Code',
  'A handbook of agile software craftsmanship.',
  3499, 4, 'Prentice Hall', ARRAY['Robert C.|Martin'], ARRAY['Programming','Non-fiction']),

 ('The Pragmatic Programmer',
  'From journeyman to master - practical advice on the craft of writing software.',
  3899, 6, 'Addison-Wesley', ARRAY['Andrew|Hunt','David|Thomas'], ARRAY['Programming','Non-fiction']);

INSERT INTO books (title, description, price_cents, quantity, publisher_id)
SELECT s.title, s.description, s.price_cents, s.quantity, p.publisher_id
FROM   seed_books s
LEFT   JOIN publishers p ON p.name = s.publisher;

INSERT INTO book_author (book_id, author_id)
SELECT b.book_id, a.author_id
FROM   seed_books s
JOIN   books b ON b.title = s.title
CROSS  JOIN LATERAL unnest(s.authors) AS an(full_name)
JOIN   authors a ON a.first_name = split_part(an.full_name, '|', 1)
                AND a.last_name  = split_part(an.full_name, '|', 2)
ON CONFLICT DO NOTHING;

INSERT INTO book_category (book_id, category_id)
SELECT b.book_id, c.category_id
FROM   seed_books s
JOIN   books b ON b.title = s.title
CROSS  JOIN LATERAL unnest(s.categories) AS cn(name)
JOIN   categories c ON c.name = cn.name
ON CONFLICT DO NOTHING;

COMMIT;
