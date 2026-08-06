import sqlite3

from app.db import connection, init_db


def test_migrates_original_three_table_schema(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        """
        CREATE TABLE residence_registrations (
            registration_id TEXT PRIMARY KEY,
            citizen_id TEXT NOT NULL UNIQUE,
            residential_address TEXT NOT NULL,
            residence_start_date TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE permit_applications (
            application_id TEXT PRIMARY KEY,
            citizen_id TEXT NOT NULL,
            status TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE application_documents (
            document_id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        );
        """
    )
    legacy.close()
    monkeypatch.setenv("DATABASE_PATH", str(path))

    init_db()

    with connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        registration_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(residence_registrations)").fetchall()
        }
    assert {"status_history", "residence_permits", "permit_endorsements"} <= tables
    assert {"contact_phone", "cancel_reason", "is_deleted"} <= registration_columns

