from .models import RecommendationRequest, RecommendationResponse


S1 = "S1 Residence Registration Service"
S2 = "S2 Residence Permit Application Service"
S3 = "S3 Employment Registration Service"
S4 = "S4 Employment Support Application Service"
S5 = "S5 Public Rental Housing Eligibility Service"
S6 = "S6 Housing Rental Subsidy Application Service"


def add_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def recommend(data: RecommendationRequest) -> RecommendationResponse:
    completed: list[str] = []
    recommended: list[str] = []
    missing: list[str] = []
    reasons: list[str] = []

    documents = set(data.available_documents)

    if data.residence_registered:
        completed.append(S1)
    else:
        recommended.append(S1)
        reasons.append(
            "Residence registration should be completed first."
        )

        if "identity_document" not in documents:
            add_once(missing, "identity_document")

    if data.residence_permit_approved:
        completed.append(S2)
    elif data.residence_registered:
        recommended.append(S2)
        reasons.append(
            "Residence registration is complete, but the residence permit "
            "has not been approved."
        )

        if "identity_document" not in documents:
            add_once(missing, "identity_document")

    if data.employment_registered:
        completed.append(S3)
    else:
        recommended.append(S3)
        reasons.append(
            "Employment registration has not been completed."
        )

    if data.employment_support_applied:
        completed.append(S4)
    elif data.needs_employment_support:
        recommended.append(S4)
        reasons.append(
            "The citizen has requested employment support."
        )

        if not data.employment_registered:
            add_once(
                missing,
                "employment_registration_record",
            )

    eligibility_result = "requires_review"

    if data.owns_local_property:
        eligibility_result = "not_eligible"
        reasons.append(
            "Housing rental services are not recommended because the citizen "
            "owns local property."
        )

    elif not data.currently_renting:
        eligibility_result = "not_applicable"
        reasons.append(
            "Housing rental services are not recommended because the citizen "
            "is not currently renting."
        )

    elif data.housing_eligibility_result == "eligible":
        eligibility_result = "eligible"
        completed.append(S5)

        if data.housing_subsidy_applied:
            completed.append(S6)
        else:
            recommended.append(S6)
            reasons.append(
                "Housing eligibility is confirmed, but the rental subsidy "
                "application has not been submitted."
            )

            if "rental_contract" not in documents:
                add_once(missing, "rental_contract")

    elif data.housing_eligibility_result == "not_eligible":
        eligibility_result = "not_eligible"
        completed.append(S5)
        reasons.append(
            "The housing subsidy is not recommended because the eligibility "
            "result is not eligible."
        )

    else:
        recommended.append(S5)
        reasons.append(
            "The citizen is renting, owns no local property, and needs a "
            "housing eligibility check."
        )

        if not data.employment_registered:
            add_once(
                missing,
                "employment_registration_record",
            )

        if "rental_contract" not in documents:
            add_once(missing, "rental_contract")

    if reasons:
        recommendation_reason = " ".join(reasons)
    else:
        recommendation_reason = (
            "No additional service is currently recommended."
        )

    return RecommendationResponse(
        citizen_id=data.citizen_id,
        completed_services=completed,
        recommended_services=recommended,
        recommended_order=recommended.copy(),
        missing_requirements=missing,
        eligibility_result=eligibility_result,
        recommendation_reason=recommendation_reason,
    )
