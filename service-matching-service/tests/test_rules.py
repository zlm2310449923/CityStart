from app.models import RecommendationRequest
from app.rules import recommend


def request(**overrides):
    values = {"citizen_id": "C1001", "available_documents": []}
    values.update(overrides)
    return RecommendationRequest(**values)


def test_recommends_residence_registration_first():
    result = recommend(request())
    assert result.recommended_order[0].startswith("S1")


def test_recommends_permit_after_registration():
    result = recommend(request(residence_registered=True))
    assert any(item.startswith("S2") for item in result.recommended_services)


def test_recommends_employment_registration():
    result = recommend(request())
    assert any(item.startswith("S3") for item in result.recommended_services)


def test_housing_eligible_profile():
    result = recommend(request(employment_registered=True, currently_renting=True))
    assert result.eligibility_result == "eligible"
    assert any(item.startswith("S6") for item in result.recommended_services)


def test_property_owner_not_recommended_for_subsidy():
    result = recommend(request(employment_registered=True, currently_renting=True, owns_local_property=True))
    assert not any(item.startswith("S6") for item in result.recommended_services)


def test_reports_missing_documents():
    result = recommend(request(available_documents=["identity_document"]))
    assert "rental_contract" in result.missing_requirements

