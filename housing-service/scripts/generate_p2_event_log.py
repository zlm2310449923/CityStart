from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

FIELDS = ["case_id", "process_name", "activity", "timestamp", "resource", "outcome", "service_name"]
PROCESS = "P2 Housing Rental Subsidy Application and Eligibility Verification"
SERVICE = "S6 Housing Rental Subsidy Application Service"


def emit_case(case_id: str, start: datetime, variant: str):
    rows = []
    t = start

    def add(activity: str, resource: str, outcome: str, minutes: int):
        nonlocal t
        rows.append({
            "case_id": case_id,
            "process_name": PROCESS,
            "activity": activity,
            "timestamp": t.isoformat(timespec="seconds"),
            "resource": resource,
            "outcome": outcome,
            "service_name": SERVICE,
        })
        t += timedelta(minutes=minutes)

    add("Submit Housing Subsidy Application", "Citizen", "submitted", 8)
    add("Check Submitted Documents", "CityStart Platform", "checked", 10)

    if variant in {"supplement_then_approved", "multiple_supplements", "incomplete_rejected"}:
        add("Request Additional Documents", "CityStart Platform", "requested", 60)
        add("Submit Additional Documents", "Citizen", "submitted", 90)
        add("Check Submitted Documents", "CityStart Platform", "checked", 10)
        if variant == "multiple_supplements":
            add("Request Additional Documents", "CityStart Platform", "requested_again", 120)
            add("Submit Additional Documents", "Citizen", "submitted_again", 90)
            add("Check Submitted Documents", "CityStart Platform", "checked", 10)
        if variant == "incomplete_rejected":
            add("Reject Application", "Housing Security Department", "rejected_documents_incomplete", 5)
            add("Notify Applicant", "CityStart Platform", "notified", 0)
            return rows

    # Parallel verification is represented by close timestamps and variant order differences.
    if variant == "housing_first":
        add("Verify Housing Information", "Housing Security Department", "verified", 15)
        add("Verify Employment Information", "Employment Information Service", "verified", 20)
    else:
        add("Verify Employment Information", "Employment Information Service", "verified" if variant != "employment_failed" else "failed", 15)
        add("Verify Housing Information", "Housing Security Department", "verified" if variant != "housing_failed" else "failed", 20)

    add("Combine Verification Results", "CityStart Platform", "combined", 5)
    add("Assess Eligibility", "Housing Security Department", "eligible" if variant not in {"employment_failed", "housing_failed", "not_eligible"} else "not_eligible", 10)

    if variant in {"employment_failed", "housing_failed", "not_eligible"}:
        add("Reject Application", "Housing Security Department", f"rejected_{variant}", 5)
    else:
        if variant == "review_delay":
            add("Review Application", "Housing Security Department", "delayed_review", 24 * 60)
        else:
            add("Review Application", "Housing Security Department", "reviewed", 30)
        add("Approve Application", "Housing Security Department", "approved", 5)

    add("Notify Applicant", "CityStart Platform", "notified", 0)
    return rows


def generate(output_path: str | Path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    variants = [
        "direct_approved",
        "supplement_then_approved",
        "multiple_supplements",
        "employment_failed",
        "housing_failed",
        "not_eligible",
        "review_delay",
        "housing_first",
        "incomplete_rejected",
    ]
    rows = []
    base = datetime(2026, 8, 1, 9, 0, 0)
    for i, variant in enumerate(variants, start=1):
        rows.extend(emit_case(f"P2-{i:03d}", base + timedelta(hours=i * 2), variant))
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return output


if __name__ == "__main__":
    generate("../../08_Event_Logs_Process_Mining/P2_housing_subsidy_event_log.csv")
