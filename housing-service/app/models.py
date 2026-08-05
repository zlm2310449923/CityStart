from typing import Literal

from pydantic import BaseModel, Field


ApplicationStatus = Literal[
    "pending", "under_review", "approved", "rejected", "additional_documents_required"
]


class HousingApplicationCreate(BaseModel):
    citizen_id: str = Field(min_length=1)
    monthly_household_income: float = Field(ge=0)
    currently_renting: bool
    owns_local_property: bool


class EligibilityCheck(BaseModel):
    citizen_id: str = Field(min_length=1)
    employment_registered: bool
    monthly_household_income: float = Field(ge=0)
    income_threshold: float = Field(default=5000, gt=0)
    currently_renting: bool
    owns_local_property: bool


class DocumentCreate(BaseModel):
    document_type: str = Field(min_length=1)
    file_name: str = Field(min_length=1)


class StatusUpdate(BaseModel):
    status: ApplicationStatus

