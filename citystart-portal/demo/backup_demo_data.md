# Demo Datasets (Primary + Backup)

F's assignment requires a backup dataset so a corrupted or already-consumed
primary record cannot derail a live recording.

All values follow Baseline §4.1 (`snake_case`), §4.2 (ISO 8601 UTC) and §4.5
(status vocabulary).

## Why a backup is needed

Application IDs are consumed once. If a take is restarted after submitting a
form, the same citizen ID may already hold an application and the service may
reject the duplicate — mid-recording. Switching to set B gives a clean run
without restarting databases.

---

## Set A — Primary

| Field | Value |
|---|---|
| `citizen_id` | `C1001` |
| `full_name` | `Zhang Wei` |
| `id_number` | `420100199001011234` |
| `phone` | `13800138000` |
| `current_address` | `123 Optical Valley Road, Hongshan District, Wuhan` |
| `employer_name` | `Wuhan Optics Valley Technology Co., Ltd.` |
| `position` | `Software Engineer` |
| `start_date` | `2026-03-01` |
| `monthly_income` | `9500.00` |
| `rental_address` | `456 Luojiashan Road, Wuchang District, Wuhan` |
| `monthly_rent` | `2500.00` |
| `lease_start` | `2026-01-01` |
| `owns_local_property` | `false` |

Recommendation panel input: residence registered ✔, permit ✘,
employment ✘, renting ✔, owns property ✘.

Expected: recommends S2 Residence Permit and S3 Employment Registration, and
reports employment registration as a missing requirement for the housing
subsidy assessment.

---

## Set B — Backup

| Field | Value |
|---|---|
| `citizen_id` | `C2002` |
| `full_name` | `Li Na` |
| `id_number` | `420100199505052345` |
| `phone` | `13900139000` |
| `current_address` | `88 Jianghan Road, Jiangan District, Wuhan` |
| `employer_name` | `Wuhan East Lake Data Services Co., Ltd.` |
| `position` | `Data Analyst` |
| `start_date` | `2026-02-15` |
| `monthly_income` | `8800.00` |
| `rental_address` | `77 Zhongshan Avenue, Jiangan District, Wuhan` |
| `monthly_rent` | `2200.00` |
| `lease_start` | `2026-02-01` |
| `owns_local_property` | `false` |

Same expected behaviour as set A.

---

## Set C — Negative case (error handling scene)

Used to show validation and error handling rather than a happy path.

| Scenario | Input | Expected |
|---|---|---|
| Missing required field | Leave `citizen_id` empty, submit | Browser validation blocks submission; field highlighted |
| Unknown citizen | Query `C9999` | `404` with the §4.6 envelope; Portal shows code and message |
| Gateway stopped | Stop the Gateway, submit any form | `GATEWAY_UNAVAILABLE` (503); page does not crash |
| Ineligible applicant | `owns_local_property = true` | Eligibility check reports ineligible with a reason |

---

## Pre-recording reset

```bash
# 1. Reset service databases (E's documented method), then restart all services.
# 2. Confirm the Portal and Gateway are up:
curl http://localhost:3000/healthz
curl http://localhost:8000/docs

# 3. Regenerate analytics so the page matches the report:
cd process-mining
python generate_logs.py && python normalize_logs.py && python analysis.py
```

Then rehearse once with set A. If any record is consumed, switch to set B for
the real take.

## Note on data realism

These are fabricated records for demonstration only. Per the project scope, the
system uses simulated data and connects to no real government database
(Baseline §3.4). Identity numbers follow the Wuhan `4201` prefix pattern for
plausibility but do not identify real people.
