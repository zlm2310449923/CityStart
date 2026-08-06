# F Review Tasks (Cross-Member Checks)

Task 9 of F's assignment. F reviews other members' deliverables from the
integration and demonstration standpoint. Record findings here and pass them to
the owner and to A.

---

## R1 — Can B's README actually be used?

Test by following it literally from a clean directory, without asking B anything.

| # | Check | Result | Finding |
|---|---|---|---|
| R1.1 | Prerequisites stated (Python version, pip) | | Baseline §1: must be Python 3.12 |
| R1.2 | `pip install -r requirements.txt` succeeds | | |
| R1.3 | Database initialisation step documented and works | | Baseline §3.1: `residence.db` |
| R1.4 | Service starts on port 8001 | | Baseline §2 |
| R1.5 | Port/host configurable via env, not hard-coded | | Baseline §2 |
| R1.6 | `.env.example` or config notes present | | Baseline §6 |
| R1.7 | Swagger reachable at `/docs` | | |
| R1.8 | Sample data present so endpoints return something | | Baseline §6 |
| R1.9 | At least 4 test cases documented | | Baseline §6 |
| R1.10 | Endpoints match what the Portal calls | | See README dependency table |

---

## R2 — E's integrated release

| # | Check | Result | Finding |
|---|---|---|---|
| R2.1 | All 6 services start from the documented scripts | | |
| R2.2 | Ports match Baseline §2 exactly (3000/8000/8001–8004) | | |
| R2.3 | Gateway routes `/api/residence|employment|housing|recommendations/*` | | |
| R2.4 | Aggregated `GET /api/citizens/{id}/service-plan` returns combined data | | |
| R2.5 | Gateway returns the §4.6 error envelope, not raw FastAPI `detail` | | Portal tolerates both, but §4.6 is required |
| R2.6 | Gateway handles a stopped downstream service without hanging | | Stop one service and retry |
| R2.7 | Timeout handling produces a proper error, not a 500 | | |
| R2.8 | Status values in responses use the §4.5 vocabulary | | Portal badges depend on this |
| R2.9 | Timestamps are ISO 8601 UTC | | Baseline §4.2 |
| R2.10 | Portal is not required to call any service directly | | Baseline §5 |

---

## R3 — Event log vs BPMN task names

Automated. `normalize_logs.py` check C2 compares every activity name against
`bpmn_reference.py`, which mirrors B's P1 and D's P2 task names.

```bash
cd process-mining
python normalize_logs.py --incoming     # validates B's and D's real logs
```

| # | Check | Result | Finding |
|---|---|---|---|
| R3.1 | B's P1 log passes C1–C8 | | |
| R3.2 | D's P2 log passes C1–C8 | | |
| R3.3 | Every BPMN task appears at least once in the logs | | See "BPMN Tasks Observed" in the report |
| R3.4 | Resources match BPMN lane ownership (C3) | | |
| R3.5 | `application_status` uses the §4.5 vocabulary (C7) | | |
| R3.6 | If B or D renamed a task, `bpmn_reference.py` was updated too | | Otherwise C2 fails and mining is blocked |

Attach the generated `logs/validated/validation_report.md` as evidence.

---

## R4 — All demo functions work

Covered by `user_acceptance_testing.md` (UAT-01…08) and
`demonstration_quality_gate.md` (D1–D5). Both must be complete before recording.

---

## R5 — Screenshots and analysis requested by A

| # | Item | Status | Notes |
|---|---|---|---|
| R5.1 | Portal screenshots, uniform size | | Blocked until E's system runs |
| R5.2 | `P1_inductive_miner.png` | Done | `process-mining/output/` |
| R5.3 | `P2_inductive_miner.png` | Done | `process-mining/output/` |
| R5.4 | Variant / bottleneck / conformance tables | Done | Generated into `analytics.json` |
| R5.5 | Extra analysis A asks for after reading the draft | | |

---

## Escalation

Anything found here that F cannot fix alone goes to the owner with: the check ID,
what was observed, what the Baseline requires, and which of F's deliverables is
blocked. Items still open one week before submission are raised at the weekly
meeting per the weekly execution rules.
