CREATE TABLE authors (
    id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE books (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_id BIGINT NOT NULL REFERENCES authors (id),
    title     TEXT NOT NULL,
    pages     INT
);

CREATE INDEX books_author_id_idx ON books (author_id);
