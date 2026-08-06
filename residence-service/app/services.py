import sqlite3
from datetime import date
from uuid import uuid4

from .constants import ALLOWED_STATUS_TRANSITIONS, UPLOADABLE_APPLICATION_STATUSES
from .db import connection
from .errors import AppError, not_found
from .models import (
    DocumentCreate,
    EndorsementCreate,
    PermitApplicationCreate,
    RegistrationCancel,
    ResidenceRegistrationCreate,
    ResidenceRegistrationUpdate,
    StatusUpdate,
)
from .rules import (
    add_one_year,
    check_document_completeness,
    check_eligibility,
    iso_datetime,
    next_business_day,
    parse_datetime,
    registration_days,
    utc_now,
)


def _active_registration(conn: sqlite3.Connection, citizen_id: str):
    return conn.execute(
        "SELECT * FROM residence_registrations WHERE citizen_id = ? AND is_deleted = 0",
        (citizen_id,),
    ).fetchone()


def _registration_payload(row) -> dict:
    result = dict(row)
    result["registration_days"] = registration_days(result["residence_start_date"])
    result["is_deleted"] = bool(result["is_deleted"])
    return result


def _document_payload(row) -> dict:
    result = dict(row)
    result["is_deleted"] = bool(result["is_deleted"])
    return result


def _permit_payload(row) -> dict:
    result = dict(row)
    result["is_e_permit_active"] = bool(result["is_e_permit_active"])
    result["is_deleted"] = bool(result["is_deleted"])
    return result


def _history_payload(row) -> dict:
    result = dict(row)
    return {
        **result,
        "status": result["to_status"],
        "timestamp": result["changed_at"],
        "reviewer_id": result["changed_by"],
    }


def _insert_history(
    conn: sqlite3.Connection,
    application_id: str,
    from_status: str,
    to_status: str,
    *,
    changed_by: str | None = None,
    comment: str | None = None,
    changed_at: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO status_history
           (application_id, from_status, to_status, changed_by, comment, changed_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (application_id, from_status, to_status, changed_by, comment, changed_at or iso_datetime()),
    )


def _application_payload(conn: sqlite3.Connection, row) -> dict:
    if row is None:
        raise not_found("居住证申请")
    result = dict(row)
    result["is_express"] = bool(result["is_express"])
    documents = conn.execute(
        """SELECT * FROM application_documents
           WHERE application_id = ? AND is_deleted = 0 ORDER BY uploaded_at""",
        (result["application_id"],),
    ).fetchall()
    history = conn.execute(
        "SELECT * FROM status_history WHERE application_id = ? ORDER BY id",
        (result["application_id"],),
    ).fetchall()
    permit = conn.execute(
        "SELECT * FROM residence_permits WHERE application_id = ? AND is_deleted = 0",
        (result["application_id"],),
    ).fetchone()
    result["documents"] = [_document_payload(item) for item in documents]
    result["status_history"] = [_history_payload(item) for item in history]
    result["permit"] = _permit_payload(permit) if permit else None
    return result


def create_registration(payload: ResidenceRegistrationCreate) -> dict:
    if payload.residence_start_date > date.today():
        raise AppError(422, "VALIDATION_ERROR", "居住起始日期不能晚于今天")
    registration_id, timestamp = str(uuid4()), iso_datetime()
    try:
        with connection() as conn:
            if _active_registration(conn, payload.citizen_id):
                raise AppError(409, "DUPLICATE_REGISTRATION", "该公民已存在有效的居住登记")
            conn.execute(
                """INSERT INTO residence_registrations
                   (registration_id, citizen_id, residential_address, residence_start_date,
                    contact_phone, status, cancel_reason, is_deleted, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'approved', NULL, 0, ?, ?)""",
                (registration_id, payload.citizen_id, payload.residential_address,
                 payload.residence_start_date.isoformat(), payload.contact_phone, timestamp, timestamp),
            )
    except sqlite3.IntegrityError as exc:
        raise AppError(409, "DUPLICATE_REGISTRATION", "该公民已存在有效的居住登记") from exc
    return get_registration(payload.citizen_id)


def get_registration(citizen_id: str) -> dict:
    with connection() as conn:
        row = _active_registration(conn, citizen_id)
    if row is None:
        raise not_found("居住登记")
    return _registration_payload(row)


def update_registration(citizen_id: str, payload: ResidenceRegistrationUpdate) -> dict:
    changes = payload.model_dump(exclude_none=True)
    with connection() as conn:
        row = _active_registration(conn, citizen_id)
        if row is None:
            raise not_found("居住登记")
        assignments = ", ".join(f"{field} = ?" for field in changes)
        conn.execute(
            f"UPDATE residence_registrations SET {assignments}, updated_at = ? WHERE registration_id = ?",
            (*changes.values(), iso_datetime(), row["registration_id"]),
        )
    return get_registration(citizen_id)


def cancel_registration(citizen_id: str, payload: RegistrationCancel) -> dict:
    timestamp = iso_datetime()
    with connection() as conn:
        row = _active_registration(conn, citizen_id)
        if row is None:
            raise not_found("居住登记")
        conn.execute(
            """UPDATE residence_registrations
               SET status = 'cancelled', cancel_reason = ?, is_deleted = 1, updated_at = ?
               WHERE registration_id = ?""",
            (payload.cancel_reason, timestamp, row["registration_id"]),
        )
        active = conn.execute(
            """SELECT application_id, status FROM permit_applications
               WHERE citizen_id = ? AND status IN
               ('pending', 'under_review', 'additional_documents_required', 'verification')""",
            (citizen_id,),
        ).fetchall()
        for application in active:
            conn.execute(
                """UPDATE permit_applications
                   SET status = 'rejected', reviewer_comment = ?, updated_at = ?
                   WHERE application_id = ?""",
                ("关联居住登记已注销", timestamp, application["application_id"]),
            )
            _insert_history(
                conn,
                application["application_id"],
                application["status"],
                "rejected",
                comment="关联居住登记已注销",
                changed_at=timestamp,
            )
        cancelled = conn.execute(
            "SELECT * FROM residence_registrations WHERE registration_id = ?", (row["registration_id"],)
        ).fetchone()
    return _registration_payload(cancelled)


def _payload_eligibility(payload: PermitApplicationCreate, days: int) -> dict:
    return check_eligibility(
        days,
        has_social_security_6m=payload.has_social_security_6m,
        is_enrolled_6m=payload.is_enrolled_6m,
        is_employed_6m=payload.is_employed_6m,
        is_married_to_local_6m=payload.is_married_to_local_6m,
    )


def create_permit_application(payload: PermitApplicationCreate) -> dict:
    timestamp = iso_datetime()
    with connection() as conn:
        registration = _active_registration(conn, payload.citizen_id)
        if registration is None:
            raise not_found("有效居住登记")
        days = registration_days(registration["residence_start_date"])
        eligibility = _payload_eligibility(payload, days)
        if not eligibility["is_eligible"]:
            raise AppError(
                400,
                "NOT_ELIGIBLE",
                f"不满足居住证申领条件：{eligibility['reason']}",
                {
                    "registration_days": days,
                    "requires_days": 183,
                    "shortcut_conditions_met": eligibility["meets_shortcut_conditions"],
                },
            )
        application_id = str(uuid4())
        conn.execute(
            """INSERT INTO permit_applications
               (application_id, citizen_id, registration_id, status, application_reason,
                eligibility_reason, is_express, reviewer_id, reviewer_comment, submitted_at, updated_at)
               VALUES (?, ?, ?, 'pending', ?, ?, ?, NULL, NULL, ?, ?)""",
            (application_id, payload.citizen_id, registration["registration_id"],
             payload.application_reason, eligibility["reason"], int(payload.is_express), timestamp, timestamp),
        )
        _insert_history(conn, application_id, "", "pending", comment="申请已提交", changed_at=timestamp)
        row = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        result = _application_payload(conn, row)
    result["registration_days"] = days
    result["eligibility"] = eligibility
    return result


def get_permit_application(application_id: str) -> dict:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        return _application_payload(conn, row)


def list_permit_applications(citizen_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM permit_applications WHERE citizen_id = ? ORDER BY submitted_at DESC",
            (citizen_id,),
        ).fetchall()
        return [_application_payload(conn, row) for row in rows]


def add_document(application_id: str, payload: DocumentCreate) -> dict:
    timestamp = iso_datetime()
    with connection() as conn:
        application = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        if application is None:
            raise not_found("居住证申请")
        if application["status"] not in UPLOADABLE_APPLICATION_STATUSES:
            raise AppError(
                400,
                "DOCUMENT_UPLOAD_DENIED",
                f"申请状态 {application['status']} 不允许上传材料",
                {"allowed_statuses": sorted(UPLOADABLE_APPLICATION_STATUSES)},
            )
        document_id = str(uuid4())
        conn.execute(
            """INSERT INTO application_documents
               (document_id, application_id, document_type, file_name, verification_status,
                verification_comment, is_deleted, uploaded_at)
               VALUES (?, ?, ?, ?, 'pending', NULL, 0, ?)""",
            (document_id, application_id, payload.document_type, payload.file_name, timestamp),
        )
        new_status = application["status"]
        if application["status"] == "additional_documents_required":
            new_status = "under_review"
            conn.execute(
                "UPDATE permit_applications SET status = ?, updated_at = ? WHERE application_id = ?",
                (new_status, timestamp, application_id),
            )
            _insert_history(
                conn, application_id, "additional_documents_required", "under_review",
                comment="申请人已补充材料", changed_at=timestamp,
            )
        row = conn.execute(
            "SELECT * FROM application_documents WHERE document_id = ?", (document_id,)
        ).fetchone()
    return {**_document_payload(row), "application_status": new_status}


def _document_check(conn: sqlite3.Connection, application) -> dict:
    registration = conn.execute(
        "SELECT * FROM residence_registrations WHERE registration_id = ?",
        (application["registration_id"],),
    ).fetchone()
    days = registration_days(registration["residence_start_date"]) if registration else 0
    documents = conn.execute(
        """SELECT document_type FROM application_documents
           WHERE application_id = ? AND is_deleted = 0 AND verification_status != 'rejected'""",
        (application["application_id"],),
    ).fetchall()
    result = check_document_completeness((row["document_type"] for row in documents), days >= 183)
    return {"application_id": application["application_id"], **result}


def check_documents(application_id: str) -> dict:
    with connection() as conn:
        application = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        if application is None:
            raise not_found("居住证申请")
        return _document_check(conn, application)


def check_application_eligibility(application_id: str) -> dict:
    with connection() as conn:
        application = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        if application is None:
            raise not_found("居住证申请")
        registration = conn.execute(
            "SELECT * FROM residence_registrations WHERE registration_id = ?",
            (application["registration_id"],),
        ).fetchone()
        if registration is None:
            raise not_found("关联居住登记")
        types = {
            row["document_type"]
            for row in conn.execute(
                """SELECT document_type FROM application_documents
                   WHERE application_id = ? AND is_deleted = 0 AND verification_status != 'rejected'""",
                (application_id,),
            ).fetchall()
        }
    result = check_eligibility(
        registration_days(registration["residence_start_date"]),
        has_social_security_6m="social_security_record" in types,
        is_enrolled_6m="enrollment_proof" in types,
        is_employed_6m="employment_proof" in types,
        is_married_to_local_6m="marriage_certificate" in types,
    )
    return {"application_id": application_id, "citizen_id": application["citizen_id"], **result}


def _issue_permit(conn: sqlite3.Connection, application, timestamp: str) -> dict:
    existing = conn.execute(
        "SELECT * FROM residence_permits WHERE application_id = ?", (application["application_id"],)
    ).fetchone()
    if existing:
        return _permit_payload(existing)
    issued_at = parse_datetime(timestamp)
    permit_id = str(uuid4())
    conn.execute(
        """INSERT INTO residence_permits
           (permit_id, application_id, citizen_id, permit_type, status, issued_at, expiry_date,
            is_e_permit_active, e_permit_id, e_permit_activated_at, is_deleted, created_at, updated_at)
           VALUES (?, ?, ?, 'physical', 'issued', ?, ?, 0, NULL, NULL, 0, ?, ?)""",
        (permit_id, application["application_id"], application["citizen_id"], timestamp,
         iso_datetime(add_one_year(issued_at)), timestamp, timestamp),
    )
    return _permit_payload(conn.execute(
        "SELECT * FROM residence_permits WHERE permit_id = ?", (permit_id,)
    ).fetchone())


def update_application_status(application_id: str, payload: StatusUpdate) -> dict:
    timestamp = iso_datetime()
    with connection() as conn:
        application = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        if application is None:
            raise not_found("居住证申请")
        current = application["status"]
        allowed = ALLOWED_STATUS_TRANSITIONS[current]
        if payload.status not in allowed:
            raise AppError(
                400,
                "INVALID_STATUS_TRANSITION",
                f"不允许从 {current} 转换为 {payload.status}",
                {"current_status": current, "allowed_transitions": sorted(allowed)},
            )
        if payload.status == "verification":
            document_check = _document_check(conn, application)
            if not document_check["is_complete"]:
                raise AppError(400, "DOCUMENTS_INCOMPLETE", "申请材料不完整", document_check)
        conn.execute(
            """UPDATE permit_applications
               SET status = ?, reviewer_id = ?, reviewer_comment = ?, updated_at = ?
               WHERE application_id = ?""",
            (payload.status, payload.reviewer_id, payload.reviewer_comment, timestamp, application_id),
        )
        _insert_history(
            conn,
            application_id,
            current,
            payload.status,
            changed_by=payload.reviewer_id,
            comment=payload.reviewer_comment,
            changed_at=timestamp,
        )
        if payload.status == "approved":
            _issue_permit(conn, application, timestamp)
        updated = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        result = _application_payload(conn, updated)
    result["previous_status"] = current
    return result


def residence_status(citizen_id: str) -> dict:
    with connection() as conn:
        registration = _active_registration(conn, citizen_id)
        applications = conn.execute(
            "SELECT * FROM permit_applications WHERE citizen_id = ? ORDER BY submitted_at DESC",
            (citizen_id,),
        ).fetchall()
        permit = conn.execute(
            """SELECT * FROM residence_permits
               WHERE citizen_id = ? AND is_deleted = 0 ORDER BY issued_at DESC LIMIT 1""",
            (citizen_id,),
        ).fetchone()
        application_payloads = [_application_payload(conn, row) for row in applications]
    current_permit = _permit_payload(permit) if permit else None
    return {
        "citizen_id": citizen_id,
        "residence_registered": registration is not None,
        "residence_permit_approved": any(row["status"] == "approved" for row in applications),
        "registration": _registration_payload(registration) if registration else None,
        "permit_applications": application_payloads,
        "current_permit": current_permit,
    }


def _get_permit(conn: sqlite3.Connection, permit_id: str):
    permit = conn.execute(
        "SELECT * FROM residence_permits WHERE permit_id = ? AND is_deleted = 0", (permit_id,)
    ).fetchone()
    if permit is None:
        raise not_found("居住证")
    return permit


def endorse_permit(permit_id: str, payload: EndorsementCreate) -> dict:
    current = utc_now()
    timestamp = iso_datetime(current)
    with connection() as conn:
        permit = _get_permit(conn, permit_id)
        if permit["status"] not in {"issued", "expired"}:
            raise AppError(400, "ENDORSEMENT_NOT_DUE", f"状态 {permit['status']} 不允许签注")
        expiry = parse_datetime(permit["expiry_date"])
        days_until_expiry = (expiry.date() - current.date()).days
        if days_until_expiry > 30:
            raise AppError(
                400, "ENDORSEMENT_NOT_DUE", "尚未到签注时间窗口",
                {"days_until_expiry": days_until_expiry, "window_days": 30},
            )
        overdue = days_until_expiry <= 0
        base = current if overdue else expiry
        new_expiry = add_one_year(base)
        endorsement_id = str(uuid4())
        conn.execute(
            """INSERT INTO permit_endorsements
               (endorsement_id, permit_id, endorsement_date, previous_expiry, new_expiry,
                is_overdue, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (endorsement_id, permit_id, timestamp, permit["expiry_date"],
             iso_datetime(new_expiry), int(overdue), timestamp),
        )
        conn.execute(
            "UPDATE residence_permits SET status = 'issued', expiry_date = ?, updated_at = ? WHERE permit_id = ?",
            (iso_datetime(new_expiry), timestamp, permit_id),
        )
        registration = _active_registration(conn, permit["citizen_id"])
        if registration and registration["residential_address"] != payload.current_address:
            conn.execute(
                "UPDATE residence_registrations SET residential_address = ?, updated_at = ? WHERE registration_id = ?",
                (payload.current_address, timestamp, registration["registration_id"]),
            )
        updated = _get_permit(conn, permit_id)
        endorsement = conn.execute(
            "SELECT * FROM permit_endorsements WHERE endorsement_id = ?", (endorsement_id,)
        ).fetchone()
    return {"permit": _permit_payload(updated), "endorsement": {**dict(endorsement), "is_overdue": bool(endorsement["is_overdue"])}}


def report_loss(permit_id: str) -> dict:
    timestamp = iso_datetime()
    with connection() as conn:
        permit = _get_permit(conn, permit_id)
        if permit["status"] != "issued":
            raise AppError(400, "INVALID_PERMIT_STATUS", f"状态 {permit['status']} 不允许挂失")
        conn.execute(
            "UPDATE residence_permits SET status = 'lost', updated_at = ? WHERE permit_id = ?",
            (timestamp, permit_id),
        )
        updated = _get_permit(conn, permit_id)
    return _permit_payload(updated)


def apply_reissue(permit_id: str) -> dict:
    timestamp = iso_datetime()
    with connection() as conn:
        permit = _get_permit(conn, permit_id)
        if permit["status"] != "lost":
            raise AppError(400, "INVALID_PERMIT_STATUS", "只有已挂失的居住证可以申请补领")
        registration = _active_registration(conn, permit["citizen_id"])
        if registration is None:
            raise not_found("有效居住登记")
        application_id = str(uuid4())
        conn.execute(
            """INSERT INTO permit_applications
               (application_id, citizen_id, registration_id, status, application_reason,
                eligibility_reason, is_express, reviewer_id, reviewer_comment, submitted_at, updated_at)
               VALUES (?, ?, ?, 'pending', ?, ?, 0, NULL, NULL, ?, ?)""",
            (application_id, permit["citizen_id"], registration["registration_id"],
             f"补领居住证（原证 {permit_id}）", "原有效居住证已挂失", timestamp, timestamp),
        )
        _insert_history(conn, application_id, "", "pending", comment="居住证补领申请已提交", changed_at=timestamp)
        application = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        return _application_payload(conn, application)


def activate_e_permit(permit_id: str) -> dict:
    current = utc_now()
    timestamp = iso_datetime(current)
    with connection() as conn:
        permit = _get_permit(conn, permit_id)
        if permit["status"] != "issued":
            raise AppError(400, "E_PERMIT_NOT_READY", "实体居住证当前不是有效状态")
        if permit["is_e_permit_active"]:
            return _permit_payload(permit)
        ready_at = next_business_day(parse_datetime(permit["issued_at"]))
        if current < ready_at:
            wait_seconds = max(0, int((ready_at - current).total_seconds()))
            raise AppError(
                400, "E_PERMIT_NOT_READY", "实体居住证签发满1个工作日后方可申领电子证",
                {"ready_at": iso_datetime(ready_at), "wait_seconds": wait_seconds},
            )
        e_permit_id = str(uuid4())
        conn.execute(
            """UPDATE residence_permits
               SET is_e_permit_active = 1, e_permit_id = ?, e_permit_activated_at = ?, updated_at = ?
               WHERE permit_id = ?""",
            (e_permit_id, timestamp, timestamp, permit_id),
        )
        updated = _get_permit(conn, permit_id)
    return _permit_payload(updated)

