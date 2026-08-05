from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ApplicationStatus = Literal[
    "pending", "under_review", "approved", "rejected", "additional_documents_required"
]


class EmploymentRegistrationCreate(BaseModel):
    citizen_id: str = Field(min_length=1)
    employer_name: str = Field(min_length=1)
    employment_type: str = Field(min_length=1)
    employment_start_date: date


class SupportApplicationCreate(BaseModel):
    citizen_id: str = Field(min_length=1)
    support_type: str = Field(min_length=1)


class StatusUpdate(BaseModel):
    status: ApplicationStatus

