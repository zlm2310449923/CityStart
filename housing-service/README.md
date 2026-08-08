# CityStart Housing Service

Role D is responsible for the Housing Service. This service supports the P2 Housing Rental Subsidy Application and Eligibility Verification process.

## Main APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/housing-subsidy-applications` | Create a housing subsidy application |
| GET | `/housing-subsidy-applications/{application_id}` | Retrieve an application |
| POST | `/housing-subsidy-applications/{application_id}/documents` | Upload supplementary document metadata |
| POST | `/housing-subsidy-applications/{application_id}/verification` | Record employment, housing and document verification results |
| PATCH | `/housing-subsidy-applications/{application_id}/status` | Update review status |
| GET | `/citizens/{citizen_id}/housing-status` | Query a citizen's housing-related status |
| POST | `/housing-eligibility/check` | Check basic housing subsidy eligibility |

## Run locally

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8003
```

Swagger UI: http://127.0.0.1:8003/docs

## Run tests

```bash
pytest -q
```

The tests cover eligibility checking, document resubmission, parallel verification, verification failure, status update, and housing status retrieval.
