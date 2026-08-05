import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def database_path() -> str:
    path = os.getenv("DATABASE_PATH", "data/housing.db")
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
            CREATE TABLE IF NOT EXISTS subsidy_applications (
                application_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                monthly_household_income REAL NOT NULL,
                currently_renting INTEGER NOT NULL,
                owns_local_property INTEGER NOT NULL,
                status TEXT NOT NULL,
                eligibility_result TEXT NOT NULL,
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
                FOREIGN KEY(application_id) REFERENCES subsidy_applications(application_id)
            );
            """
        )

