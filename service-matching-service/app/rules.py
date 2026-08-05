from .models import RecommendationRequest, RecommendationResponse


def recommend(data: RecommendationRequest) -> RecommendationResponse:
    completed: list[str] = []
    recommended: list[str] = []
    missing: list[str] = []
    reasons: list[str] = []

    if data.residence_registered:
        completed.append("S1 Residence Registration Service")
    else:
        recommended.append("S1 Residence Registration Service")
        reasons.append("Residence registration is the first required step.")

    if data.residence_permit_approved:
        completed.append("S2 Residence Permit Application Service")
    elif data.residence_registered:
        recommended.append("S2 Residence Permit Application Service")
        reasons.append("A residence permit can be requested after registration.")

    if data.employment_registered:
        completed.append("S3 Employment Registration Service")
        recommended.append("S4 Employment Support Application Service")
    else:
        recommended.append("S3 Employment Registration Service")
        missing.append("employment_registration_record")

    housing_eligible = (
        data.employment_registered and data.currently_renting and not data.owns_local_property
    )
    if housing_eligible:
        recommended.extend([
            "S5 Public Rental Housing Eligibility Service",
            "S6 Housing Rental Subsidy Application Service",
        ])
        reasons.append("The citizen is renting, employed, and owns no local property.")
    elif data.owns_local_property:
        reasons.append("Housing rental subsidy is not recommended because local property is owned.")
    elif not data.currently_renting:
        reasons.append("Housing rental subsidy requires a current rental situation.")

    required_documents = {"identity_document", "rental_contract"}
    missing.extend(sorted(required_documents - set(data.available_documents)))

    return RecommendationResponse(
        citizen_id=data.citizen_id,
        completed_services=completed,
        recommended_services=list(dict.fromkeys(recommended)),
        recommended_order=list(dict.fromkeys(recommended)),
        missing_requirements=list(dict.fromkeys(missing)),
        eligibility_result="eligible" if housing_eligible else "requires_review",
        recommendation_reason=" ".join(reasons) or "No additional service is currently required.",
    )

