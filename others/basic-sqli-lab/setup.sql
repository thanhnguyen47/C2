CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
);

INSERT INTO users (username, password) VALUES ('admin', 'admin123');
-- sqlite3 db.sqlite < setup.sql
