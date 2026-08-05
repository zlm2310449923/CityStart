from fastapi.testclient import TestClient

from app.main import app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "housing.db"))
    return TestClient(app)


def test_eligible_profile(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.post("/housing-eligibility/check", json={
            "citizen_id": "C1", "employment_registered": True, "monthly_household_income": 3000,
            "currently_renting": True, "owns_local_property": False
        })
    assert response.json()["eligibility_result"] == "eligible"


def test_property_owner_is_not_eligible(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.post("/housing-eligibility/check", json={
            "citizen_id": "C2", "employment_registered": True, "monthly_household_income": 3000,
            "currently_renting": True, "owns_local_property": True
        })
    assert "owns_local_property" in response.json()["reasons"]


def test_create_application_and_add_document(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        created = api.post("/housing-subsidy-applications", json={
            "citizen_id": "C3", "monthly_household_income": 3000,
            "currently_renting": True, "owns_local_property": False
        }).json()
        response = api.post(f"/housing-subsidy-applications/{created['application_id']}/documents", json={
            "document_type": "rental_contract", "file_name": "contract.pdf"
        })
    assert response.status_code == 201


def test_housing_status_reflects_latest_application(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        api.post("/housing-subsidy-applications", json={
            "citizen_id": "C4", "monthly_household_income": 3000,
            "currently_renting": True, "owns_local_property": False
        })
        response = api.get("/citizens/C4/housing-status")
    assert response.json()["currently_renting"] is True
    assert len(response.json()["applications"]) == 1

