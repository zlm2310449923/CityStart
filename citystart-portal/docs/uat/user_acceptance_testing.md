# CityStart Portal — User Acceptance Testing

Scope: the Portal from the end user's perspective (F's task 4). Backend service
correctness is covered by each service owner's own tests; this document covers
what the user sees and how the Portal behaves when things go wrong.

**Portal:** `http://localhost:3000` (Baseline §2)
**Gateway:** `http://localhost:8000`

Status column: PASS / FAIL / BLOCKED (with reason).

---

## UAT-01 — Residence registration submits

| | |
|---|---|
| Page | `/residence-registration` |
| Precondition | Gateway + Residence Service running |
| Steps | Enter set A data (`demo/backup_demo_data.md`); click *Submit Registration* |
| Expected | Success alert; status rendered as a Baseline §4.5 badge; `POST /api/residence/residence-registrations` reaches the service |
| Status | |

---

## UAT-02 — Missing required fields are caught

| | |
|---|---|
| Page | All service forms |
| Steps | Leave `citizen_id` and `full_name` empty; click submit |
| Expected | HTML5 validation blocks submission; no request sent; offending field focused |
| Status | |

Also verify a server-side rejection: submit a body the service considers invalid
and confirm the Portal renders the returned `VALIDATION_ERROR` including the
per-field details, rather than a bare "Unknown error".

---

## UAT-03 — Status dashboard aggregates all three domains

| | |
|---|---|
| Page | `/application-status` |
| Precondition | All services running; set A has submitted applications |
| Steps | Enter `C1001`; click *Load Status* |
| Expected | One `GET /api/citizens/C1001/service-plan` call populates Residence, Employment and Housing cards; badges use the §4.5 vocabulary; recommended services and missing requirements listed |
| Status | |

---

## UAT-04 — Recommendations are complete and explainable

| | |
|---|---|
| Page | `/service-recommendation` |
| Steps | Enter `C1001`; residence ✔, permit ✘, employment ✘, renting ✔, owns property ✘; submit |
| Expected | All five response fields rendered: completed services, recommended services, recommended order, missing requirements, and a non-empty reason |
| Status | |

A recommendation shown without its reason is a fail: explainability is the
service's stated purpose.

---

## UAT-05 — Gateway unavailable degrades gracefully

| | |
|---|---|
| Page | Any page that calls an API |
| Steps | Stop the Gateway; submit a form and run a query |
| Expected | `GATEWAY_UNAVAILABLE` (HTTP 503) in the §4.6 envelope; message and code shown; page remains usable; no blank screen and no unhandled console exception |
| Status | |

Note: if a system HTTP proxy is active, leave `PORTAL_TRUST_ENV_PROXY=0`
(default). Otherwise the proxy answers instead of the Gateway and this test
misreports as `GATEWAY_INVALID_RESPONSE`.

---

## UAT-06 — Slow Gateway produces a timeout, not a hang

| | |
|---|---|
| Steps | Point the Portal at a stub that delays beyond `GATEWAY_TIMEOUT_SECONDS`; submit |
| Expected | `GATEWAY_TIMEOUT` (HTTP 504); button leaves its loading state; user can retry |
| Status | |

---

## UAT-07 — Process analytics renders from generated data

| | |
|---|---|
| Page | `/process-analytics` |
| Precondition | `analysis.py` has been run |
| Steps | Open all four tabs |
| Expected | Overview comparison, P1 and P2 variant / bottleneck / conformance / resource tables, and discovered-model details all populate; the generation timestamp is shown |
| Status | |

Then delete `static/analytics.json` and reload: the page must show the
instructions for regenerating it, not a blank tab.

---

## UAT-08 — Navigation reaches all ten pages

| | |
|---|---|
| Steps | From Home, follow every nav link and every Services dropdown item |
| Expected | All ten pages return 200; no broken link; active page reachable in one or two clicks |
| Status | |

---

## UAT-09 — End-to-end demo route is stable

| | |
|---|---|
| Precondition | Full integrated system running; databases reset |
| Steps | Execute `demo/demo_storyboard.md` scenes 2–8 with set A |
| Expected | Route completes with no error alert; repeatable with set B |
| Status | |

This is the test that gates recording. It must pass twice in a row.

---

## UAT-10 — Baseline conformance of Portal behaviour

| # | Check | Expected | Status |
|---|---|---|---|
| 10.1 | Portal listens on 3000 | `GET /healthz` returns `"port": 3000` | |
| 10.2 | Gateway address from env | Changing `API_GATEWAY_URL` redirects calls with no code edit | |
| 10.3 | No direct service access | `/api/direct/*` returns 404; no service port appears in page source | |
| 10.4 | Request fields `snake_case` | Inspect request bodies in devtools | |
| 10.5 | Status values from §4.5 vocabulary | Unrecognised values fall back to a neutral badge, never crash | |
| 10.6 | Errors use the §4.6 envelope | All three Portal error codes verified | |

---

## Summary

| ID | Test | Status |
|---|---|---|
| UAT-01 | Residence registration submits | |
| UAT-02 | Missing required fields caught | |
| UAT-03 | Status dashboard aggregates | |
| UAT-04 | Recommendations explainable | |
| UAT-05 | Gateway unavailable handled | |
| UAT-06 | Timeout handled | |
| UAT-07 | Analytics renders | |
| UAT-08 | Navigation complete | |
| UAT-09 | Demo route stable | |
| UAT-10 | Baseline conformance | |

UAT-01, 03, 04, 09 depend on E's integrated system and are BLOCKED until it is
available. UAT-02, 05, 06, 07, 08, 10 are testable against the Portal alone.
