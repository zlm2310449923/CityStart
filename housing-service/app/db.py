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


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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
                employment_registered INTEGER NOT NULL DEFAULT 0,
                district TEXT,
                rental_contract_id TEXT,
                available_documents TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                eligibility_result TEXT NOT NULL,
                eligibility_reasons TEXT NOT NULL DEFAULT '',
                missing_requirements TEXT NOT NULL DEFAULT '',
                decision_reason TEXT,
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
            CREATE TABLE IF NOT EXISTS verification_records (
                verification_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                employment_verified INTEGER NOT NULL,
                housing_verified INTEGER NOT NULL,
                documents_complete INTEGER NOT NULL,
                verifier TEXT NOT NULL,
                remarks TEXT,
                verified_at TEXT NOT NULL,
                FOREIGN KEY(application_id) REFERENCES subsidy_applications(application_id)
            );
            """
        )
        # Backward-compatible migrations for repositories with an older local housing.db.
        _add_column_if_missing(conn, "subsidy_applications", "employment_registered", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "subsidy_applications", "district", "TEXT")
        _add_column_if_missing(conn, "subsidy_applications", "rental_contract_id", "TEXT")
        _add_column_if_missing(conn, "subsidy_applications", "available_documents", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "subsidy_applications", "eligibility_reasons", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "subsidy_applications", "missing_requirements", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "subsidy_applications", "decision_reason", "TEXT")
