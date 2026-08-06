from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ApplicationStatus = Literal[
    "pending",
    "under_review",
    "additional_documents_required",
    "verification",
    "approved",
    "rejected",
]
DocumentType = Literal[
    "identity_document",
    "residence_proof",
    "employment_proof",
    "enrollment_proof",
    "social_security_record",
    "marriage_certificate",
    "spouse_id_document",
    "application_form",
    "other",
]


class ResidenceRegistrationCreate(BaseModel):
    citizen_id: str = Field(min_length=1, max_length=64)
    residential_address: str = Field(min_length=1, max_length=300)
    residence_start_date: date
    contact_phone: str | None = Field(default=None, pattern=r"^1\d{10}$")


class ResidenceRegistrationUpdate(BaseModel):
    residential_address: str | None = Field(default=None, min_length=1, max_length=300)
    contact_phone: str | None = Field(default=None, pattern=r"^1\d{10}$")

    @model_validator(mode="after")
    def require_change(self):
        if self.residential_address is None and self.contact_phone is None:
            raise ValueError("至少提供一个需要更新的字段")
        return self


class RegistrationCancel(BaseModel):
    cancel_reason: str = Field(min_length=1, max_length=500)


class PermitApplicationCreate(BaseModel):
    citizen_id: str = Field(min_length=1, max_length=64)
    application_reason: str | None = Field(default=None, max_length=500)
    is_express: bool = False
    has_social_security_6m: bool = False
    is_enrolled_6m: bool = False
    is_employed_6m: bool = False
    is_married_to_local_6m: bool = False


class DocumentCreate(BaseModel):
    document_type: DocumentType
    file_name: str = Field(min_length=1, max_length=255)


class StatusUpdate(BaseModel):
    status: ApplicationStatus
    reviewer_id: str | None = Field(default=None, max_length=64)
    reviewer_comment: str | None = Field(default=None, max_length=1000)


class EndorsementCreate(BaseModel):
    current_address: str = Field(min_length=1, max_length=300)

