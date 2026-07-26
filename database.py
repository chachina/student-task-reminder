"""
Database helper — Neon Postgres version.
Replaces SQLite with psycopg2 + DATABASE_URL env var.
"""
import psycopg2
import psycopg2.extras
import os

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    """Return a Postgres connection with dict-like row access."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id      SERIAL PRIMARY KEY,
            full_name       TEXT NOT NULL,
            registration_no TEXT NOT NULL,
            email           TEXT NOT NULL UNIQUE,
            course          TEXT,
            year_of_study   TEXT,
            password        TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            task_id           SERIAL PRIMARY KEY,
            student_id        INTEGER NOT NULL REFERENCES students(student_id),
            task_title        TEXT NOT NULL,
            task_description  TEXT,
            due_date          TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'Pending'
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
