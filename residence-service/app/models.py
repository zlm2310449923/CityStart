from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ApplicationStatus = Literal[
    "pending", "under_review", "approved", "rejected", "additional_documents_required"
]


class ResidenceRegistrationCreate(BaseModel):
    citizen_id: str = Field(min_length=1)
    residential_address: str = Field(min_length=1)
    residence_start_date: date


class PermitApplicationCreate(BaseModel):
    citizen_id: str = Field(min_length=1)


class DocumentCreate(BaseModel):
    document_type: str = Field(min_length=1)
    file_name: str = Field(min_length=1)


class StatusUpdate(BaseModel):
    status: ApplicationStatus

