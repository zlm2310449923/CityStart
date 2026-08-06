from app.models import RecommendationRequest
from app.rules import S1, S2, S3, S4, S5, S6, recommend


def make_request(**overrides) -> RecommendationRequest:
    values = {
        "citizen_id": "C1001",
        "available_documents": [],
    }
    values.update(overrides)

    return RecommendationRequest(**values)


def test_new_citizen_receives_basic_recommendations():
    result = recommend(make_request())

    assert result.recommended_order[:2] == [S1, S3]
    assert "identity_document" in result.missing_requirements
    assert "rental_contract" not in result.missing_requirements


def test_residence_permit_is_recommended_after_registration():
    result = recommend(
        make_request(
            residence_registered=True,
            available_documents=["identity_document"],
        )
    )

    assert S1 in result.completed_services
    assert S2 in result.recommended_services


def test_employment_support_reports_missing_registration():
    result = recommend(
        make_request(
            needs_employment_support=True,
        )
    )

    assert S4 in result.recommended_services
    assert (
        "employment_registration_record"
        in result.missing_requirements
    )


def test_renting_citizen_receives_housing_eligibility_check():
    result = recommend(
        make_request(
            residence_registered=True,
            residence_permit_approved=True,
            employment_registered=True,
            currently_renting=True,
            available_documents=["rental_contract"],
        )
    )

    assert result.recommended_services == [S5]
    assert result.eligibility_result == "requires_review"
    assert result.missing_requirements == []


def test_eligible_citizen_receives_subsidy_recommendation():
    result = recommend(
        make_request(
            residence_registered=True,
            residence_permit_approved=True,
            employment_registered=True,
            currently_renting=True,
            housing_eligibility_result="eligible",
            available_documents=["rental_contract"],
        )
    )

    assert S5 in result.completed_services
    assert result.recommended_services == [S6]
    assert result.eligibility_result == "eligible"


def test_property_owner_does_not_receive_housing_services():
    result = recommend(
        make_request(
            employment_registered=True,
            currently_renting=True,
            owns_local_property=True,
        )
    )

    assert S5 not in result.recommended_services
    assert S6 not in result.recommended_services
    assert result.eligibility_result == "not_eligible"


def test_not_eligible_result_does_not_recommend_subsidy():
    result = recommend(
        make_request(
            employment_registered=True,
            currently_renting=True,
            housing_eligibility_result="not_eligible",
        )
    )

    assert S5 in result.completed_services
    assert S6 not in result.recommended_services


def test_document_names_are_cleaned():
    request = make_request(
        available_documents=[
            " Identity_Document ",
            "identity_document",
            "Rental_Contract",
        ]
    )

    assert request.available_documents == [
        "identity_document",
        "rental_contract",
    ]
