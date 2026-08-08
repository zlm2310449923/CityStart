from fastapi.testclient import TestClient

from app.main import app


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "housing.db"))
    return TestClient(app)


def complete_documents():
    return ["identity_document", "rental_contract", "employment_evidence", "housing_status_statement"]


def test_eligible_profile_with_complete_documents(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.post("/housing-eligibility/check", json={
            "citizen_id": "C1",
            "employment_registered": True,
            "monthly_household_income": 3000,
            "currently_renting": True,
            "owns_local_property": False,
            "available_documents": complete_documents(),
        })
    body = response.json()
    assert body["eligibility_result"] == "eligible"
    assert body["missing_requirements"] == []


def test_property_owner_is_not_eligible(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.post("/housing-eligibility/check", json={
            "citizen_id": "C2",
            "employment_registered": True,
            "monthly_household_income": 3000,
            "currently_renting": True,
            "owns_local_property": True,
            "available_documents": complete_documents(),
        })
    assert response.json()["eligibility_result"] == "not_eligible"
    assert "owns_local_property" in response.json()["reasons"]


def test_missing_documents_returns_conditional_result(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        response = api.post("/housing-eligibility/check", json={
            "citizen_id": "C_DOC",
            "employment_registered": True,
            "monthly_household_income": 2800,
            "currently_renting": True,
            "owns_local_property": False,
            "available_documents": ["identity_document"],
        })
    body = response.json()
    assert body["eligibility_result"] == "conditionally_eligible_missing_documents"
    assert "rental_contract" in body["missing_requirements"]


def test_create_application_and_add_document(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        created = api.post("/housing-subsidy-applications", json={
            "citizen_id": "C3",
            "monthly_household_income": 3000,
            "currently_renting": True,
            "owns_local_property": False,
            "employment_registered": True,
            "available_documents": ["identity_document"],
        }).json()
        response = api.post(f"/housing-subsidy-applications/{created['application_id']}/documents", json={
            "document_type": "rental_contract", "file_name": "contract.pdf"
        })
    assert response.status_code == 201
    assert "employment_evidence" in response.json()["remaining_missing_requirements"]


def test_housing_status_reflects_latest_application(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        api.post("/housing-subsidy-applications", json={
            "citizen_id": "C4",
            "monthly_household_income": 3000,
            "currently_renting": True,
            "owns_local_property": False,
            "employment_registered": True,
            "available_documents": complete_documents(),
        })
        response = api.get("/citizens/C4/housing-status")
    assert response.json()["currently_renting"] is True
    assert response.json()["employment_registered"] is True
    assert len(response.json()["applications"]) == 1


def test_parallel_verification_passes_and_moves_to_review(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        created = api.post("/housing-subsidy-applications", json={
            "citizen_id": "C5",
            "monthly_household_income": 3000,
            "currently_renting": True,
            "owns_local_property": False,
            "employment_registered": True,
            "available_documents": complete_documents(),
        }).json()
        response = api.post(f"/housing-subsidy-applications/{created['application_id']}/verification", json={
            "employment_verified": True,
            "housing_verified": True,
            "documents_complete": True,
            "remarks": "Parallel checks passed"
        })
    body = response.json()
    assert body["status"] == "under_review"
    assert body["eligibility_result"] == "eligible"
    assert body["decision_reason"] == "parallel_verification_passed"


def test_verification_failure_returns_verification_failed(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        created = api.post("/housing-subsidy-applications", json={
            "citizen_id": "C6",
            "monthly_household_income": 3000,
            "currently_renting": True,
            "owns_local_property": False,
            "employment_registered": True,
            "available_documents": complete_documents(),
        }).json()
        response = api.post(f"/housing-subsidy-applications/{created['application_id']}/verification", json={
            "employment_verified": False,
            "housing_verified": True,
            "documents_complete": True
        })
    body = response.json()
    assert body["status"] == "verification_failed"
    assert body["decision_reason"] == "employment_verification_failed"


def test_update_status_can_approve_application(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as api:
        created = api.post("/housing-subsidy-applications", json={
            "citizen_id": "C7",
            "monthly_household_income": 3000,
            "currently_renting": True,
            "owns_local_property": False,
            "employment_registered": True,
            "available_documents": complete_documents(),
        }).json()
        response = api.patch(f"/housing-subsidy-applications/{created['application_id']}/status", json={
            "status": "approved", "decision_reason": "approved_after_final_review"
        })
    assert response.json()["status"] == "approved"
    assert response.json()["decision_reason"] == "approved_after_final_review"
