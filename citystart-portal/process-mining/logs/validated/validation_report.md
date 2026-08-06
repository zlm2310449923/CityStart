# Event Log Validation Report

Generated: 2026-08-05T17:02:42

Validation gate applied by F before any process mining analysis. Activity names are checked against the BPMN Task names defined by B (P1) and D (P2) in `bpmn_reference.py`.

## Summary

| Log | Source | Events | Cases | BPMN Tasks Observed | Errors | Warnings | Verdict |
|---|---|---|---|---|---|---|---|
| P1 | `logs\p1_event_log.csv` | 708 | 100 | 9/9 | 0 | 0 | **PASS** |
| P2 | `logs\p2_event_log.csv` | 938 | 100 | 12/12 | 0 | 0 | **PASS** |

## P1 detail

All checks passed with no warnings.

## P2 detail

All checks passed with no warnings.

## Check definitions

| Code | Check |
|---|---|
| C1 | Required fields present |
| C2 | Activity names match BPMN Task names exactly |
| C3 | Resource matches the BPMN lane owning the task |
| C4 | Timestamps parse and increase monotonically within each case |
| C5 | Every case terminates in a recognised end activity |
| C6 | No duplicate (case_id, activity, timestamp) events |
| C7 | `application_status` uses the Baseline §4.5 vocabulary |
| C8 | Timestamps are ISO 8601 UTC with a `Z` suffix (Baseline §4.2) |
