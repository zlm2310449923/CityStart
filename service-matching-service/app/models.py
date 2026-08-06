from typing import Literal

from pydantic import BaseModel, Field, field_validator


HousingEligibilityResult = Literal[
    "not_assessed",
    "eligible",
    "not_eligible",
]


class RecommendationRequest(BaseModel):
    citizen_id: str = Field(min_length=1, max_length=64)
    residence_registered: bool = False
    residence_permit_approved: bool = False
    employment_registered: bool = False
    needs_employment_support: bool = False
    employment_support_applied: bool = False
    currently_renting: bool = False
    owns_local_property: bool = False
    housing_eligibility_result: HousingEligibilityResult = "not_assessed"
    housing_subsidy_applied: bool = False
    available_documents: list[str] = Field(default_factory=list)

    @field_validator("citizen_id")
    @classmethod
    def clean_citizen_id(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("citizen_id must not be blank")

        return value

    @field_validator("available_documents")
    @classmethod
    def clean_documents(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []

        for value in values:
            document = value.strip().lower()

            if document and document not in cleaned:
                cleaned.append(document)

        return cleaned


class RecommendationResponse(BaseModel):
    citizen_id: str
    completed_services: list[str]
    recommended_services: list[str]
    recommended_order: list[str]
    missing_requirements: list[str]
    eligibility_result: str
    recommendation_reason: str
