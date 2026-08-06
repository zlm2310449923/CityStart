"""BPMN reference definitions for P1 and P2.

This module is the single source of truth used by:
  - normalize_logs.py  (validating that event log activity names match BPMN Task names)
  - analysis.py        (conformance checking against the designed process)

Task names and IDs follow the unified numbering convention agreed in the
supplementary specification (P1-T1, P1-G1, ...). B owns the P1 BPMN and D owns
the P2 BPMN; F mirrors their task names here for cross-model consistency
checking. If B or D rename a task, this file must be updated in the same commit.
"""

P1_PROCESS_NAME = "Residence Permit Application and Additional Document Process"
P2_PROCESS_NAME = "Housing Rental Subsidy Application and Eligibility Verification Process"

# ---------------------------------------------------------------------------
# P1 -- owned by B
# ---------------------------------------------------------------------------

P1_TASKS = {
    "P1-T1": "Submit Residence Permit Application",
    "P1-T2": "Validate Identity",
    "P1-T3": "Check Submitted Documents",
    "P1-T4": "Request Additional Documents",
    "P1-T5": "Submit Additional Documents",
    "P1-T6": "Review Application",
    "P1-T7": "Approve Application",
    "P1-T8": "Reject Application",
    "P1-T9": "Notify Applicant",
}

P1_RESOURCES = {
    "Submit Residence Permit Application": "Citizen",
    "Validate Identity": "Public Security Department",
    "Check Submitted Documents": "Public Security Department",
    "Request Additional Documents": "Public Security Department",
    "Submit Additional Documents": "Citizen",
    "Review Application": "Public Security Department",
    "Approve Application": "Public Security Department",
    "Reject Application": "Public Security Department",
    "Notify Applicant": "CityStart Platform",
}

# ---------------------------------------------------------------------------
# P2 -- owned by D
# ---------------------------------------------------------------------------

P2_TASKS = {
    "P2-T1": "Submit Housing Subsidy Application",
    "P2-T2": "Check Submitted Documents",
    "P2-T3": "Request Additional Documents",
    "P2-T4": "Submit Additional Documents",
    "P2-T5": "Verify Employment Information",
    "P2-T6": "Verify Housing Information",
    "P2-T7": "Combine Verification Results",
    "P2-T8": "Assess Eligibility",
    "P2-T9": "Review Application",
    "P2-T10": "Approve Application",
    "P2-T11": "Reject Application",
    "P2-T12": "Notify Applicant",
}

P2_RESOURCES = {
    "Submit Housing Subsidy Application": "Citizen",
    "Check Submitted Documents": "Housing Security Department",
    "Request Additional Documents": "Housing Security Department",
    "Submit Additional Documents": "Citizen",
    "Verify Employment Information": "Human Resources Department",
    "Verify Housing Information": "Housing Security Department",
    "Combine Verification Results": "Housing Security Department",
    "Assess Eligibility": "Housing Security Department",
    "Review Application": "Housing Security Department",
    "Approve Application": "Housing Security Department",
    "Reject Application": "Housing Security Department",
    "Notify Applicant": "CityStart Platform",
}

# ---------------------------------------------------------------------------
# Terminal / decision activities, used for outcome derivation
# ---------------------------------------------------------------------------

APPROVAL_ACTIVITY = "Approve Application"
REJECTION_ACTIVITY = "Reject Application"
SUPPLEMENT_REQUEST_ACTIVITY = "Request Additional Documents"
SUPPLEMENT_SUBMIT_ACTIVITY = "Submit Additional Documents"

# Activities that P2 executes on parallel branches after the Parallel Gateway
# (P2-G1). Their relative order in a trace is not semantically meaningful.
P2_PARALLEL_BRANCH = [
    "Verify Employment Information",
    "Verify Housing Information",
]

# Required event log fields. The group specification (小组分配) names these
# process_name / service_name, while the supplementary specification (补充)
# names them process_id / service_id. Both are emitted so that neither B/D's
# generators nor F's analysis break.
REQUIRED_FIELDS = [
    "case_id",
    "process_name",
    "activity",
    "timestamp",
    "resource",
    "outcome",
    "service_name",
]

OPTIONAL_FIELDS = [
    "process_id",
    "service_id",
    "lifecycle",
    "application_status",
    "duration_hours",
    "variant",
]

# ---------------------------------------------------------------------------
# Baseline §4.5 -- the only permitted application_status values. Event logs
# must use the same vocabulary as the REST APIs, otherwise the mining chapter
# and the API chapter of the report describe different state machines.
# ---------------------------------------------------------------------------

STATUS_PENDING = "pending"
STATUS_UNDER_REVIEW = "under_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_ADDITIONAL_DOCUMENTS_REQUIRED = "additional_documents_required"

ALLOWED_STATUS_VALUES = {
    STATUS_PENDING,
    STATUS_UNDER_REVIEW,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_ADDITIONAL_DOCUMENTS_REQUIRED,
}

# Activity -> status the case enters on completion of that activity.
STATUS_AFTER_ACTIVITY = {
    "Review Application": STATUS_UNDER_REVIEW,
    APPROVAL_ACTIVITY: STATUS_APPROVED,
    REJECTION_ACTIVITY: STATUS_REJECTED,
    SUPPLEMENT_REQUEST_ACTIVITY: STATUS_ADDITIONAL_DOCUMENTS_REQUIRED,
    SUPPLEMENT_SUBMIT_ACTIVITY: STATUS_UNDER_REVIEW,
}


def tasks_for(process_id):
    return P1_TASKS if process_id == "P1" else P2_TASKS


def resources_for(process_id):
    return P1_RESOURCES if process_id == "P1" else P2_RESOURCES


def process_name_for(process_id):
    return P1_PROCESS_NAME if process_id == "P1" else P2_PROCESS_NAME


def allowed_activities(process_id):
    return set(tasks_for(process_id).values())
