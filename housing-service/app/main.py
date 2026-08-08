from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import connection, init_db
from .models import (
    DocumentCreate,
    EligibilityCheck,
    HousingApplicationCreate,
    REQUIRED_HOUSING_DOCUMENTS,
    StatusUpdate,
    VerificationUpdate,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def encode_list(values: list[str]) -> str:
    return ";".join(sorted({v.strip() for v in values if v and v.strip()}))


def decode_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item for item in value.split(";") if item]


def row_or_404(row, message: str):
    if row is None:
        raise HTTPException(404, message)
    result = dict(row)
    for key in ("currently_renting", "owns_local_property", "employment_registered"):
        if key in result:
            result[key] = bool(result[key])
    for key in ("available_documents", "eligibility_reasons", "missing_requirements"):
        if key in result:
            result[key] = decode_list(result[key])
    return result


def assess(payload: EligibilityCheck) -> tuple[str, list[str], list[str]]:
    reasons = []
    if not payload.employment_registered:
        reasons.append("employment_registration_required")
    if payload.monthly_household_income > payload.income_threshold:
        reasons.append("income_above_threshold")
    if not payload.currently_renting:
        reasons.append("not_currently_renting")
    if payload.owns_local_property:
        reasons.append("owns_local_property")

    available = set(payload.available_documents)
    missing = [doc for doc in REQUIRED_HOUSING_DOCUMENTS if doc not in available]
    if reasons:
        result = "not_eligible"
    elif missing:
        result = "conditionally_eligible_missing_documents"
    else:
        result = "eligible"
    return result, reasons, missing


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CityStart Housing Service", version="0.2.0", lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_ERROR"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail), "details": []}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "The request is invalid.", "details": exc.errors()}},
    )


@app.get("/health")
def health():
    return {"service": "housing-service", "status": "ok"}


@app.post("/housing-subsidy-applications", status_code=201)
def create_application(payload: HousingApplicationCreate):
    application_id, timestamp = str(uuid4()), now()
    check = EligibilityCheck(
        citizen_id=payload.citizen_id,
        employment_registered=payload.employment_registered,
        monthly_household_income=payload.monthly_household_income,
        currently_renting=payload.currently_renting,
        owns_local_property=payload.owns_local_property,
        available_documents=payload.available_documents,
    )
    eligibility, reasons, missing = assess(check)
    status = "pending" if eligibility == "eligible" else "additional_documents_required" if not reasons else "verification_failed"
    decision_reason = payload.remarks or "initial_eligibility_screening"

    with connection() as conn:
        conn.execute(
            """
            INSERT INTO subsidy_applications (
                application_id, citizen_id, monthly_household_income, currently_renting,
                owns_local_property, employment_registered, district, rental_contract_id,
                available_documents, status, eligibility_result, eligibility_reasons,
                missing_requirements, decision_reason, submitted_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id,
                payload.citizen_id,
                payload.monthly_household_income,
                int(payload.currently_renting),
                int(payload.owns_local_property),
                int(payload.employment_registered),
                payload.district,
                payload.rental_contract_id,
                encode_list(payload.available_documents),
                status,
                eligibility,
                encode_list(reasons),
                encode_list(missing),
                decision_reason,
                timestamp,
                timestamp,
            ),
        )
    return get_application(application_id)


@app.get("/housing-subsidy-applications/{application_id}")
def get_application(application_id: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM subsidy_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        documents = conn.execute(
            "SELECT * FROM application_documents WHERE application_id = ? ORDER BY uploaded_at",
            (application_id,),
        ).fetchall()
        verifications = conn.execute(
            "SELECT * FROM verification_records WHERE application_id = ? ORDER BY verified_at",
            (application_id,),
        ).fetchall()
    result = row_or_404(row, "Housing subsidy application not found")
    result["documents"] = [dict(item) for item in documents]
    result["verification_records"] = [dict(item) for item in verifications]
    return result


@app.post("/housing-subsidy-applications/{application_id}/documents", status_code=201)
def add_document(application_id: str, payload: DocumentCreate):
    application = get_application(application_id)
    document_id, timestamp = str(uuid4()), now()
    available_documents = set(application.get("available_documents", []))
    available_documents.add(payload.document_type)
    remaining_missing = [doc for doc in REQUIRED_HOUSING_DOCUMENTS if doc not in available_documents]
    status = application["status"]
    if status == "additional_documents_required" and not remaining_missing and application["eligibility_result"] != "not_eligible":
        status = "pending"
    with connection() as conn:
        conn.execute(
            "INSERT INTO application_documents VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, application_id, payload.document_type, payload.file_name, "pending", timestamp),
        )
        conn.execute(
            """
            UPDATE subsidy_applications
            SET available_documents = ?, missing_requirements = ?, status = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (encode_list(list(available_documents)), encode_list(remaining_missing), status, timestamp, application_id),
        )
    return {
        "document_id": document_id,
        "application_id": application_id,
        **payload.model_dump(),
        "verification_status": "pending",
        "remaining_missing_requirements": remaining_missing,
        "uploaded_at": timestamp,
    }


@app.get("/citizens/{citizen_id}/housing-status")
def housing_status(citizen_id: str):
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM subsidy_applications WHERE citizen_id = ? ORDER BY submitted_at DESC",
            (citizen_id,),
        ).fetchall()
    applications = [row_or_404(row, "") for row in rows]
    latest = applications[0] if applications else None
    return {
        "citizen_id": citizen_id,
        "currently_renting": latest["currently_renting"] if latest else False,
        "owns_local_property": latest["owns_local_property"] if latest else False,
        "employment_registered": latest["employment_registered"] if latest else False,
        "latest_eligibility_result": latest["eligibility_result"] if latest else "not_assessed",
        "applications": applications,
    }


@app.post("/housing-eligibility/check")
def check_eligibility(payload: EligibilityCheck):
    result, reasons, missing = assess(payload)
    return {
        "citizen_id": payload.citizen_id,
        "eligibility_result": result,
        "reasons": reasons,
        "required_documents": REQUIRED_HOUSING_DOCUMENTS,
        "missing_requirements": missing,
    }


@app.post("/housing-subsidy-applications/{application_id}/verification")
def verify_application(application_id: str, payload: VerificationUpdate):
    application = get_application(application_id)
    verification_id, timestamp = str(uuid4()), now()
    if not payload.documents_complete:
        status = "additional_documents_required"
        eligibility = application["eligibility_result"]
        decision_reason = "documents_incomplete"
    elif not payload.employment_verified:
        status = "verification_failed"
        eligibility = "not_eligible"
        decision_reason = "employment_verification_failed"
    elif not payload.housing_verified:
        status = "verification_failed"
        eligibility = "not_eligible"
        decision_reason = "housing_information_verification_failed"
    else:
        status = "under_review"
        eligibility = "eligible"
        decision_reason = "parallel_verification_passed"
    with connection() as conn:
        conn.execute(
            "INSERT INTO verification_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                verification_id,
                application_id,
                int(payload.employment_verified),
                int(payload.housing_verified),
                int(payload.documents_complete),
                payload.verifier,
                payload.remarks,
                timestamp,
            ),
        )
        conn.execute(
            """
            UPDATE subsidy_applications
            SET status = ?, eligibility_result = ?, decision_reason = ?, updated_at = ?
            WHERE application_id = ?
            """,
            (status, eligibility, decision_reason, timestamp, application_id),
        )
    return get_application(application_id)


@app.patch("/housing-subsidy-applications/{application_id}/status")
def update_status(application_id: str, payload: StatusUpdate):
    get_application(application_id)
    with connection() as conn:
        conn.execute(
            """
            UPDATE subsidy_applications
            SET status = ?, decision_reason = COALESCE(?, decision_reason), updated_at = ?
            WHERE application_id = ?
            """,
            (payload.status, payload.decision_reason, now(), application_id),
        )
    return get_application(application_id)
