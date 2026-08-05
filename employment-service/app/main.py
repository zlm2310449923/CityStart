from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import connection, init_db
from .models import EmploymentRegistrationCreate, StatusUpdate, SupportApplicationCreate


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def row_or_404(row, message: str):
    if row is None:
        raise HTTPException(404, message)
    return dict(row)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CityStart Employment Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_ERROR"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail), "details": []}})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "The request is invalid.", "details": exc.errors()}})


@app.get("/health")
def health():
    return {"service": "employment-service", "status": "ok"}


@app.post("/employment-registrations", status_code=201)
def create_registration(payload: EmploymentRegistrationCreate):
    registration_id, timestamp = str(uuid4()), now()
    try:
        with connection() as conn:
            conn.execute(
                "INSERT INTO employment_registrations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (registration_id, payload.citizen_id, payload.employer_name, payload.employment_type,
                 payload.employment_start_date.isoformat(), "verified", timestamp, timestamp),
            )
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(409, "Employment registration already exists") from exc
        raise
    return get_registration(payload.citizen_id)


@app.get("/employment-registrations/{citizen_id}")
def get_registration(citizen_id: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM employment_registrations WHERE citizen_id = ?", (citizen_id,)
        ).fetchone()
    return row_or_404(row, "Employment registration not found")


@app.post("/employment-support-applications", status_code=201)
def create_support_application(payload: SupportApplicationCreate):
    with connection() as conn:
        registration = conn.execute(
            "SELECT 1 FROM employment_registrations WHERE citizen_id = ?", (payload.citizen_id,)
        ).fetchone()
    eligibility = "eligible" if registration else "registration_required"
    application_id, timestamp = str(uuid4()), now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO support_applications VALUES (?, ?, ?, ?, ?, ?, ?)",
            (application_id, payload.citizen_id, payload.support_type, "pending", eligibility,
             timestamp, timestamp),
        )
    return get_support_application(application_id)


@app.get("/employment-support-applications/{application_id}")
def get_support_application(application_id: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM support_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
    return row_or_404(row, "Employment support application not found")


@app.get("/citizens/{citizen_id}/employment-status")
def employment_status(citizen_id: str):
    with connection() as conn:
        registration = conn.execute(
            "SELECT * FROM employment_registrations WHERE citizen_id = ?", (citizen_id,)
        ).fetchone()
        applications = conn.execute(
            "SELECT * FROM support_applications WHERE citizen_id = ? ORDER BY submitted_at DESC",
            (citizen_id,),
        ).fetchall()
    return {
        "citizen_id": citizen_id,
        "employment_registered": registration is not None,
        "registration": dict(registration) if registration else None,
        "support_applications": [dict(row) for row in applications],
    }


@app.patch("/employment-support-applications/{application_id}/status")
def update_status(application_id: str, payload: StatusUpdate):
    get_support_application(application_id)
    with connection() as conn:
        conn.execute(
            "UPDATE support_applications SET status = ?, updated_at = ? WHERE application_id = ?",
            (payload.status, now(), application_id),
        )
    return get_support_application(application_id)
