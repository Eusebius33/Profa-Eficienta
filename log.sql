CREATE TABLE IF NOT EXISTS users ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL, "
    "username TEXT NOT NULL, "
    "email TEXT NOT NULL, "
    "hash INTEGER NOT NULL, "
    "gender NUMERIC NOT NULL DEFAULT M, "
    "liceu NUMERIC NOT NULL, "
    "tehnologie TIMESTAMP NOT NULL DEFAULT nu, "
    "FOREIGN KEY(user_id) REFERENCES users(id)"
    ")xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

CREATE TABLE user_style ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL, "
    "user_id INTEGER UNIQUE NOT NULL, "
    "email TEXT NOT NULL, "
    "hash INTEGER NOT NULL, "
    "gender NUMERIC NOT NULL DEFAULT M, "
    "liceu NUMERIC NOT NULL, "
    "tehnologie TIMESTAMP NOT NULL DEFAULT nu, "
    "FOREIGN KEY(user_id) REFERENCES users(id)"
    ")

CREATE TABLE users ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL, "
    "username TEXT NOT NULL, "
    "email TEXT NOT NULL, "
    "hash TEXT NOT NULL, "
    "gender TEXT NOT NULL DEFAULT M, "
    "liceu TEXT NOT NULL, "
    "tehnologie TEXT NOT NULL DEFAULT nu"
    ");


