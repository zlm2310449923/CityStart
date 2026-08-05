from fastapi.testclient import TestClient

from app.main import app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "employment.db"))
    return TestClient(app)


def test_empty_employment_status(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.get("/citizens/C1/employment-status")
    assert response.json()["employment_registered"] is False


def test_create_employment_registration(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.post("/employment-registrations", json={
            "citizen_id": "C2", "employer_name": "Example Co", "employment_type": "full_time",
            "employment_start_date": "2026-01-01"
        })
    assert response.status_code == 201
    assert response.json()["status"] == "verified"


def test_support_requires_registration(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.post("/employment-support-applications", json={
            "citizen_id": "C3", "support_type": "training"
        })
    assert response.json()["eligibility_result"] == "registration_required"


def test_update_support_status(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        created = api.post("/employment-support-applications", json={
            "citizen_id": "C4", "support_type": "training"
        }).json()
        response = api.patch(
            f"/employment-support-applications/{created['application_id']}/status",
            json={"status": "under_review"},
        )
    assert response.json()["status"] == "under_review"

