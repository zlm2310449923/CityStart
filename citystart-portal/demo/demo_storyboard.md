# CityStart Demonstration Storyboard

**Total budget: 9:30 (hard limit 10:00)**
**Resolution: 1920×1080, browser zoom 100%**
**Datasets: `demo/backup_demo_data.md` (set A primary, set B backup)**

Every member speaks. Segment owners record their own narration; F assembles and
edits. Times are targets — F confirms the total in Gate D4 before final export.

---

## Segment allocation

| Seg | Scenes | Speaker | Duration | Topic |
|---|---|---|---|---|
| 1 | 1 | A | 1:10 | Problem, scope, architecture overview |
| 2 | 2–3 | B | 1:20 | Service identification, BSRL, Residence Service, P1 |
| 3 | 4 | C | 1:20 | BPMN conventions, semantic effects, Employment Service, P3 |
| 4 | 5 | D | 1:20 | ArchiMate layers, Housing Service, P2 parallel verification |
| 5 | 6 | E | 1:30 | SoaML, Gateway routing, aggregation, integration |
| 6 | 7–8 | A | 0:50 | Matching Service rules and explainability |
| 7 | 9 | F | 1:40 | Portal implementation and process mining results |
| 8 | 10 | F | 0:20 | Close |
| | | | **9:30** | |

---

## Scene 1 — Problem and architecture (A, 1:10)

Visual: title slide, then the overall architecture diagram.

Narration points:
- New residents in Wuhan must deal with three separate agencies and do not know
  the required order of steps.
- CityStart unifies six business services across three providers.
- `Citizen → Portal → API Gateway → Microservices` (Baseline §5). Each business
  service owns its own SQLite database; no shared database.

---

## Scene 2 — Portal home and citizen profile (B, 0:40)

Visual: `http://localhost:3000/`, then Profile page.

Actions: enter set A citizen details, save, click *Load Status Overview*.

Narration: the Portal is the only thing the citizen sees; it holds no business
data and reaches every service through the Gateway.

---

## Scene 3 — Residence registration and permit, P1 (B, 0:40)

Visual: Residence Registration form → submit → query. Then Residence Permit form.

Actions: submit set A registration; show the success alert with the returned
status badge; query it back.

Narration: S1 and S2, BSRL specification, and P1's document supplement loop —
the loop that later shows up in the mining results.

---

## Scene 4 — Employment registration and support, P3 (C, 1:20)

Visual: Employment Registration page; query employment status; Employment
Support page.

Actions: query `C1001` employment status *before* registering to show the gap,
then register, then re-query.

Narration: S3 and S4, BPMN task naming convention (`P3-T1` style), immediate vs
cumulative semantic effects, and why employment registration is a precondition
for the housing subsidy assessment.

---

## Scene 5 — Housing subsidy and P2, ArchiMate (D, 1:20)

Visual: Housing Subsidy form → submit → eligibility check.

Actions: submit set A housing application; run the eligibility check.

Narration: S5 and S6; P2 verifies employment and housing information on
**parallel** branches across two agencies; ArchiMate business / application /
technology layers and how they align.

---

## Scene 6 — Gateway aggregation and integration (E, 1:30)

Visual: Application Status Dashboard, then the Gateway's Swagger UI.

Actions: load `C1001`; show the three status cards populated from one call.
In Swagger, call `GET /api/citizens/{citizen_id}/service-plan` and show the
composed response. Then stop one downstream service and repeat to show the error
path.

Narration: SoaML participants and contracts; the Gateway routes, composes,
handles timeouts and unavailable services, and returns the unified §4.6 error
envelope; the Portal never contacts a service directly.

---

## Scene 7 — Service recommendation (A, 0:35)

Visual: Service Recommendation page.

Actions: enter set A status (residence ✔, permit ✘, employment ✘, renting ✔,
owns property ✘), submit.

Narration: rule-based, stateless, explainable — it returns completed services,
recommended services, an execution order, missing requirements, and a reason.

---

## Scene 8 — Remaining pages (A, 0:15)

Visual: quick pass through Employment Support and Residence Permit document
upload to show full coverage of all six services.

---

## Scene 9 — Portal implementation and process mining (F, 1:40)

Visual: Process Analytics page, all four tabs. Then the generated Petri nets in
`process-mining/output/`.

Actions and narration:

1. **Portal** (0:20) — Jinja2 + Bootstrap + `fetch`, no framework. Every figure
   on this page is loaded from `analytics.json`; nothing is typed by hand, so
   the page and the report cannot drift apart.

2. **Log integration** (0:25) — B and D produce the P1 and P2 logs; F validates
   them through eight checks before any analysis. Show
   `validation_report.md`. Check C2 rejects any activity name that is not a BPMN
   task name, which is what keeps the mining chapter traceable to the BPMN
   chapter. Logs export to CSV and XES.

3. **Variants** (0:25) — P1: 5 control-flow variants from 6 designed variants,
   because the delayed-review variant differs only in timing and shares a
   trace. P2: 9 variants from 6, because the two parallel verification
   activities complete in different orders. Concurrency multiplies observable
   traces without changing the model.

4. **Bottlenecks** (0:20) — P1: *Review Application*, 102 h mean, 63.5% of all
   recorded time. P2: no single dominant task; instead the parallel join waits
   a mean of 20 h (max 93 h) for the slower agency — a cost of the gateway
   design, invisible in per-activity statistics.

5. **Conformance** (0:20) — Replay fitness against a model discovered from the
   same log is 1.0 by construction, so the meaningful check is the comparison
   against B's and D's designed paths: 100% of cases conform.

6. **Models** (0:10) — Inductive Miner Petri nets; P2 shows the concurrency
   construct matching D's Parallel Gateway.

---

## Scene 10 — Close (F, 0:20)

Visual: Home page.

Narration: report, source code, runnable system and this demonstration form one
consistent deliverable; models, code, logs and analysis all use the same task
names, service numbers and status vocabulary.

---

## Production checklist

Before recording:
- [ ] E's integrated release runs; ports 3000 / 8000 / 8001–8004 confirmed
- [ ] Databases reset; set A unconsumed
- [ ] `python generate_logs.py && python normalize_logs.py && python analysis.py` re-run
- [ ] Graphviz on `PATH` so Petri nets exist
- [ ] Browser at 100% zoom, bookmarks bar hidden, no personal tabs
- [ ] Notifications silenced
- [ ] Set B ready if a take fails

After recording:
- [ ] Every segment has audio at a consistent level
- [ ] On-screen title identifies each speaker
- [ ] No console errors or placeholder data in any frame
- [ ] Total under 10:00
- [ ] Exported file played start to finish
- [ ] `docs/uat/demonstration_quality_gate.md` signed off

Recording tool: OBS Studio. Editing: any NLE that exports 1080p MP4.
