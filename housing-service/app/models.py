from typing import Literal

from pydantic import BaseModel, Field


ApplicationStatus = Literal[
    "pending",
    "under_review",
    "additional_documents_required",
    "verification_failed",
    "approved",
    "rejected",
]

VerificationStatus = Literal["pending", "verified", "failed"]

REQUIRED_HOUSING_DOCUMENTS = [
    "identity_document",
    "rental_contract",
    "employment_evidence",
    "housing_status_statement",
]


class HousingApplicationCreate(BaseModel):
    citizen_id: str = Field(min_length=1)
    monthly_household_income: float = Field(ge=0)
    currently_renting: bool
    owns_local_property: bool
    employment_registered: bool = False
    district: str | None = None
    rental_contract_id: str | None = None
    available_documents: list[str] = Field(default_factory=list)
    remarks: str | None = None


class EligibilityCheck(BaseModel):
    citizen_id: str = Field(min_length=1)
    employment_registered: bool
    monthly_household_income: float = Field(ge=0)
    income_threshold: float = Field(default=5000, gt=0)
    currently_renting: bool
    owns_local_property: bool
    available_documents: list[str] = Field(default_factory=list)


class DocumentCreate(BaseModel):
    document_type: str = Field(min_length=1)
    file_name: str = Field(min_length=1)


class StatusUpdate(BaseModel):
    status: ApplicationStatus
    decision_reason: str | None = None


class VerificationUpdate(BaseModel):
    employment_verified: bool
    housing_verified: bool
    documents_complete: bool
    verifier: str = "Housing Security Department"
    remarks: str | None = None
