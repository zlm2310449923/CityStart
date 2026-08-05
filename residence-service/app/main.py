from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import connection, init_db
from .models import DocumentCreate, PermitApplicationCreate, ResidenceRegistrationCreate, StatusUpdate


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def row_or_404(row, message: str):
    if row is None:
        raise HTTPException(status_code=404, detail=message)
    return dict(row)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CityStart Residence Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_ERROR"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail), "details": []}})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "The request is invalid.", "details": exc.errors()}})


@app.get("/health")
def health():
    return {"service": "residence-service", "status": "ok"}


@app.post("/residence-registrations", status_code=201)
def create_registration(payload: ResidenceRegistrationCreate):
    registration_id, timestamp = str(uuid4()), now()
    try:
        with connection() as conn:
            conn.execute(
                "INSERT INTO residence_registrations VALUES (?, ?, ?, ?, ?, ?, ?)",
                (registration_id, payload.citizen_id, payload.residential_address,
                 payload.residence_start_date.isoformat(), "approved", timestamp, timestamp),
            )
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(409, "Residence registration already exists") from exc
        raise
    return get_registration(payload.citizen_id)


@app.get("/residence-registrations/{citizen_id}")
def get_registration(citizen_id: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM residence_registrations WHERE citizen_id = ?", (citizen_id,)
        ).fetchone()
    return row_or_404(row, "Residence registration not found")


@app.get("/citizens/{citizen_id}/residence-status")
def residence_status(citizen_id: str):
    with connection() as conn:
        registration = conn.execute(
            "SELECT * FROM residence_registrations WHERE citizen_id = ?", (citizen_id,)
        ).fetchone()
        applications = conn.execute(
            "SELECT * FROM permit_applications WHERE citizen_id = ? ORDER BY submitted_at DESC",
            (citizen_id,),
        ).fetchall()
    return {
        "citizen_id": citizen_id,
        "residence_registered": registration is not None,
        "residence_permit_approved": any(row["status"] == "approved" for row in applications),
        "registration": dict(registration) if registration else None,
        "permit_applications": [dict(row) for row in applications],
    }


@app.post("/residence-permit-applications", status_code=201)
def create_permit_application(payload: PermitApplicationCreate):
    application_id, timestamp = str(uuid4()), now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO permit_applications VALUES (?, ?, ?, ?, ?)",
            (application_id, payload.citizen_id, "pending", timestamp, timestamp),
        )
    return get_permit_application(application_id)


@app.get("/residence-permit-applications/{application_id}")
def get_permit_application(application_id: str):
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM permit_applications WHERE application_id = ?", (application_id,)
        ).fetchone()
        documents = conn.execute(
            "SELECT * FROM application_documents WHERE application_id = ? ORDER BY uploaded_at",
            (application_id,),
        ).fetchall()
    result = row_or_404(row, "Residence permit application not found")
    result["documents"] = [dict(item) for item in documents]
    return result


@app.post("/residence-permit-applications/{application_id}/documents", status_code=201)
def add_document(application_id: str, payload: DocumentCreate):
    get_permit_application(application_id)
    document_id, timestamp = str(uuid4()), now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO application_documents VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, application_id, payload.document_type, payload.file_name, "pending", timestamp),
        )
    return {"document_id": document_id, "application_id": application_id, **payload.model_dump(),
            "verification_status": "pending", "uploaded_at": timestamp}


@app.patch("/residence-permit-applications/{application_id}/status")
def update_status(application_id: str, payload: StatusUpdate):
    get_permit_application(application_id)
    with connection() as conn:
        conn.execute(
            "UPDATE permit_applications SET status = ?, updated_at = ? WHERE application_id = ?",
            (payload.status, now(), application_id),
        )
    return get_permit_application(application_id)
