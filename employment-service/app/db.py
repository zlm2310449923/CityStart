import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def database_path() -> str:
    path = os.getenv("DATABASE_PATH", "data/employment.db")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection():
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS employment_registrations (
                registration_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL UNIQUE,
                employer_name TEXT NOT NULL,
                employment_type TEXT NOT NULL,
                employment_start_date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS support_applications (
                application_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                support_type TEXT NOT NULL,
                status TEXT NOT NULL,
                eligibility_result TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

