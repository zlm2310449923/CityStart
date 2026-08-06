Service Matching Service

This is the service recommendation part of the CityStart project.

The service receives a citizen's current residence, employment and housing information. It then checks a set of simple rules and returns the services that have already been completed, the services that may be needed next, the suggested order and any missing requirements.

The service does not use its own database. The required citizen information is included in the request.

The default port is 8004.

To install the required packages, run:

pip install -r requirements.txt

To start the service, run:

python -m uvicorn app.main:app --reload --port 8004

Swagger can be opened at:

http://127.0.0.1:8004/docs

The health check endpoint is:

GET /health

The recommendation endpoint is:

POST /recommendations

The request may contain the citizen ID, residence registration status, residence permit status, employment registration status, current rental status, local property status and available documents.

The result contains completed services, recommended services, the recommended order, missing requirements, an eligibility result and a short reason for the recommendation.

The service uses the following CityStart service names:

S1 Residence Registration Service
S2 Residence Permit Application Service
S3 Employment Registration Service
S4 Employment Support Application Service
S5 Public Rental Housing Eligibility Service
S6 Housing Rental Subsidy Application Service

To run the tests, use:

pytest

The tests cover the main recommendation rules, missing requirements, API responses and invalid requests.
