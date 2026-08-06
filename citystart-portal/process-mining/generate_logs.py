"""Event log generator for P1 and P2.

Role note
---------
In the group split, B generates the P1 log and D generates the P2 log from
their own service implementations. F is responsible for *integrating* those
logs (see normalize_logs.py). This generator exists so that F's analysis
pipeline can be developed and demonstrated before B/D deliver, and so that a
reproducible reference log set is always available for the demo. When B/D
supply real logs, place them in logs/incoming/ and run normalize_logs.py --
the analysis pipeline is identical.

Modelling decisions
-------------------
1. Reproducibility: a fixed RANDOM_SEED makes every figure in the report
   re-derivable. Do not change the seed after report figures are quoted.

2. duration_hours is defined as the elapsed time attributable to completing
   that activity (waiting + processing), i.e. the gap between the previous
   event's completion and this event's completion. Case throughput time is
   therefore the sum of its activities' durations.

3. Per-activity duration profiles (triangular distributions) are used instead
   of one uniform range. A uniform range across all activities would make
   every activity look equally slow and destroy the bottleneck signal --
   real bottlenecks must come from the model, not from the analysis.

4. P2's two verification activities sit on parallel branches after the
   Parallel Gateway. They are modelled as genuinely concurrent: both start
   when document checking finishes, and each is stamped at its own completion
   time. Their order in the trace therefore varies by case, which is what
   allows the Inductive Miner to discover concurrency rather than a fixed
   sequence. "Combine Verification Results" can only start once the slower
   branch finishes, so the synchronisation wait is an emergent property.

5. Designed variants are labelled in the `variant` column. Note that a
   designed variant is not the same thing as a discovered control-flow
   variant: two designed variants that differ only in timing (e.g. the
   delayed-processing path) share one control-flow trace. The analysis
   reports both views separately rather than conflating them.
"""

import csv
import os
import random

from datetime import datetime, timedelta, timezone

import bpmn_reference as bpmn

RANDOM_SEED = 20260803

# (low, high, mode) in hours, for random.triangular
P1_DURATION_PROFILE = {
    "Submit Residence Permit Application": (0.2, 1.5, 0.5),
    "Validate Identity": (1.0, 8.0, 2.0),
    "Check Submitted Documents": (4.0, 24.0, 8.0),
    "Request Additional Documents": (1.0, 6.0, 2.0),
    "Submit Additional Documents": (24.0, 120.0, 48.0),
    "Review Application": (48.0, 168.0, 72.0),
    "Approve Application": (2.0, 12.0, 4.0),
    "Reject Application": (2.0, 12.0, 4.0),
    "Notify Applicant": (0.1, 1.0, 0.3),
}

P2_DURATION_PROFILE = {
    "Submit Housing Subsidy Application": (0.2, 1.5, 0.5),
    "Check Submitted Documents": (4.0, 24.0, 8.0),
    "Request Additional Documents": (1.0, 6.0, 2.0),
    "Submit Additional Documents": (24.0, 120.0, 48.0),
    "Verify Employment Information": (24.0, 96.0, 48.0),
    "Verify Housing Information": (24.0, 96.0, 40.0),
    "Combine Verification Results": (1.0, 8.0, 2.0),
    "Assess Eligibility": (4.0, 24.0, 8.0),
    "Review Application": (12.0, 48.0, 24.0),
    "Approve Application": (2.0, 12.0, 4.0),
    "Reject Application": (2.0, 12.0, 4.0),
    "Notify Applicant": (0.1, 1.0, 0.3),
}

FIELDNAMES = [
    "case_id",
    "process_name",
    "process_id",
    "service_name",
    "service_id",
    "activity",
    "timestamp",
    "resource",
    "lifecycle",
    "outcome",
    "application_status",
    "duration_hours",
    "variant",
]

BASE_TIME = datetime(2026, 7, 1, 9, 0, 0, tzinfo=timezone.utc)


def _iso_utc(dt):
    """Baseline §4.2: ISO 8601 in UTC, e.g. 2026-08-05T10:30:00Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _draw(profile, activity, multiplier=1.0):
    low, high, mode = profile[activity]
    return round(random.triangular(low, high, mode) * multiplier, 2)


def _outcome_for(activity):
    if activity == bpmn.APPROVAL_ACTIVITY:
        return "approved"
    if activity == bpmn.REJECTION_ACTIVITY:
        return "rejected"
    if activity == bpmn.SUPPLEMENT_REQUEST_ACTIVITY:
        return "pending_documents"
    return "in_progress"


def _make_event(case_id, process_id, service_id, service_name, activity,
                timestamp, duration_hours, application_status, variant):
    return {
        "case_id": case_id,
        "process_name": bpmn.process_name_for(process_id),
        "process_id": process_id,
        "service_name": service_name,
        "service_id": service_id,
        "activity": activity,
        "timestamp": _iso_utc(timestamp),
        "resource": bpmn.resources_for(process_id)[activity],
        "lifecycle": "complete",
        "outcome": _outcome_for(activity),
        "application_status": application_status,
        "duration_hours": duration_hours,
        "variant": variant,
    }


# ---------------------------------------------------------------------------
# P1
# ---------------------------------------------------------------------------

P1_VARIANTS = {
    # variant name -> (case count, supplement rounds, final decision, review multiplier)
    "V1_DirectApproval": (45, 0, "approve", 1.0),
    "V2_SingleSupplement": (20, 1, "approve", 1.0),
    "V3_ReviewRejection": (15, 0, "reject", 1.0),
    "V4_MultipleSupplements": (10, 2, "approve", 1.0),
    "V5_IdentityFailure": (6, 0, "identity_fail", 1.0),
    "V6_DelayedReview": (4, 0, "approve", 2.5),
}

P1_SERVICE_ID = "S2"
P1_SERVICE_NAME = "Residence Permit Application Service"


def generate_p1_logs(output_path="logs/p1_event_log.csv"):
    events = []
    case_counter = 0

    for variant, (count, rounds, decision, review_mult) in P1_VARIANTS.items():
        for _ in range(count):
            case_counter += 1
            case_id = f"P1-C{case_counter:04d}"
            t = BASE_TIME + timedelta(days=random.randint(0, 30),
                                      hours=random.randint(0, 8))
            status = bpmn.STATUS_PENDING

            def emit(activity, multiplier=1.0):
                nonlocal t, status
                d = _draw(P1_DURATION_PROFILE, activity, multiplier)
                t = t + timedelta(hours=d)
                status = bpmn.STATUS_AFTER_ACTIVITY.get(activity, status)
                events.append(_make_event(
                    case_id, "P1", P1_SERVICE_ID, P1_SERVICE_NAME,
                    activity, t, d, status, variant))

            emit("Submit Residence Permit Application")
            emit("Validate Identity")

            if decision == "identity_fail":
                # P1-G1 identity gateway takes the failure branch: no document
                # check and no review are performed at all.
                emit("Reject Application")
                emit("Notify Applicant")
                continue

            emit("Check Submitted Documents")
            for _ in range(rounds):
                emit("Request Additional Documents")
                emit("Submit Additional Documents")
                emit("Check Submitted Documents")

            emit("Review Application", review_mult)
            if decision == "approve":
                emit("Approve Application")
            else:
                emit("Reject Application")
            emit("Notify Applicant")

    _write(events, output_path, "P1", case_counter)
    return output_path


# ---------------------------------------------------------------------------
# P2
# ---------------------------------------------------------------------------

P2_VARIANTS = {
    # variant -> (count, supplement rounds, decision, slow branch, branch multiplier)
    "V1_DirectApproval": (38, 0, "approve", None, 1.0),
    "V2_DocumentSupplement": (22, 1, "approve", None, 1.0),
    "V3_EmploymentIneligible": (16, 0, "reject_after_review", None, 1.0),
    "V4_HousingIneligible": (12, 0, "reject_at_assessment", None, 1.0),
    "V5_ParallelBranchDelay": (8, 0, "approve", "Verify Employment Information", 2.5),
    "V6_DocumentRejection": (4, 0, "reject_early", None, 1.0),
}

P2_SERVICE_ID = "S6"
P2_SERVICE_NAME = "Housing Rental Subsidy Application Service"


def generate_p2_logs(output_path="logs/p2_event_log.csv"):
    events = []
    case_counter = 0

    for variant, (count, rounds, decision, slow_branch, mult) in P2_VARIANTS.items():
        for _ in range(count):
            case_counter += 1
            case_id = f"P2-C{case_counter:04d}"
            t = BASE_TIME + timedelta(days=random.randint(0, 30),
                                      hours=random.randint(0, 8))
            status = bpmn.STATUS_PENDING

            def emit(activity, at_time, duration):
                nonlocal status
                status = bpmn.STATUS_AFTER_ACTIVITY.get(activity, status)
                events.append(_make_event(
                    case_id, "P2", P2_SERVICE_ID, P2_SERVICE_NAME,
                    activity, at_time, duration, status, variant))

            def emit_seq(activity, multiplier=1.0):
                nonlocal t
                d = _draw(P2_DURATION_PROFILE, activity, multiplier)
                t = t + timedelta(hours=d)
                emit(activity, t, d)

            emit_seq("Submit Housing Subsidy Application")
            emit_seq("Check Submitted Documents")

            if decision == "reject_early":
                # P2-G1 document completeness gateway rejects outright, so the
                # parallel verification branches never execute.
                emit_seq("Review Application")
                emit_seq("Reject Application")
                emit_seq("Notify Applicant")
                continue

            for _ in range(rounds):
                emit_seq("Request Additional Documents")
                emit_seq("Submit Additional Documents")
                emit_seq("Check Submitted Documents")

            # --- Parallel Gateway P2-G2: both branches start together -------
            fork_time = t
            branch_events = []
            for activity in bpmn.P2_PARALLEL_BRANCH:
                m = mult if activity == slow_branch else 1.0
                d = _draw(P2_DURATION_PROFILE, activity, m)
                branch_events.append((fork_time + timedelta(hours=d), activity, d))

            # Log order follows actual completion order -> genuine interleaving.
            branch_events.sort(key=lambda x: x[0])
            for at_time, activity, d in branch_events:
                emit(activity, at_time, d)

            # --- Synchronisation: join waits for the slower branch ----------
            join_time = max(e[0] for e in branch_events)
            t = join_time
            emit_seq("Combine Verification Results")
            emit_seq("Assess Eligibility")

            if decision == "reject_at_assessment":
                emit_seq("Reject Application")
                emit_seq("Notify Applicant")
                continue

            emit_seq("Review Application")
            if decision == "approve":
                emit_seq("Approve Application")
            else:
                emit_seq("Reject Application")
            emit_seq("Notify Applicant")

    _write(events, output_path, "P2", case_counter)
    return output_path


def _write(events, output_path, label, case_count):
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(events)
    print(f"{label} event log: {len(events)} events, {case_count} cases -> {output_path}")


if __name__ == "__main__":
    random.seed(RANDOM_SEED)
    generate_p1_logs()
    generate_p2_logs()
    print(f"Done (seed={RANDOM_SEED}, reproducible).")
