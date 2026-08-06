from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "service-matching-service",
        "status": "ok",
    }


def test_gateway_payload_is_accepted():
    response = client.post(
        "/recommendations",
        json={
            "citizen_id": "C2001",
            "residence_registered": True,
            "residence_permit_approved": False,
            "employment_registered": False,
            "currently_renting": True,
            "owns_local_property": False,
            "available_documents": [],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["citizen_id"] == "C2001"
    assert body["recommended_order"][0].startswith("S2")
    assert (
        "employment_registration_record"
        in body["missing_requirements"]
    )


def test_validation_error_uses_common_format():
    response = client.post(
        "/recommendations",
        json={"citizen_id": "   "},
    )

    assert response.status_code == 422

    body = response.json()

    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert (
        body["error"]["message"]
        == "The request body is invalid."
    )
    assert isinstance(body["error"]["details"], list)
