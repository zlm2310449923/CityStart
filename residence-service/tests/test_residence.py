from datetime import date, datetime, timedelta, timezone

from app.db import connection
from app.rules import iso_datetime
from tests.conftest import approve_application, create_application, upload_required_documents


def test_registration_create_query_update_and_cancel(api):
    citizen_id = "C-REG-FLOW"
    created = api.post("/residence-registrations", json={
        "citizen_id": citizen_id,
        "residential_address": "武汉市江岸区原地址",
        "residence_start_date": (date.today() - timedelta(days=10)).isoformat(),
    })
    assert created.status_code == 201
    assert created.json()["registration_days"] == 10

    updated = api.patch(f"/residence-registrations/{citizen_id}", json={
        "residential_address": "武汉市洪山区新地址",
        "contact_phone": "13900139000",
    })
    assert updated.status_code == 200
    assert updated.json()["residential_address"] == "武汉市洪山区新地址"

    cancelled = api.request(
        "DELETE",
        f"/residence-registrations/{citizen_id}",
        json={"cancel_reason": "已搬离武汉"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert api.get(f"/residence-registrations/{citizen_id}").status_code == 404


def test_duplicate_active_registration(api, registered_citizen):
    response = api.post("/residence-registrations", json={
        "citizen_id": registered_citizen,
        "residential_address": "武汉市重复地址",
        "residence_start_date": date.today().isoformat(),
    })
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_REGISTRATION"


def test_application_requires_registration(api):
    response = api.post("/residence-permit-applications", json={"citizen_id": "C-NOT-REGISTERED"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_application_requires_183_days_or_shortcut(api):
    citizen_id = "C-NEW"
    api.post("/residence-registrations", json={
        "citizen_id": citizen_id,
        "residential_address": "武汉市武昌区测试地址",
        "residence_start_date": (date.today() - timedelta(days=30)).isoformat(),
    })
    denied = api.post("/residence-permit-applications", json={"citizen_id": citizen_id})
    assert denied.status_code == 400
    assert denied.json()["error"]["code"] == "NOT_ELIGIBLE"

    accepted = api.post("/residence-permit-applications", json={
        "citizen_id": citizen_id,
        "is_employed_6m": True,
    })
    assert accepted.status_code == 201
    assert accepted.json()["eligibility"]["meets_shortcut"] is True


def test_document_completeness(api, registered_citizen):
    application = create_application(api, registered_citizen)
    application_id = application["application_id"]
    incomplete = api.post(f"/residence-permit-applications/{application_id}/check-documents")
    assert incomplete.json()["is_complete"] is False

    upload_required_documents(api, application_id)
    complete = api.post(f"/residence-permit-applications/{application_id}/check-documents")
    assert complete.json()["is_complete"] is True


def test_full_approval_flow_creates_permit_and_history(api, registered_citizen):
    application = create_application(api, registered_citizen)
    application_id = application["application_id"]
    upload_required_documents(api, application_id)
    approved = approve_application(api, application_id)

    assert approved["status"] == "approved"
    assert approved["permit"]["status"] == "issued"
    assert [item["to_status"] for item in approved["status_history"]] == [
        "pending", "under_review", "verification", "approved"
    ]

    status = api.get(f"/citizens/{registered_citizen}/residence-status").json()
    assert status["residence_permit_approved"] is True
    assert status["current_permit"]["permit_id"] == approved["permit"]["permit_id"]


def test_invalid_status_transition(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    response = api.patch(
        f"/residence-permit-applications/{application_id}/status",
        json={"status": "approved"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_documents_must_be_complete_before_verification(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    api.patch(f"/residence-permit-applications/{application_id}/status", json={"status": "under_review"})
    response = api.patch(
        f"/residence-permit-applications/{application_id}/status",
        json={"status": "verification"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DOCUMENTS_INCOMPLETE"


def test_additional_documents_return_application_to_review(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    api.patch(f"/residence-permit-applications/{application_id}/status", json={"status": "under_review"})
    api.patch(
        f"/residence-permit-applications/{application_id}/status",
        json={"status": "additional_documents_required"},
    )
    uploaded = api.post(
        f"/residence-permit-applications/{application_id}/documents",
        json={"document_type": "identity_document", "file_name": "identity.pdf"},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["application_status"] == "under_review"


def test_citizen_application_list_and_eligibility(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    eligibility = api.post(
        f"/residence-permit-applications/{application_id}/check-eligibility"
    ).json()
    listing = api.get(f"/citizens/{registered_citizen}/permit-applications").json()
    assert eligibility["is_eligible"] is True
    assert len(listing["permit_applications"]) == 1


def test_report_loss_and_apply_reissue(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    upload_required_documents(api, application_id)
    permit = approve_application(api, application_id)["permit"]

    lost = api.post(f"/residence-permits/{permit['permit_id']}/report-loss")
    assert lost.json()["status"] == "lost"
    reissue = api.post(f"/residence-permits/{permit['permit_id']}/apply-reissue")
    assert reissue.status_code == 201
    assert "补领居住证" in reissue.json()["application_reason"]


def test_endorsement_window(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    upload_required_documents(api, application_id)
    permit = approve_application(api, application_id)["permit"]
    permit_id = permit["permit_id"]

    too_early = api.post(
        f"/residence-permits/{permit_id}/endorsement",
        json={"current_address": "武汉市洪山区签注地址"},
    )
    assert too_early.status_code == 400
    assert too_early.json()["error"]["code"] == "ENDORSEMENT_NOT_DUE"

    near_expiry = datetime.now(timezone.utc) + timedelta(days=20)
    with connection() as conn:
        conn.execute(
            "UPDATE residence_permits SET expiry_date = ? WHERE permit_id = ?",
            (iso_datetime(near_expiry), permit_id),
        )
    endorsed = api.post(
        f"/residence-permits/{permit_id}/endorsement",
        json={"current_address": "武汉市洪山区签注地址"},
    )
    assert endorsed.status_code == 200
    assert endorsed.json()["endorsement"]["is_overdue"] is False


def test_e_permit_waits_one_business_day(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    upload_required_documents(api, application_id)
    permit = approve_application(api, application_id)["permit"]
    permit_id = permit["permit_id"]

    too_early = api.post(f"/residence-permits/{permit_id}/e-permit")
    assert too_early.status_code == 400
    assert too_early.json()["error"]["code"] == "E_PERMIT_NOT_READY"

    issued_at = datetime.now(timezone.utc) - timedelta(days=7)
    with connection() as conn:
        conn.execute(
            "UPDATE residence_permits SET issued_at = ? WHERE permit_id = ?",
            (iso_datetime(issued_at), permit_id),
        )
    activated = api.post(f"/residence-permits/{permit_id}/e-permit")
    assert activated.status_code == 200
    assert activated.json()["is_e_permit_active"] is True
    assert activated.json()["e_permit_id"]


def test_cancel_registration_rejects_active_applications(api, registered_citizen):
    application_id = create_application(api, registered_citizen)["application_id"]
    cancelled = api.request(
        "DELETE",
        f"/residence-registrations/{registered_citizen}",
        json={"cancel_reason": "离开本市"},
    )
    application = api.get(f"/residence-permit-applications/{application_id}")
    assert cancelled.status_code == 200
    assert application.json()["status"] == "rejected"


def test_validation_error_shape(api):
    response = api.post("/residence-registrations", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

