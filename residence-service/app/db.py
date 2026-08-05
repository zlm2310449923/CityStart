import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def database_path() -> str:
    path = os.getenv("DATABASE_PATH", "data/residence.db")
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
            CREATE TABLE IF NOT EXISTS residence_registrations (
                registration_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL UNIQUE,
                residential_address TEXT NOT NULL,
                residence_start_date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS permit_applications (
                application_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                status TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS application_documents (
                document_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY(application_id) REFERENCES permit_applications(application_id)
            );
            """
        )

