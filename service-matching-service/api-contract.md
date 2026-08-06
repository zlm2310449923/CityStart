Service Matching API Contract

The Service Matching Service runs on port 8004.

It provides two endpoints.

GET /health

This endpoint is used to check whether the service is running.

A successful response contains the service name and the status.

POST /recommendations

This endpoint receives the current status of a citizen and generates a list of recommended CityStart services.

Request fields

citizen_id

Required string. This is the ID used to identify the citizen.

residence_registered

Boolean value. It shows whether residence registration has been completed. The default value is false.

residence_permit_approved

Boolean value. It shows whether the residence permit has been approved. The default value is false.

employment_registered

Boolean value. It shows whether employment registration has been completed. The default value is false.

needs_employment_support

Boolean value. It shows whether the citizen needs employment support. The default value is false.

employment_support_applied

Boolean value. It shows whether an employment support application has already been submitted. The default value is false.

currently_renting

Boolean value. It shows whether the citizen is currently renting a property. The default value is false.

owns_local_property

Boolean value. It shows whether the citizen owns local property. The default value is false.

housing_eligibility_result

String value. The available values are not_assessed, eligible and not_eligible. The default value is not_assessed.

housing_subsidy_applied

Boolean value. It shows whether a housing rental subsidy application has already been submitted. The default value is false.

available_documents

A list of document names currently available to the citizen. The default value is an empty list.

The current Gateway can send the basic residence, employment and housing fields. Fields that are not sent will use their default values.

Response fields

citizen_id

The citizen ID received in the request.

completed_services

A list of services that have already been completed.

recommended_services

A list of services recommended for the citizen.

recommended_order

The suggested order for completing the recommended services.

missing_requirements

A list of documents or conditions that are still missing.

eligibility_result

The current housing-related eligibility result. Possible returned values include requires_review, eligible, not_eligible and not_applicable.

recommendation_reason

A short explanation of why the services were recommended or not recommended.

Service names

S1 Residence Registration Service
S2 Residence Permit Application Service
S3 Employment Registration Service
S4 Employment Support Application Service
S5 Public Rental Housing Eligibility Service
S6 Housing Rental Subsidy Application Service

Error response

If the request is invalid, the service returns HTTP status code 422.

The error response contains an error code, an error message and a list of validation details.

The error code used for an invalid request is VALIDATION_ERROR.
