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
    conn = sqlite3.connect(database_path(), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_missing_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = _columns(conn, table)
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS residence_registrations (
                registration_id TEXT PRIMARY KEY NOT NULL,
                citizen_id TEXT NOT NULL,
                residential_address TEXT NOT NULL,
                residence_start_date TEXT NOT NULL,
                contact_phone TEXT,
                status TEXT NOT NULL DEFAULT 'approved',
                cancel_reason TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS permit_applications (
                application_id TEXT PRIMARY KEY NOT NULL,
                citizen_id TEXT NOT NULL,
                registration_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                application_reason TEXT,
                eligibility_reason TEXT,
                is_express INTEGER NOT NULL DEFAULT 0,
                reviewer_id TEXT,
                reviewer_comment TEXT,
                submitted_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (registration_id) REFERENCES residence_registrations(registration_id)
            );
            CREATE TABLE IF NOT EXISTS application_documents (
                document_id TEXT PRIMARY KEY NOT NULL,
                application_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                verification_status TEXT NOT NULL DEFAULT 'pending',
                verification_comment TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (application_id) REFERENCES permit_applications(application_id)
            );
            """
        )
        _add_missing_columns(conn, "residence_registrations", {
            "contact_phone": "TEXT",
            "cancel_reason": "TEXT",
            "is_deleted": "INTEGER NOT NULL DEFAULT 0",
        })
        _add_missing_columns(conn, "permit_applications", {
            "registration_id": "TEXT",
            "application_reason": "TEXT",
            "eligibility_reason": "TEXT",
            "is_express": "INTEGER NOT NULL DEFAULT 0",
            "reviewer_id": "TEXT",
            "reviewer_comment": "TEXT",
        })
        _add_missing_columns(conn, "application_documents", {
            "verification_comment": "TEXT",
            "is_deleted": "INTEGER NOT NULL DEFAULT 0",
        })
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL,
                from_status TEXT NOT NULL,
                to_status TEXT NOT NULL,
                changed_by TEXT,
                comment TEXT,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (application_id) REFERENCES permit_applications(application_id)
            );
            CREATE TABLE IF NOT EXISTS residence_permits (
                permit_id TEXT PRIMARY KEY NOT NULL,
                application_id TEXT NOT NULL UNIQUE,
                citizen_id TEXT NOT NULL,
                permit_type TEXT NOT NULL DEFAULT 'physical',
                status TEXT NOT NULL DEFAULT 'issued',
                issued_at TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                is_e_permit_active INTEGER NOT NULL DEFAULT 0,
                e_permit_id TEXT,
                e_permit_activated_at TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (application_id) REFERENCES permit_applications(application_id)
            );
            CREATE TABLE IF NOT EXISTS permit_endorsements (
                endorsement_id TEXT PRIMARY KEY NOT NULL,
                permit_id TEXT NOT NULL,
                endorsement_date TEXT NOT NULL,
                previous_expiry TEXT NOT NULL,
                new_expiry TEXT NOT NULL,
                is_overdue INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (permit_id) REFERENCES residence_permits(permit_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_registration_citizen_active
                ON residence_registrations(citizen_id) WHERE is_deleted = 0;
            CREATE INDEX IF NOT EXISTS idx_permit_app_citizen ON permit_applications(citizen_id);
            CREATE INDEX IF NOT EXISTS idx_permit_app_status ON permit_applications(status);
            CREATE INDEX IF NOT EXISTS idx_permit_app_registration ON permit_applications(registration_id);
            CREATE INDEX IF NOT EXISTS idx_document_application ON application_documents(application_id);
            CREATE INDEX IF NOT EXISTS idx_document_type ON application_documents(document_type);
            CREATE INDEX IF NOT EXISTS idx_status_history_app ON status_history(application_id);
            CREATE INDEX IF NOT EXISTS idx_status_history_time ON status_history(changed_at);
            CREATE INDEX IF NOT EXISTS idx_permit_citizen ON residence_permits(citizen_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_permit_application ON residence_permits(application_id);
            CREATE INDEX IF NOT EXISTS idx_endorsement_permit ON permit_endorsements(permit_id);
            """
        )

