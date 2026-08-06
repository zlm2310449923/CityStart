import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import init_db
from .errors import AppError
from .models import (
    DocumentCreate,
    EndorsementCreate,
    PermitApplicationCreate,
    RegistrationCancel,
    ResidenceRegistrationCreate,
    ResidenceRegistrationUpdate,
    StatusUpdate,
)
from . import services


logger = logging.getLogger("residence-service")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="CityStart Residence Service",
    description="S1 居住登记与 S2 居住证申请管理微服务",
    version="1.0.0",
    lifespan=lifespan,
)


def error_response(status_code: int, code: str, message: str, details=None):
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "error": {"code": code, "message": message, "details": [] if details is None else details}
        }),
    )


@app.exception_handler(AppError)
async def application_error(_: Request, exc: AppError):
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_ERROR"
    return error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return error_response(422, "VALIDATION_ERROR", "请求参数校验失败", exc.errors())


@app.exception_handler(Exception)
async def internal_error(_: Request, exc: Exception):
    logger.exception("Unhandled residence-service error", exc_info=exc)
    return error_response(500, "INTERNAL_ERROR", "服务器内部错误")


@app.get("/health", tags=["System"])
def health():
    return {"service": "residence-service", "status": "ok", "version": app.version}


@app.post("/residence-registrations", status_code=201, tags=["Residence Registration"])
def create_registration(payload: ResidenceRegistrationCreate):
    return services.create_registration(payload)


@app.get("/residence-registrations/{citizen_id}", tags=["Residence Registration"])
def get_registration(citizen_id: str):
    return services.get_registration(citizen_id)


@app.patch("/residence-registrations/{citizen_id}", tags=["Residence Registration"])
def update_registration(citizen_id: str, payload: ResidenceRegistrationUpdate):
    return services.update_registration(citizen_id, payload)


@app.delete("/residence-registrations/{citizen_id}", tags=["Residence Registration"])
def cancel_registration(citizen_id: str, payload: RegistrationCancel):
    return services.cancel_registration(citizen_id, payload)


@app.post("/residence-permit-applications", status_code=201, tags=["Permit Application"])
def create_permit_application(payload: PermitApplicationCreate):
    return services.create_permit_application(payload)


@app.get("/residence-permit-applications/{application_id}", tags=["Permit Application"])
def get_permit_application(application_id: str):
    return services.get_permit_application(application_id)


@app.post(
    "/residence-permit-applications/{application_id}/documents",
    status_code=201,
    tags=["Permit Application"],
)
def add_document(application_id: str, payload: DocumentCreate):
    return services.add_document(application_id, payload)


@app.patch("/residence-permit-applications/{application_id}/status", tags=["Permit Application"])
def update_status(application_id: str, payload: StatusUpdate):
    return services.update_application_status(application_id, payload)


@app.get("/citizens/{citizen_id}/residence-status", tags=["Citizen Query"])
def residence_status(citizen_id: str):
    return services.residence_status(citizen_id)


@app.get("/citizens/{citizen_id}/permit-applications", tags=["Citizen Query"])
def list_permit_applications(citizen_id: str):
    return {
        "citizen_id": citizen_id,
        "permit_applications": services.list_permit_applications(citizen_id),
    }


@app.post("/residence-permits/{permit_id}/endorsement", tags=["Residence Permit"])
def endorse_permit(permit_id: str, payload: EndorsementCreate):
    return services.endorse_permit(permit_id, payload)


@app.post("/residence-permits/{permit_id}/report-loss", tags=["Residence Permit"])
def report_loss(permit_id: str):
    return services.report_loss(permit_id)


@app.post("/residence-permits/{permit_id}/apply-reissue", status_code=201, tags=["Residence Permit"])
def apply_reissue(permit_id: str):
    return services.apply_reissue(permit_id)


@app.post("/residence-permits/{permit_id}/e-permit", tags=["Residence Permit"])
def activate_e_permit(permit_id: str):
    return services.activate_e_permit(permit_id)


@app.post(
    "/residence-permit-applications/{application_id}/check-eligibility",
    tags=["Rules"],
)
def check_eligibility(application_id: str):
    return services.check_application_eligibility(application_id)


@app.post(
    "/residence-permit-applications/{application_id}/check-documents",
    tags=["Rules"],
)
def check_documents(application_id: str):
    return services.check_documents(application_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8001")), reload=False)

