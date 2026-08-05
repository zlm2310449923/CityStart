from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    citizen_id: str = Field(min_length=1)
    residence_registered: bool = False
    residence_permit_approved: bool = False
    employment_registered: bool = False
    currently_renting: bool = False
    owns_local_property: bool = False
    available_documents: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    citizen_id: str
    completed_services: list[str]
    recommended_services: list[str]
    recommended_order: list[str]
    missing_requirements: list[str]
    eligibility_result: str
    recommendation_reason: str

