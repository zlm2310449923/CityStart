from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "residence.db"))
    with TestClient(app) as client:
        yield client


@pytest.fixture
def registered_citizen(api):
    citizen_id = "C-REGISTERED"
    response = api.post("/residence-registrations", json={
        "citizen_id": citizen_id,
        "residential_address": "武汉市洪山区测试路1号",
        "residence_start_date": (date.today() - timedelta(days=200)).isoformat(),
        "contact_phone": "13800138000",
    })
    assert response.status_code == 201
    return citizen_id


def create_application(api, citizen_id: str) -> dict:
    response = api.post("/residence-permit-applications", json={
        "citizen_id": citizen_id,
        "application_reason": "就业需要",
    })
    assert response.status_code == 201, response.text
    return response.json()


def upload_required_documents(api, application_id: str) -> None:
    for document_type in ("identity_document", "residence_proof"):
        response = api.post(
            f"/residence-permit-applications/{application_id}/documents",
            json={"document_type": document_type, "file_name": f"{document_type}.pdf"},
        )
        assert response.status_code == 201, response.text


def approve_application(api, application_id: str) -> dict:
    transitions = ("under_review", "verification", "approved")
    result = None
    for status in transitions:
        response = api.patch(
            f"/residence-permit-applications/{application_id}/status",
            json={"status": status, "reviewer_id": "REV-001", "reviewer_comment": "测试审核"},
        )
        assert response.status_code == 200, response.text
        result = response.json()
    return result

