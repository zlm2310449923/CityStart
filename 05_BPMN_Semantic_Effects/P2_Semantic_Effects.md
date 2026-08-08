# Role D Deliverable: P2 Semantic Effects

## 1. Predicate Naming Convention Used in P2

| Predicate | Meaning |
|---|---|
| Submitted(app, citizen) | The citizen has submitted a housing subsidy application. |
| DocumentsChecked(app) | The submitted documents have been checked. |
| DocumentsComplete(app) | Required documents are complete. |
| AdditionalDocumentsRequested(app) | The platform requests additional materials. |
| AdditionalDocumentsSubmitted(app) | The applicant has submitted supplementary documents. |
| EmploymentVerified(app) | Employment information is verified. |
| HousingInfoVerified(app) | Housing information is verified. |
| EligibilityAssessed(app) | Eligibility has been assessed. |
| Eligible(app) | The applicant meets basic eligibility requirements. |
| Approved(app) | The application has been approved. |
| Rejected(app) | The application has been rejected. |
| ApplicantNotified(app) | The applicant has been notified of the result. |

## 2. Immediate Effects

| BPMN ID | Task | Immediate Effect in English | First-order Logic Effect |
|---|---|---|---|
| P2-T1 | Submit Housing Subsidy Application | A new housing subsidy application is created for the citizen. | Submitted(app, citizen) ∧ Status(app, pending) |
| P2-T2 | Check Submitted Documents | The platform checks whether required documents are complete. | DocumentsChecked(app) |
| P2-G1 | Documents Complete? | The process branches according to document completeness. | DocumentsComplete(app) ∨ ¬DocumentsComplete(app) |
| P2-T3 | Request Additional Documents | The platform requests missing documents from the citizen. | AdditionalDocumentsRequested(app) ∧ Status(app, additional_documents_required) |
| P2-T4 | Submit Additional Documents | The citizen submits supplementary documents. | AdditionalDocumentsSubmitted(app) |
| P2-T5 | Verify Employment Information | Employment registration or employment evidence is verified. | EmploymentVerified(app) ∨ EmploymentVerificationFailed(app) |
| P2-T6 | Verify Housing Information | Renting status and local housing ownership are verified. | HousingInfoVerified(app) ∨ HousingVerificationFailed(app) |
| P2-T7 | Assess Eligibility | The system combines document, employment and housing verification results. | EligibilityAssessed(app) |
| P2-G4 | Eligible? | The process branches into approval review or rejection. | Eligible(app) ∨ ¬Eligible(app) |
| P2-T9 | Approve Application | A qualified application is approved. | Approved(app) ∧ Status(app, approved) |
| P2-T10 | Reject Application | An unqualified application is rejected with a reason. | Rejected(app) ∧ Status(app, rejected) |
| P2-T11 | Notify Applicant | The applicant receives the final decision. | ApplicantNotified(app) |

## 3. Cumulative Effect Scenarios

### Scenario CE-P2-1: Direct Approval

English cumulative effect:
The citizen submits a housing subsidy application with complete materials. Employment information and housing information are both verified. The applicant is assessed as eligible, the application is approved, and the applicant is notified.

Logic:
Submitted(app,citizen) ∧ DocumentsComplete(app) ∧ EmploymentVerified(app) ∧ HousingInfoVerified(app) ∧ EligibilityAssessed(app) ∧ Eligible(app) ∧ Approved(app) ∧ ApplicantNotified(app)

### Scenario CE-P2-2: Supplementary Documents then Approval

English cumulative effect:
The citizen submits an application but some materials are missing. The platform requests additional documents. After the citizen submits supplementary documents, the application passes employment and housing verification and is approved.

Logic:
Submitted(app,citizen) ∧ ¬DocumentsComplete(app) ∧ AdditionalDocumentsRequested(app) ∧ AdditionalDocumentsSubmitted(app) ∧ DocumentsComplete(app) ∧ EmploymentVerified(app) ∧ HousingInfoVerified(app) ∧ Eligible(app) ∧ Approved(app)

### Scenario CE-P2-3: Employment Verification Failure

English cumulative effect:
The application documents are complete, but employment information cannot be verified. The applicant fails eligibility assessment and the application is rejected with an employment-related reason.

Logic:
Submitted(app,citizen) ∧ DocumentsComplete(app) ∧ EmploymentVerificationFailed(app) ∧ EligibilityAssessed(app) ∧ ¬Eligible(app) ∧ Rejected(app)

### Scenario CE-P2-4: Housing Information Verification Failure

English cumulative effect:
The application documents are complete, but the applicant's housing condition does not satisfy the rules, for example the applicant owns local property or is not currently renting. The application is rejected.

Logic:
Submitted(app,citizen) ∧ DocumentsComplete(app) ∧ HousingVerificationFailed(app) ∧ EligibilityAssessed(app) ∧ ¬Eligible(app) ∧ Rejected(app)

## 4. API Mapping for Semantic Effects

| Semantic Effect | Housing Service API |
|---|---|
| Submitted(app, citizen) | POST `/housing-subsidy-applications` |
| AdditionalDocumentsSubmitted(app) | POST `/housing-subsidy-applications/{application_id}/documents` |
| EmploymentVerified(app), HousingInfoVerified(app) | POST `/housing-subsidy-applications/{application_id}/verification` |
| Approved(app), Rejected(app) | PATCH `/housing-subsidy-applications/{application_id}/status` |
| ApplicantNotified(app) | Represented as final status returned to Portal/Gateway in prototype |
