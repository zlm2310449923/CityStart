"""Process mining analysis for P1 and P2.

Every figure quoted in the Part F report is produced by this script and written
to output/analytics.json, which the Portal's Process Analytics page fetches at
runtime. No number is hard-coded in the report or in the page -- if the logs
change, re-run this script and both update together.

Analyses
--------
1. Control-flow variant analysis
     Designed variants (the `variant` column) and discovered control-flow
     variants are reported separately. They do not coincide: variants that
     differ only in timing collapse onto one control-flow trace.

2. Performance / bottleneck analysis
     Per-activity duration statistics, case throughput time, and the
     synchronisation wait introduced by P2's parallel gateway.

3. Conformance checking
     Token-based replay fitness of the log against a model discovered by the
     Inductive Miner, plus an explicit structural comparison against the
     designed BPMN control flow. Both are needed: replay fitness against a
     model discovered *from the same log* is near-1 by construction and says
     little on its own, so the designed-path comparison is what actually
     answers "does reality match B and D's BPMN".

4. Resource analysis
     Workload and mean activity duration per organisational unit.
"""

import csv
import json
import os
import statistics

from collections import Counter, defaultdict
from datetime import datetime

import bpmn_reference as bpmn

try:
    import pandas as pd
    import pm4py
    from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
    from pm4py.algo.discovery.inductive import algorithm as inductive_miner
    from pm4py.objects.conversion.process_tree import converter as pt_converter
    PM4PY = True
except ImportError:
    PM4PY = False

VALIDATED_DIR = os.path.join("logs", "validated")
OUTPUT_DIR = "output"
BOTTLENECK_THRESHOLD_HOURS = 48.0


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_cases(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        # Baseline §4.2 timestamps end in Z; normalise for fromisoformat so the
        # pipeline does not depend on the interpreter minor version.
        r["_ts"] = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        r["_dur"] = float(r.get("duration_hours") or 0)
    cases = defaultdict(list)
    for r in rows:
        cases[r["case_id"]].append(r)
    for evs in cases.values():
        evs.sort(key=lambda e: e["_ts"])
    return rows, dict(cases)


# ---------------------------------------------------------------------------
# 1. Variant analysis
# ---------------------------------------------------------------------------

def variant_analysis(cases):
    traces = defaultdict(list)
    for case_id, evs in cases.items():
        traces[tuple(e["activity"] for e in evs)].append(case_id)

    designed = Counter()
    for evs in cases.values():
        if evs[0].get("variant"):
            designed[evs[0]["variant"]] += 1

    total = len(cases)
    control_flow = []
    for rank, (trace, ids) in enumerate(
            sorted(traces.items(), key=lambda x: len(x[1]), reverse=True), start=1):
        member_variants = Counter()
        for cid in ids:
            v = cases[cid][0].get("variant")
            if v:
                member_variants[v] += 1
        control_flow.append({
            "rank": rank,
            "cases": len(ids),
            "percentage": round(len(ids) / total * 100, 1),
            "length": len(trace),
            "trace": list(trace),
            "designed_variants": dict(member_variants),
            "sample_case_ids": ids[:3],
        })

    return {
        "total_cases": total,
        "distinct_control_flow_variants": len(traces),
        "control_flow_variants": control_flow,
        "designed_variants": [
            {"variant": name, "cases": n, "percentage": round(n / total * 100, 1)}
            for name, n in designed.most_common()
        ],
    }


# ---------------------------------------------------------------------------
# 2. Performance / bottleneck analysis
# ---------------------------------------------------------------------------

def performance_analysis(rows, cases):
    per_activity = defaultdict(list)
    for r in rows:
        per_activity[r["activity"]].append(r["_dur"])

    activities = []
    for activity, durs in per_activity.items():
        occurrences_over = sum(1 for d in durs if d > BOTTLENECK_THRESHOLD_HOURS)
        activities.append({
            "activity": activity,
            "occurrences": len(durs),
            "mean_hours": round(statistics.mean(durs), 1),
            "median_hours": round(statistics.median(durs), 1),
            "max_hours": round(max(durs), 1),
            "min_hours": round(min(durs), 1),
            "total_hours": round(sum(durs), 1),
            "share_of_total_time_pct": 0.0,
            "occurrences_over_threshold": occurrences_over,
        })

    grand_total = sum(a["total_hours"] for a in activities) or 1.0
    for a in activities:
        a["share_of_total_time_pct"] = round(a["total_hours"] / grand_total * 100, 1)

    activities.sort(key=lambda a: a["mean_hours"], reverse=True)

    throughput = []
    for evs in cases.values():
        hours = (evs[-1]["_ts"] - evs[0]["_ts"]).total_seconds() / 3600
        throughput.append(hours)

    rework_cases = 0
    for evs in cases.values():
        counts = Counter(e["activity"] for e in evs)
        if any(v > 1 for v in counts.values()):
            rework_cases += 1

    return {
        "bottleneck_threshold_hours": BOTTLENECK_THRESHOLD_HOURS,
        "throughput_days": {
            "mean": round(statistics.mean(throughput) / 24, 1),
            "median": round(statistics.median(throughput) / 24, 1),
            "p90": round(sorted(throughput)[int(len(throughput) * 0.9)] / 24, 1),
            "max": round(max(throughput) / 24, 1),
            "min": round(min(throughput) / 24, 1),
        },
        "activities": activities,
        "top_bottleneck": activities[0]["activity"] if activities else None,
        "rework_cases": rework_cases,
        "rework_percentage": round(rework_cases / len(cases) * 100, 1),
    }


def synchronisation_analysis(cases):
    """P2 only: quantify the wait created by the parallel gateway join.

    The join cannot fire until the slower verification branch completes, so the
    difference between the two branch completion times is time the faster
    branch spends idle. This is invisible in per-activity statistics and is the
    real cost of D's Parallel Gateway design.
    """
    waits = []
    slower = Counter()
    for evs in cases.values():
        branch = [e for e in evs if e["activity"] in bpmn.P2_PARALLEL_BRANCH]
        if len(branch) != 2:
            continue
        first, second = sorted(branch, key=lambda e: e["_ts"])
        waits.append((second["_ts"] - first["_ts"]).total_seconds() / 3600)
        slower[second["activity"]] += 1

    if not waits:
        return None
    return {
        "cases_with_parallel_branches": len(waits),
        "idle_wait_hours": {
            "mean": round(statistics.mean(waits), 1),
            "median": round(statistics.median(waits), 1),
            "max": round(max(waits), 1),
        },
        "slower_branch_frequency": dict(slower),
    }


# ---------------------------------------------------------------------------
# 3. Conformance checking
# ---------------------------------------------------------------------------

def designed_paths(process_id):
    """Enumerate the control-flow paths the BPMN model permits.

    Kept deliberately small and explicit rather than parsing BPMN XML, because
    B and D deliver diagrams rather than machine-readable models. This encodes
    the same paths their diagrams describe.
    """
    if process_id == "P1":
        base = ["Submit Residence Permit Application", "Validate Identity"]
        paths = [base + ["Reject Application", "Notify Applicant"]]
        for rounds in range(0, 3):
            mid = ["Check Submitted Documents"]
            for _ in range(rounds):
                mid += ["Request Additional Documents",
                        "Submit Additional Documents",
                        "Check Submitted Documents"]
            for decision in ("Approve Application", "Reject Application"):
                paths.append(base + mid + ["Review Application", decision,
                                           "Notify Applicant"])
        return paths

    base = ["Submit Housing Subsidy Application", "Check Submitted Documents"]
    paths = [base + ["Review Application", "Reject Application", "Notify Applicant"]]
    for rounds in range(0, 2):
        mid = []
        for _ in range(rounds):
            mid += ["Request Additional Documents",
                    "Submit Additional Documents",
                    "Check Submitted Documents"]
        # both interleavings of the parallel branch are conformant
        for order in ([bpmn.P2_PARALLEL_BRANCH[0], bpmn.P2_PARALLEL_BRANCH[1]],
                      [bpmn.P2_PARALLEL_BRANCH[1], bpmn.P2_PARALLEL_BRANCH[0]]):
            head = base + mid + order + ["Combine Verification Results",
                                         "Assess Eligibility"]
            paths.append(head + ["Reject Application", "Notify Applicant"])
            for decision in ("Approve Application", "Reject Application"):
                paths.append(head + ["Review Application", decision,
                                     "Notify Applicant"])
    return paths


def structural_conformance(cases, process_id):
    allowed = {tuple(p) for p in designed_paths(process_id)}
    conformant = 0
    deviations = Counter()
    for case_id, evs in cases.items():
        trace = tuple(e["activity"] for e in evs)
        if trace in allowed:
            conformant += 1
        else:
            deviations[" -> ".join(trace)] += 1
    total = len(cases)
    return {
        "method": "designed-path comparison",
        "designed_paths_enumerated": len(allowed),
        "conformant_cases": conformant,
        "conformant_percentage": round(conformant / total * 100, 1),
        "deviating_cases": total - conformant,
        "deviating_traces": [
            {"trace": t, "cases": n} for t, n in deviations.most_common(5)
        ],
    }


def replay_conformance(rows, process_id):
    if not PM4PY:
        return {"available": False,
                "reason": "pm4py not installed"}
    try:
        df = pd.DataFrame([{
            "case:concept:name": r["case_id"],
            "concept:name": r["activity"],
            "time:timestamp": r["_ts"],
            "org:resource": r.get("resource", ""),
        } for r in rows])
        df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
        log = pm4py.convert_to_event_log(pm4py.format_dataframe(
            df,
            case_id="case:concept:name",
            activity_key="concept:name",
            timestamp_key="time:timestamp"))

        discovered = inductive_miner.apply(log)
        if isinstance(discovered, tuple):
            net, im, fm = discovered
        else:
            net, im, fm = pt_converter.apply(discovered)

        replayed = token_replay.apply(log, net, im, fm)
        fit = [t["trace_fitness"] for t in replayed]
        perfect = sum(1 for t in replayed if t["trace_is_fit"])

        result = {
            "available": True,
            "algorithm": "Inductive Miner + token-based replay",
            "mean_trace_fitness": round(statistics.mean(fit), 4),
            "perfectly_fitting_cases": perfect,
            "perfectly_fitting_percentage": round(perfect / len(replayed) * 100, 1),
            "petri_net_places": len(net.places),
            "petri_net_transitions": len(net.transitions),
            "silent_transitions": sum(1 for t in net.transitions if t.label is None),
        }

        try:
            from pm4py.visualization.petri_net import visualizer as pn_vis
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            png = os.path.join(OUTPUT_DIR, f"{process_id}_inductive_miner.png")
            pn_vis.save(pn_vis.apply(net, im, fm), png)
            result["model_image"] = png
        except Exception as exc:
            result["model_image"] = None
            result["model_image_error"] = (
                f"{type(exc).__name__}: Graphviz executables not on PATH; "
                f"install Graphviz to render the Petri net")
        return result
    except Exception as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# 4. Resource analysis
# ---------------------------------------------------------------------------

def resource_analysis(rows):
    per_resource = defaultdict(list)
    activities_per_resource = defaultdict(set)
    for r in rows:
        per_resource[r["resource"]].append(r["_dur"])
        activities_per_resource[r["resource"]].add(r["activity"])

    out = []
    for resource, durs in per_resource.items():
        out.append({
            "resource": resource,
            "events": len(durs),
            "activity_types": len(activities_per_resource[resource]),
            "mean_hours": round(statistics.mean(durs), 1),
            "total_hours": round(sum(durs), 1),
        })
    out.sort(key=lambda x: x["total_hours"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------

def outcome_analysis(cases):
    approved = rejected = supplemented = 0
    for evs in cases.values():
        acts = [e["activity"] for e in evs]
        if bpmn.APPROVAL_ACTIVITY in acts:
            approved += 1
        if bpmn.REJECTION_ACTIVITY in acts:
            rejected += 1
        if bpmn.SUPPLEMENT_REQUEST_ACTIVITY in acts:
            supplemented += 1
    total = len(cases)
    return {
        "total_cases": total,
        "approved": approved,
        "approved_pct": round(approved / total * 100, 1),
        "rejected": rejected,
        "rejected_pct": round(rejected / total * 100, 1),
        "required_supplement": supplemented,
        "required_supplement_pct": round(supplemented / total * 100, 1),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def analyse(process_id, path):
    rows, cases = load_cases(path)
    result = {
        "process_id": process_id,
        "process_name": bpmn.process_name_for(process_id),
        "source_log": path,
        "events": len(rows),
        "variants": variant_analysis(cases),
        "performance": performance_analysis(rows, cases),
        "outcomes": outcome_analysis(cases),
        "resources": resource_analysis(rows),
        "conformance": {
            "structural": structural_conformance(cases, process_id),
            "replay": replay_conformance(rows, process_id),
        },
    }
    if process_id == "P2":
        sync = synchronisation_analysis(cases)
        if sync:
            result["performance"]["parallel_synchronisation"] = sync
    return result


def print_summary(a):
    pid = a["process_id"]
    v, p, o = a["variants"], a["performance"], a["outcomes"]
    print(f"\n{'=' * 66}")
    print(f"{pid}: {a['process_name']}")
    print(f"{'=' * 66}")
    print(f"  events={a['events']}  cases={v['total_cases']}  "
          f"control-flow variants={v['distinct_control_flow_variants']}  "
          f"designed variants={len(v['designed_variants'])}")
    print(f"  throughput mean={p['throughput_days']['mean']}d  "
          f"median={p['throughput_days']['median']}d  "
          f"p90={p['throughput_days']['p90']}d")
    print(f"  approved={o['approved_pct']}%  rejected={o['rejected_pct']}%  "
          f"supplement={o['required_supplement_pct']}%  "
          f"rework={p['rework_percentage']}%")
    print(f"  top bottleneck: {p['top_bottleneck']} "
          f"(mean {p['activities'][0]['mean_hours']}h, "
          f"{p['activities'][0]['share_of_total_time_pct']}% of total time)")

    sync = p.get("parallel_synchronisation")
    if sync:
        print(f"  parallel join idle wait: mean "
              f"{sync['idle_wait_hours']['mean']}h  "
              f"max {sync['idle_wait_hours']['max']}h")

    s = a["conformance"]["structural"]
    print(f"  structural conformance: {s['conformant_percentage']}% "
          f"({s['conformant_cases']}/{v['total_cases']} on designed paths)")
    r = a["conformance"]["replay"]
    if r.get("available"):
        print(f"  replay fitness: {r['mean_trace_fitness']} "
              f"({r['perfectly_fitting_percentage']}% perfectly fitting)")
        if not r.get("model_image"):
            print(f"  note: {r.get('model_image_error', 'model image not rendered')}")
    else:
        print(f"  replay fitness unavailable: {r.get('reason')}")

    print("\n  Top control-flow variants:")
    for cf in v["control_flow_variants"][:6]:
        print(f"    {cf['rank']}. {cf['cases']:>3} cases ({cf['percentage']:>4}%) "
              f"len={cf['length']}  {list(cf['designed_variants'])}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    targets = [("P1", os.path.join(VALIDATED_DIR, "p1_event_log.csv")),
               ("P2", os.path.join(VALIDATED_DIR, "p2_event_log.csv"))]

    analyses = {}
    for pid, path in targets:
        if not os.path.exists(path):
            print(f"[skip] {pid}: {path} not found -- "
                  f"run generate_logs.py then normalize_logs.py first")
            continue
        a = analyse(pid, path)
        analyses[pid] = a
        print_summary(a)

    if not analyses:
        return 1

    comparison = None
    if "P1" in analyses and "P2" in analyses:
        p1, p2 = analyses["P1"], analyses["P2"]
        comparison = {
            "throughput_ratio": round(
                p2["performance"]["throughput_days"]["mean"] /
                p1["performance"]["throughput_days"]["mean"], 2),
            "rows": [
                {"metric": "Cases",
                 "p1": p1["variants"]["total_cases"],
                 "p2": p2["variants"]["total_cases"]},
                {"metric": "Events",
                 "p1": p1["events"], "p2": p2["events"]},
                {"metric": "Control-flow variants",
                 "p1": p1["variants"]["distinct_control_flow_variants"],
                 "p2": p2["variants"]["distinct_control_flow_variants"]},
                {"metric": "Mean throughput (days)",
                 "p1": p1["performance"]["throughput_days"]["mean"],
                 "p2": p2["performance"]["throughput_days"]["mean"]},
                {"metric": "Median throughput (days)",
                 "p1": p1["performance"]["throughput_days"]["median"],
                 "p2": p2["performance"]["throughput_days"]["median"]},
                {"metric": "Approval rate (%)",
                 "p1": p1["outcomes"]["approved_pct"],
                 "p2": p2["outcomes"]["approved_pct"]},
                {"metric": "Rejection rate (%)",
                 "p1": p1["outcomes"]["rejected_pct"],
                 "p2": p2["outcomes"]["rejected_pct"]},
                {"metric": "Supplement rate (%)",
                 "p1": p1["outcomes"]["required_supplement_pct"],
                 "p2": p2["outcomes"]["required_supplement_pct"]},
                {"metric": "Rework rate (%)",
                 "p1": p1["performance"]["rework_percentage"],
                 "p2": p2["performance"]["rework_percentage"]},
                {"metric": "Top bottleneck",
                 "p1": p1["performance"]["top_bottleneck"],
                 "p2": p2["performance"]["top_bottleneck"]},
                {"metric": "Structural conformance (%)",
                 "p1": p1["conformance"]["structural"]["conformant_percentage"],
                 "p2": p2["conformance"]["structural"]["conformant_percentage"]},
            ],
        }

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pm4py_available": PM4PY,
        "processes": analyses,
        "comparison": comparison,
    }
    out = os.path.join(OUTPUT_DIR, "analytics.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\nAnalytics written: {out}")

    portal_copy = os.path.join("..", "citystart-portal", "static", "analytics.json")
    if os.path.isdir(os.path.dirname(portal_copy)):
        with open(portal_copy, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Portal copy:       {portal_copy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
