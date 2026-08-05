from fastapi.testclient import TestClient

from app.main import app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "residence.db"))
    return TestClient(app)


def test_create_and_get_registration(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        created = api.post("/residence-registrations", json={
            "citizen_id": "C1", "residential_address": "Wuhan", "residence_start_date": "2026-01-01"
        })
        fetched = api.get("/residence-registrations/C1")
    assert created.status_code == 201
    assert fetched.json()["status"] == "approved"


def test_missing_registration_uses_unified_error(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.get("/residence-registrations/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_permit_document_and_status_flow(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        application = api.post("/residence-permit-applications", json={"citizen_id": "C2"}).json()
        application_id = application["application_id"]
        document = api.post(f"/residence-permit-applications/{application_id}/documents", json={
            "document_type": "identity_document", "file_name": "identity.pdf"
        })
        updated = api.patch(f"/residence-permit-applications/{application_id}/status", json={"status": "approved"})
    assert document.status_code == 201
    assert updated.json()["status"] == "approved"
    assert len(updated.json()["documents"]) == 1

