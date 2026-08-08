# Role D Housing Service Test Cases

| Test Case | Endpoint | Expected Result |
|---|---|---|
| Eligible profile with complete documents | POST `/housing-eligibility/check` | Returns `eligible` and no missing requirements. |
| Applicant owns local property | POST `/housing-eligibility/check` | Returns `not_eligible` and reason `owns_local_property`. |
| Missing required documents | POST `/housing-eligibility/check` | Returns `conditionally_eligible_missing_documents`. |
| Create application and add document | POST `/housing-subsidy-applications`; POST `/documents` | Application is created and supplementary document is recorded. |
| Query housing status | GET `/citizens/{citizen_id}/housing-status` | Returns latest housing application state. |
| Parallel verification passes | POST `/verification` | Status becomes `under_review`. |
| Employment verification failure | POST `/verification` | Status becomes `verification_failed`. |
| Final approval status update | PATCH `/status` | Status becomes `approved`. |

Run command:

```bash
cd housing-service
pytest -q
```

## Verified Result

On the completed repository version, the Housing Service tests were executed with:

```bash
cd housing-service
python -m pytest -q
```

Result:

```text
9 passed in 0.50s
```
