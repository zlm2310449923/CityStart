from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import connection, init_db
from .models import DocumentCreate, EligibilityCheck, HousingApplicationCreate, StatusUpdate


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def row_or_404(row, message: str):
    if row is None:
        raise HTTPException(404, message)
    result = dict(row)
    for key in ("currently_renting", "owns_local_property"):
        if key in result:
            result[key] = bool(result[key])
    return result


def assess(payload: EligibilityCheck) -> tuple[str, list[str]]:
    reasons = []
    if not payload.employment_registered:
        reasons.append("employment_registration_required")
    if payload.monthly_household_income > payload.income_threshold:
        reasons.append("income_above_threshold")
    if not payload.currently_renting:
        reasons.append("not_currently_renting")
    if payload.owns_local_property:
        reasons.append("owns_local_property")
    return ("eligible" if not reasons else "not_eligible", reasons)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CityStart Housing Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_ERROR"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail), "details": []}})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "The request is invalid.", "details": exc.errors()}})


@app.get("/health")
def health():
    return {"service": "housing-service", "status": "ok"}


@app.post("/housing-subsidy-applications", status_code=201)
def create_application(payload: HousingApplicationCreate):
    application_id, timestamp = str(uuid4()), now()
    eligibility = "not_assessed"
    with connection() as conn:
        conn.execute(
            "INSERT INTO subsidy_applications VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (application_id, payload.citizen_id, payload.monthly_household_income,
             int(payload.currently_renting), int(payload.owns_local_property), "pending",
             eligibility, timestamp, timestamp),
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
    result = row_or_404(row, "Housing subsidy application not found")
    result["documents"] = [dict(item) for item in documents]
    return result


@app.post("/housing-subsidy-applications/{application_id}/documents", status_code=201)
def add_document(application_id: str, payload: DocumentCreate):
    get_application(application_id)
    document_id, timestamp = str(uuid4()), now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO application_documents VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, application_id, payload.document_type, payload.file_name, "pending", timestamp),
        )
    return {"document_id": document_id, "application_id": application_id, **payload.model_dump(),
            "verification_status": "pending", "uploaded_at": timestamp}


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
        "applications": applications,
    }


@app.post("/housing-eligibility/check")
def check_eligibility(payload: EligibilityCheck):
    result, reasons = assess(payload)
    return {"citizen_id": payload.citizen_id, "eligibility_result": result, "reasons": reasons}


@app.patch("/housing-subsidy-applications/{application_id}/status")
def update_status(application_id: str, payload: StatusUpdate):
    get_application(application_id)
    with connection() as conn:
        conn.execute(
            "UPDATE subsidy_applications SET status = ?, updated_at = ? WHERE application_id = ?",
            (payload.status, now(), application_id),
        )
    return get_application(application_id)
