# Demonstration Quality Gate (F)

The project defines three final quality gates. This is the third, owned by F.
It must be signed off before the final video is recorded, not on submission day.

Run this checklist against the integrated system delivered by E.

## Gate D1 — Demo route runs end to end

| # | Check | Method | Result | Notes |
|---|---|---|---|---|
| D1.1 | All six services plus Gateway and Portal start from E's scripts | Follow E's release README from a clean checkout | | |
| D1.2 | Portal reachable on port 3000 | `curl http://localhost:3000/healthz` | | Baseline §2 |
| D1.3 | Gateway reachable on port 8000 | `curl http://localhost:8000/docs` | | |
| D1.4 | Full demo route completes without an error alert | Follow `demo/demo_storyboard.md` scenes 2–8 | | |
| D1.5 | Route completes within 6 minutes at speaking pace | Timed dry run | | |
| D1.6 | Backup dataset produces the same route | Load `demo/backup_demo_data.md` set B | | |

## Gate D2 — All major microservices appear in the demo

Every service must be visibly exercised, not merely mentioned.

| # | Service | Where it appears | Result |
|---|---|---|---|
| D2.1 | Residence Service (S1, S2) | Scenes 3, 8 | |
| D2.2 | Employment Service (S3, S4) | Scenes 4, 8 | |
| D2.3 | Housing Service (S5, S6) | Scene 5 | |
| D2.4 | Service Matching Service | Scene 7 | |
| D2.5 | API Gateway aggregation | Scene 6 (`/service-plan` combines three services) | |
| D2.6 | CityStart Portal | All scenes | |

## Gate D3 — Recording quality

| # | Check | Result | Notes |
|---|---|---|---|
| D3.1 | Resolution 1920×1080, browser zoom 100% | | |
| D3.2 | No console errors visible in any captured frame | | |
| D3.3 | No test/debug data visible (no "test", "asdf", placeholder names) | | |
| D3.4 | Audio present for every segment, no clipping, consistent level | | |
| D3.5 | Each speaker audible and identified by an on-screen title | | |
| D3.6 | Text legible when played at 720p | | |

## Gate D4 — Duration

| # | Check | Limit | Actual | Result |
|---|---|---|---|---|
| D4.1 | Total video duration | < 10:00 | | |
| D4.2 | Every member has speaking time | ≥ 1:00 each | | |
| D4.3 | Exported file plays start to finish without corruption | | | |

## Gate D5 — Demo matches the report

Mismatch between demo and report is the most likely way to lose marks, because
it is the one inconsistency an examiner sees without reading any code.

| # | Check | Result | Notes |
|---|---|---|---|
| D5.1 | Service names in the demo use the official S1–S6 English names | | Baseline §4.4 |
| D5.2 | Status values shown match the Baseline §4.5 vocabulary | | |
| D5.3 | Endpoints demonstrated match E's frozen API Baseline | | Baseline §7 |
| D5.4 | Analytics figures shown match `analytics.json` and the report | | Both read the same file |
| D5.5 | Activity names on screen match BPMN task names from B and D | | Enforced by `normalize_logs.py` C2 |
| D5.6 | Narration claims nothing the system does not actually do | | |

## Sign-off

| Gate | Owner | Date | Signature |
|---|---|---|---|
| D1 Demo route | F | | |
| D2 Service coverage | F | | |
| D3 Recording quality | F | | |
| D4 Duration | F | | |
| D5 Report consistency | F + A | | |
