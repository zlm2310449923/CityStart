# Role D Report Sections: Enterprise Architecture, Housing Process and Housing Service

## 1. Role D Overview

Role D is responsible for the enterprise architecture model, the P2 housing rental subsidy process, P2 semantic effects, Housing Service implementation, P2 event log simulation, and the related report sections. This role connects the housing business process with the application and technology design of CityStart.

## 2. Enterprise Architecture Method

The enterprise architecture is described using a three-layer ArchiMate-style structure: Business Layer, Application Layer and Technology Layer. The purpose is to show how the business services required by new urban residents are realized by application components and deployed on a technical environment.

The Business Layer defines the main actors, business services and processes. The key actor for Role D is the Housing Security Department. The key business service is S6 Housing Rental Subsidy Application Service. The main process is P2 Housing Rental Subsidy Application and Eligibility Verification.

The Application Layer maps business functions to system modules. The Housing Application Service realizes the housing-related business service. It exposes APIs for application creation, document submission, eligibility checking, verification recording and status update. The API Gateway provides a unified access point and the CityStart Portal provides the user interface.

The Technology Layer describes the runtime environment. The prototype uses FastAPI services, Python/Uvicorn runtime, SQLite database storage, Docker or local processes, and HTTP/JSON communication.

## 3. Business Layer

In the Business Layer, the Citizen uses the housing service to apply for rental subsidy support. The Housing Security Department is the main service provider. The Employment Information Service is involved because employment status may be part of the eligibility evidence for new urban residents. The main business objects include Housing Subsidy Application, Rental Contract, Employment Verification Result, Housing Verification Result and Application Decision.

## 4. Application Layer

The Housing Application Service is designed as an independent microservice. It has high cohesion because it only handles housing-related application data, document metadata, eligibility checks and verification results. It has low coupling because other components access it through HTTP APIs instead of directly accessing its database.

The main Housing Service APIs are:

- `POST /housing-subsidy-applications`
- `GET /housing-subsidy-applications/{application_id}`
- `POST /housing-subsidy-applications/{application_id}/documents`
- `POST /housing-subsidy-applications/{application_id}/verification`
- `PATCH /housing-subsidy-applications/{application_id}/status`
- `GET /citizens/{citizen_id}/housing-status`
- `POST /housing-eligibility/check`

## 5. Technology Layer

The Housing Service can be deployed as a Docker container or a local FastAPI process. It uses SQLite as a lightweight database for the course prototype. The service does not store real personal files; uploaded documents are represented by metadata such as document type and file name. Communication follows the project API convention: JSON payloads, snake_case fields and ISO 8601 timestamps.

## 6. Cross-layer Relationships and Business–IT Alignment

The S6 Housing Rental Subsidy Application Service is realized by the Housing Application Service. The P2 BPMN process is supported by Housing Service endpoints. For example, application submission corresponds to `POST /housing-subsidy-applications`; supplementary document submission corresponds to `POST /housing-subsidy-applications/{application_id}/documents`; final approval or rejection corresponds to `PATCH /housing-subsidy-applications/{application_id}/status`.

This mapping ensures that the business process, the application service, and the implemented API remain consistent.

## 7. P2 Housing Subsidy Process Description

P2 begins when a citizen submits a housing subsidy application. The platform checks whether the required materials are complete. If materials are incomplete, the platform requests additional documents and the citizen submits them. After document checking is complete, employment information and housing information are verified in parallel. The verification results are combined and the applicant's eligibility is assessed. If the applicant is eligible, the application enters review and can be approved. If not, the application is rejected. In both cases, the applicant is notified.

## 8. P2 Semantic Effects

Immediate effects and cumulative effects are used to clarify what changes after each task. For instance, after `Submit Housing Subsidy Application`, the immediate effect is `Submitted(app, citizen) ∧ Status(app, pending)`. After document checking, the process branches according to `DocumentsComplete(app)` or `¬DocumentsComplete(app)`. After final review, the cumulative effect can be either `Approved(app)` or `Rejected(app)`, followed by `ApplicantNotified(app)`.

## 9. Housing Service Implementation

The Housing Service was enhanced to support a more complete P2 process. The implementation includes:

- Pydantic request/response models;
- SQLite tables for subsidy applications, documents and verification records;
- eligibility checking rules;
- supplementary document handling;
- parallel verification result recording;
- final status update;
- unified error responses;
- API tests using FastAPI TestClient.

## 10. P2 Event Log Simulation

A P2 event log simulator was added under `housing-service/scripts/generate_p2_event_log.py`. The generated CSV log is stored at `08_Event_Logs_Process_Mining/P2_housing_subsidy_event_log.csv`. It covers direct approval, supplementary document loops, employment verification failure, housing verification failure, general ineligibility, delayed review and different parallel verification orders. The log uses the agreed fields: `case_id`, `process_name`, `activity`, `timestamp`, `resource`, `outcome`, and `service_name`.

## 11. Testing

Eight Housing Service tests were added or updated. They cover eligibility checking, document completeness, document upload, housing status query, parallel verification success, verification failure and final approval update. These tests verify that the implemented APIs match the P2 process and semantic effects.

## 12. Limitations

The current Housing Service is a course prototype. It does not connect to official housing, property, income or employment databases. Employment and housing verification are simulated through request parameters. The ArchiMate and BPMN deliverables are represented in Markdown/Mermaid and BPMN XML files for easy review and version control.

## 13. Future Work

Future work may include connecting the Gateway service plan interface with the housing verification result, adding more realistic data validation, using PM4Py to generate process mining diagrams, and replacing simulated verification with secure service calls to trusted data providers in a controlled environment.
