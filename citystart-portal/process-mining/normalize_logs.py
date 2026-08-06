"""Event log integration and validation (F's actual responsibility).

The group split assigns F the task of *integrating* the P1 log produced by B
and the P2 log produced by D. Integration is not just concatenation -- the two
logs come from different developers and must be checked before any process
mining conclusion can be trusted. This script performs that gate.

Checks performed
----------------
C1  Required fields present            (小组分配 field list)
C2  Activity names match BPMN Task names exactly
        This is the cross-model consistency check F owes the group: if an
        activity in the log is not a BPMN Task name, either B/D renamed a task
        without telling anyone, or the log writer abbreviated it. Both break
        traceability between the report's BPMN chapter and the mining chapter.
C3  Resource matches the BPMN lane that owns the task
C4  Timestamps parse and increase monotonically within each case
C5  Every case terminates in a recognised end activity
C6  No duplicate (case_id, activity, timestamp) triples
C7  application_status values are drawn from the Baseline §4.5 vocabulary
        pending / under_review / approved / rejected /
        additional_documents_required
C8  Timestamps are ISO 8601 in UTC with a Z suffix (Baseline §4.2), so that
        the log, the REST APIs and the report all express time identically

Outputs
-------
logs/validated/{p1,p2}_event_log.csv   normalised, both field-naming schemes
logs/validated/{p1,p2}_event_log.xes   XES for ProM interoperability
logs/validated/validation_report.md    the audit trail to hand to A

Usage
-----
    python normalize_logs.py                    # validate generated reference logs
    python normalize_logs.py --incoming         # validate B/D logs in logs/incoming/
"""

import argparse
import csv
import os
import re
import sys

from collections import Counter, defaultdict
from datetime import datetime
from xml.sax.saxutils import escape

import bpmn_reference as bpmn

VALIDATED_DIR = os.path.join("logs", "validated")
INCOMING_DIR = os.path.join("logs", "incoming")

END_ACTIVITIES = {"Notify Applicant"}

# Baseline §4.2 -- ISO 8601 UTC, e.g. 2026-08-05T10:30:00Z
ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ValidationResult:
    def __init__(self, process_id, source_path):
        self.process_id = process_id
        self.source_path = source_path
        self.errors = []
        self.warnings = []
        self.info = {}

    @property
    def passed(self):
        return not self.errors

    def error(self, code, message):
        self.errors.append((code, message))

    def warn(self, code, message):
        self.warnings.append((code, message))


def _read_csv(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _normalise_row(row, process_id):
    """Fill in whichever of the two field-naming schemes is missing."""
    out = dict(row)
    if not out.get("process_name"):
        out["process_name"] = bpmn.process_name_for(process_id)
    if not out.get("process_id"):
        out["process_id"] = process_id
    if not out.get("service_name") and out.get("service_id"):
        out["service_name"] = out["service_id"]
    if not out.get("service_id") and out.get("service_name"):
        out["service_id"] = out["service_name"]
    out.setdefault("lifecycle", "complete")
    out.setdefault("variant", "")
    return out


def validate(path, process_id):
    result = ValidationResult(process_id, path)
    rows = _read_csv(path)

    if not rows:
        result.error("C1", "log is empty")
        return result, []

    # --- C1 required fields -------------------------------------------------
    header = set(rows[0].keys())
    for field in bpmn.REQUIRED_FIELDS:
        if field not in header:
            # tolerated only if the alternate naming scheme supplies it
            alt = {"process_name": "process_id", "service_name": "service_id"}.get(field)
            if alt and alt in header:
                result.warn("C1", f"field '{field}' missing, derived from '{alt}'")
            else:
                result.error("C1", f"required field '{field}' missing")

    rows = [_normalise_row(r, process_id) for r in rows]

    allowed = bpmn.allowed_activities(process_id)
    expected_resources = bpmn.resources_for(process_id)

    # --- C2 / C3 activity names and lane ownership --------------------------
    unknown_activities = defaultdict(int)
    resource_mismatch = defaultdict(int)
    for r in rows:
        activity = r.get("activity", "")
        if activity not in allowed:
            unknown_activities[activity] += 1
            continue
        expected = expected_resources[activity]
        actual = r.get("resource", "")
        if actual and actual != expected:
            resource_mismatch[f"{activity}: expected '{expected}', got '{actual}'"] += 1

    for activity, n in sorted(unknown_activities.items()):
        result.error(
            "C2",
            f"activity '{activity}' ({n} events) is not a {process_id} BPMN Task name")
    for message, n in sorted(resource_mismatch.items()):
        result.warn("C3", f"{message} ({n} events)")

    # --- C4 timestamps ------------------------------------------------------
    cases = defaultdict(list)
    for idx, r in enumerate(rows):
        raw = r.get("timestamp", "")
        try:
            # fromisoformat accepts "...Z" only from Python 3.11 onwards;
            # normalise defensively so validation does not depend on the
            # interpreter minor version.
            r["_ts"] = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            result.error("C4", f"row {idx + 2}: unparseable timestamp {raw!r}")
            r["_ts"] = None
            continue
        cases[r["case_id"]].append(r)

    non_monotonic = 0
    mixed_awareness = 0
    for case_id, evs in cases.items():
        stamps = [e["_ts"] for e in evs if e["_ts"]]
        aware = [s for s in stamps if s.tzinfo is not None]
        # A log that mixes offset-aware and offset-naive timestamps cannot be
        # ordered at all, so report it as its own fault rather than crashing.
        if aware and len(aware) != len(stamps):
            mixed_awareness += 1
            continue
        if stamps != sorted(stamps):
            non_monotonic += 1
    if mixed_awareness:
        result.error(
            "C4",
            f"{mixed_awareness} cases mix timezone-aware and timezone-naive "
            f"timestamps; all timestamps must be UTC per Baseline §4.2")
    if non_monotonic:
        result.error("C4", f"{non_monotonic} cases have out-of-order timestamps")

    # --- C5 termination -----------------------------------------------------
    unterminated = [cid for cid, evs in cases.items()
                    if evs and evs[-1]["activity"] not in END_ACTIVITIES]
    if unterminated:
        result.warn(
            "C5",
            f"{len(unterminated)} cases do not end in {sorted(END_ACTIVITIES)} "
            f"(e.g. {unterminated[:3]})")

    # --- C6 duplicates ------------------------------------------------------
    seen = set()
    duplicates = 0
    for r in rows:
        key = (r["case_id"], r.get("activity"), r.get("timestamp"))
        if key in seen:
            duplicates += 1
        seen.add(key)
    if duplicates:
        result.error("C6", f"{duplicates} duplicate (case, activity, timestamp) events")

    # --- C7 Baseline status vocabulary --------------------------------------
    bad_status = Counter()
    for r in rows:
        value = (r.get("application_status") or "").strip()
        if not value:
            continue
        if value not in bpmn.ALLOWED_STATUS_VALUES:
            bad_status[value] += 1
    for value, n in sorted(bad_status.items()):
        result.error(
            "C7",
            f"application_status '{value}' ({n} events) is not in the Baseline "
            f"§4.5 vocabulary {sorted(bpmn.ALLOWED_STATUS_VALUES)}")

    # --- C8 UTC timestamp format -------------------------------------------
    bad_format = 0
    for r in rows:
        if not ISO_UTC_RE.match(r.get("timestamp", "")):
            bad_format += 1
    if bad_format:
        result.warn(
            "C8",
            f"{bad_format} timestamps are not ISO 8601 UTC with a Z suffix "
            f"(Baseline §4.2, e.g. 2026-08-05T10:30:00Z)")

    result.info = {
        "events": len(rows),
        "cases": len(cases),
        "activities": len({r["activity"] for r in rows}),
        "bpmn_tasks_defined": len(bpmn.tasks_for(process_id)),
        "bpmn_tasks_observed": len({r["activity"] for r in rows} & allowed),
        "resources": len({r.get("resource", "") for r in rows}),
    }

    for r in rows:
        r.pop("_ts", None)
    return result, rows


def write_normalised(rows, process_id, out_dir=VALIDATED_DIR):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{process_id.lower()}_event_log.csv")
    fieldnames = bpmn.REQUIRED_FIELDS + [
        f for f in bpmn.OPTIONAL_FIELDS if any(f in r for r in rows)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_xes(rows, process_id, out_dir=VALIDATED_DIR):
    """Emit XES 1.0 so the logs can also be opened in ProM."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{process_id.lower()}_event_log.xes")

    cases = defaultdict(list)
    for r in rows:
        cases[r["case_id"]].append(r)
    for evs in cases.values():
        evs.sort(key=lambda e: e["timestamp"])

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<log xes.version="1.0" xes.features="nested-attributes" '
        'xmlns="http://www.xes-standard.org/">',
        '  <extension name="Concept" prefix="concept" '
        'uri="http://www.xes-standard.org/concept.xesext"/>',
        '  <extension name="Time" prefix="time" '
        'uri="http://www.xes-standard.org/time.xesext"/>',
        '  <extension name="Organizational" prefix="org" '
        'uri="http://www.xes-standard.org/org.xesext"/>',
        '  <extension name="Lifecycle" prefix="lifecycle" '
        'uri="http://www.xes-standard.org/lifecycle.xesext"/>',
        f'  <string key="concept:name" value="{escape(bpmn.process_name_for(process_id))}"/>',
    ]

    for case_id, evs in sorted(cases.items()):
        lines.append("  <trace>")
        lines.append(f'    <string key="concept:name" value="{escape(case_id)}"/>')
        if evs[0].get("variant"):
            lines.append(f'    <string key="variant" value="{escape(evs[0]["variant"])}"/>')
        for e in evs:
            lines.append("    <event>")
            lines.append(f'      <string key="concept:name" value="{escape(e["activity"])}"/>')
            lines.append(f'      <date key="time:timestamp" value="{e["timestamp"]}"/>')
            lines.append(f'      <string key="org:resource" value="{escape(e.get("resource", ""))}"/>')
            lines.append(f'      <string key="lifecycle:transition" value="{escape(e.get("lifecycle", "complete"))}"/>')
            if e.get("outcome"):
                lines.append(f'      <string key="outcome" value="{escape(e["outcome"])}"/>')
            lines.append("    </event>")
        lines.append("  </trace>")

    lines.append("</log>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def write_report(results, out_dir=VALIDATED_DIR):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "validation_report.md")
    lines = [
        "# Event Log Validation Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Validation gate applied by F before any process mining analysis. "
        "Activity names are checked against the BPMN Task names defined by B (P1) "
        "and D (P2) in `bpmn_reference.py`.",
        "",
        "## Summary",
        "",
        "| Log | Source | Events | Cases | BPMN Tasks Observed | Errors | Warnings | Verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        info = r.info or {}
        observed = f"{info.get('bpmn_tasks_observed', 0)}/{info.get('bpmn_tasks_defined', 0)}"
        verdict = "PASS" if r.passed else "FAIL"
        lines.append(
            f"| {r.process_id} | `{r.source_path}` | {info.get('events', 0)} | "
            f"{info.get('cases', 0)} | {observed} | {len(r.errors)} | "
            f"{len(r.warnings)} | **{verdict}** |")

    for r in results:
        lines += ["", f"## {r.process_id} detail", ""]
        if not r.errors and not r.warnings:
            lines.append("All checks passed with no warnings.")
        for code, msg in r.errors:
            lines.append(f"- **ERROR [{code}]** {msg}")
        for code, msg in r.warnings:
            lines.append(f"- WARNING [{code}] {msg}")

    lines += [
        "",
        "## Check definitions",
        "",
        "| Code | Check |",
        "|---|---|",
        "| C1 | Required fields present |",
        "| C2 | Activity names match BPMN Task names exactly |",
        "| C3 | Resource matches the BPMN lane owning the task |",
        "| C4 | Timestamps parse and increase monotonically within each case |",
        "| C5 | Every case terminates in a recognised end activity |",
        "| C6 | No duplicate (case_id, activity, timestamp) events |",
        "| C7 | `application_status` uses the Baseline §4.5 vocabulary |",
        "| C8 | Timestamps are ISO 8601 UTC with a `Z` suffix (Baseline §4.2) |",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming", action="store_true",
                        help="validate B/D supplied logs in logs/incoming/ instead")
    args = parser.parse_args()

    source_dir = INCOMING_DIR if args.incoming else "logs"
    targets = [("P1", os.path.join(source_dir, "p1_event_log.csv")),
               ("P2", os.path.join(source_dir, "p2_event_log.csv"))]

    results = []
    for process_id, path in targets:
        if not os.path.exists(path):
            print(f"[skip] {process_id}: {path} not found")
            continue
        print(f"[validate] {process_id}: {path}")
        result, rows = validate(path, process_id)
        results.append(result)

        for code, msg in result.errors:
            print(f"  ERROR [{code}] {msg}")
        for code, msg in result.warnings:
            print(f"  WARN  [{code}] {msg}")

        if result.passed:
            csv_path = write_normalised(rows, process_id)
            xes_path = write_xes(rows, process_id)
            print(f"  PASS -> {csv_path}")
            print(f"       -> {xes_path}")
        else:
            print(f"  FAIL: {process_id} not exported. Fix the log before mining.")

    if results:
        report = write_report(results)
        print(f"\nValidation report: {report}")

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
