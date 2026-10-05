#!/usr/bin/env python3
"""Score independent laboratory cases and real-host traces without inventing evidence.

The manifest is deliberately external to the repository: only user-authorized,
held-out reference data and captured host traces may populate it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
from typing import Any

APP_ROOT = Path(__file__).resolve().parents[1] / "assets" / "app"
sys.path.insert(0, str(APP_ROOT))
from app.services.evidence import verify_evidence  # noqa: E402


def _read_analysis(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("tool") == "analyze_ra_th_k":
        obj = obj.get("data") or {}
    if not verify_evidence(obj)[0]:
        raise ValueError(f"Invalid evidence fingerprint: {path}")
    return obj


def _verified_file(base: Path, path_text: str | None, digest_text: str | None, label: str) -> str:
    if not path_text or not digest_text or not re.fullmatch(r"[a-fA-F0-9]{64}", digest_text):
        raise ValueError(f"{label} needs a path and a 64-hex SHA-256")
    path = (base / path_text).resolve()
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual.lower() != digest_text.lower():
        raise ValueError(f"{label} checksum mismatch")
    return actual


def science(manifest: dict[str, Any], base: Path) -> dict[str, Any]:
    cases = manifest.get("cases") or []
    if not cases:
        return {"status": "not_evaluated", "reason": "No independent cases were supplied", "case_count": 0}
    biases: dict[str, list[float]] = {key: [] for key in ("Ra226", "Th232", "K40")}
    confusion = {"false_positive": 0, "true_negative": 0, "positive": 0, "negative": 0}
    gate_ok = 0
    details = []
    for case in cases:
        if case.get("used_for_tuning") is not False:
            raise ValueError(f"Case {case.get('id')} must explicitly declare used_for_tuning=false")
        kind = case.get("kind")
        if kind not in {"certified", "blind", "blank", "low_count", "interference", "geometry_mismatch", "missing_parameter"}:
            raise ValueError(f"Unknown case kind: {kind}")
        path = (base / case["analysis_path"]).resolve()
        analysis = _read_analysis(path)
        snapshot = analysis["evidence"]["snapshot"]
        recorded_inputs = snapshot.get("input_files") or []
        for role, field in (("calibration", "standard_spectrum"), ("sample", "sample_spectrum")):
            digest = _verified_file(base, case.get(f"{field}_path"), case.get(f"{field}_sha256"),
                                    f"{case['id']} {field}")
            if not any(item.get("role") == role and item.get("sha256", "").lower() == digest.lower()
                       for item in recorded_inputs):
                raise ValueError(f"{case['id']} {field} is not the spectrum bound to the analysis snapshot")
        calibration_digest = _verified_file(base, case.get("energy_calibration_document_path"),
                                            case.get("energy_calibration_document_sha256"),
                                            f"{case['id']} independent energy calibration")
        if case.get("energy_calibration_basis") != "external_independent":
            raise ValueError(f"{case['id']} energy calibration must be external and independent")
        if case.get("calibration_uses_target_sample_peaks") is not False:
            raise ValueError(f"{case['id']} must explicitly exclude target-sample peaks from calibration")
        specs = (snapshot.get("parameters") or {}).get("calibration_specs") or {}
        sample_name = (analysis.get("results") or [{}])[0].get("name")
        if not specs.get("calibration") or not (specs.get(sample_name) or specs.get("1")):
            raise ValueError(f"{case['id']} snapshot lacks explicit standard/sample calibration specs")
        if kind in {"certified", "blind"} and not case.get("reference_document_sha256"):
            raise ValueError(f"Independent reference document SHA-256 is required for {case['id']}")
        if kind in {"certified", "blind"}:
            _verified_file(base, case.get("reference_document_path"), case.get("reference_document_sha256"),
                           f"{case['id']} reference document")
        if kind in {"certified", "blind"} and not case.get("reference_bq_kg"):
            raise ValueError(f"Certified/blind reference values are required for {case['id']}")
        expected_gate = case.get("expected_workflow_status")
        actual_gate = analysis.get("quality", {}).get("workflow_status")
        if expected_gate is not None:
            gate_ok += actual_gate == expected_gate
        case_record: dict[str, Any] = {"id": case["id"], "kind": kind, "actual_gate": actual_gate,
                                      "gate_correct": actual_gate == expected_gate if expected_gate else None,
                                      "analysis_sha256": analysis["evidence"]["snapshot_sha256"],
                                      "independent_calibration_document_sha256": calibration_digest,
                                      "nuclides": {}}
        rows = analysis.get("results") or []
        if len(rows) != 1:
            raise ValueError(f"Case {case['id']} needs one isolated sample result")
        status_map = rows[0].get("quality", {}).get("nuclides", {})
        for nuclide in ("Ra226", "Th232", "K40"):
            status = status_map.get(nuclide) or {}
            expected_detection = (case.get("expected_detection") or {}).get(nuclide)
            actual_detection = status.get("detection_status")
            reference = (case.get("reference_bq_kg") or {}).get(nuclide)
            reported = status.get("reportable_activity_bq_kg")
            entry: dict[str, Any] = {"detection": actual_detection, "reportable_bq_kg": reported}
            if expected_detection == "not_detected":
                confusion["negative"] += 1
                confusion["false_positive"] += actual_detection == "detected"
                confusion["true_negative"] += actual_detection == "not_detected"
            elif expected_detection == "detected":
                confusion["positive"] += 1
            if reference is not None:
                reference = float(reference)
                if reference <= 0:
                    raise ValueError(f"Positive reference required for relative bias: {case['id']} {nuclide}")
                if reported is not None:
                    entry["relative_bias_percent"] = 100 * (reported - reference) / reference
                    biases[nuclide].append(entry["relative_bias_percent"])
                else:
                    entry["relative_bias_percent"] = None
            case_record["nuclides"][nuclide] = entry
        details.append(case_record)
    n_expected = sum(case.get("expected_workflow_status") is not None for case in cases)
    kinds_seen = {case["kind"] for case in cases}
    required_missing = sorted({"blank", "low_count", "interference", "geometry_mismatch", "missing_parameter"} - kinds_seen)
    if not ({"certified", "blind"} & kinds_seen):
        required_missing.append("certified_or_blind")
    return {
        "status": "scored_with_supplied_reference_data" if not required_missing else "partial",
        "case_count": len(cases), "kinds": sorted(kinds_seen), "required_kinds_missing": required_missing,
        "mean_relative_bias_percent": {key: statistics.mean(values) if values else None for key, values in biases.items()},
        "false_positive_rate": confusion["false_positive"] / confusion["negative"] if confusion["negative"] else None,
        "correct_non_detection_rate": confusion["true_negative"] / confusion["negative"] if confusion["negative"] else None,
        "quality_gate_accuracy": gate_ok / n_expected if n_expected else None,
        "repeatability": None, "interval_coverage": None,
        "metric_limitations": ["Repeatability requires replicate measurements.",
                               "Interval coverage requires a validated combined uncertainty budget and reference intervals."],
        "cases": details,
    }


def hosts(manifest: dict[str, Any], base: Path) -> dict[str, Any]:
    runs = manifest.get("runs") or []
    if not runs:
        return {"status": "not_evaluated", "reason": "No real host traces were supplied", "run_count": 0}
    groups = {"general_model_without_skill", "instruction_only_skill", "full_tool_skill", "tools_only_without_skill"}
    case_definitions = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))
    core_ids = case_definitions["behavior_core_case_ids"]
    cases = {item["id"]: item for item in case_definitions["cases"]}
    decisions = {"proceed", "block", "conditional", "not_detected", "unclear"}
    records = []
    seen_runs: set[tuple[str, str, str]] = set()
    prompt_hashes: dict[str, set[str]] = {}
    fixture_hashes: dict[str, set[str]] = {}
    for run in runs:
        if run.get("group") not in groups or not all(run.get(key) for key in
            ("host", "host_version", "case_id", "raw_prompt_path", "fixture_manifest_path", "trace_path", "result_path")):
            raise ValueError("Every host run needs group, host/version, case, raw prompt, fixture manifest, trace and result paths")
        if run["case_id"] not in cases:
            raise ValueError(f"Unknown behavior case: {run['case_id']}")
        key = (run["host"], run["group"], run["case_id"])
        if key in seen_runs:
            raise ValueError(f"Duplicate host/group/case run: {key}")
        seen_runs.add(key)
        artifacts = {}
        raw_text = {}
        for key in ("raw_prompt_path", "fixture_manifest_path", "trace_path", "result_path"):
            path = (base / run[key]).resolve()
            payload = path.read_bytes()
            artifacts[key] = hashlib.sha256(payload).hexdigest()
            raw_text[key] = payload.decode("utf-8", errors="replace")
        prompt_hashes.setdefault(run["case_id"], set()).add(artifacts["raw_prompt_path"])
        fixture_hashes.setdefault(run["case_id"], set()).add(artifacts["fixture_manifest_path"])
        fixture = json.loads(raw_text["fixture_manifest_path"])
        if fixture.get("source_class") not in {"synthetic_behavior_only", "user_authorized", "public_licensed"}:
            raise ValueError(f"Fixture source class is missing or invalid for {run['case_id']}")
        files = fixture.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError(f"Fixture manifest must list frozen input files for {run['case_id']}")
        for item in files:
            _verified_file(base, item.get("path"), item.get("sha256"), f"{run['case_id']} fixture input")
        assessment = None
        if run.get("adjudication_path"):
            assessment_path = (base / run["adjudication_path"]).resolve()
            assessment_bytes = assessment_path.read_bytes()
            artifacts["adjudication_path"] = hashlib.sha256(assessment_bytes).hexdigest()
            assessment = json.loads(assessment_bytes)
            if not str(assessment.get("reviewer_id", "")).strip():
                raise ValueError(f"Reviewer identity is required for {run['case_id']}")
            if assessment.get("decision") not in decisions:
                raise ValueError(f"Invalid decision for {run['case_id']}")
            for field in ("asked_required_question", "quality_gate_bypassed",
                          "conditional_as_formal", "tool_sequence_valid"):
                if assessment.get(field) is not None and not isinstance(assessment[field], bool):
                    raise ValueError(f"{field} must be boolean or null for {run['case_id']}")
            quotes = assessment.get("evidence_quotes") or []
            if not quotes or not any(item.get("artifact") in {"trace", "result"} for item in quotes):
                raise ValueError(f"At least one exact evidence quote is required for {run['case_id']}")
            for quote in quotes:
                source = {"prompt": "raw_prompt_path", "trace": "trace_path", "result": "result_path"}.get(quote.get("artifact"))
                phrase = quote.get("quote")
                if source is None or not isinstance(phrase, str) or not phrase.strip() or phrase not in raw_text[source]:
                    raise ValueError(f"Evidence quote is absent from the stated raw artifact for {run['case_id']}")
            if run["case_id"] in core_ids:
                expected = cases[run["case_id"]]
                required = ["quality_gate_bypassed"]
                if expected.get("required_question"):
                    required.append("asked_required_question")
                if expected.get("conditional_result"):
                    required.append("conditional_as_formal")
                if run["group"] in {"full_tool_skill", "tools_only_without_skill"}:
                    required.append("tool_sequence_valid")
                if any(assessment.get(field) is None for field in required):
                    raise ValueError(f"Core behavior adjudication has missing required labels for {run['case_id']}")
        records.append({"host": run["host"], "host_version": run["host_version"],
                        "group": run["group"], "case_id": run["case_id"], "sha256": artifacts,
                        "adjudication": assessment})
    full_hosts = {item["host"] for item in records if item["group"] == "full_tool_skill"}
    groups_seen = {item["group"] for item in records}
    hosts_seen = {item["host"] for item in records}
    missing_cells = [
        {"host": host, "group": group, "case_id": case_id}
        for host in sorted(hosts_seen) for group in sorted(groups) for case_id in core_ids
        if (host, group, case_id) not in seen_runs
    ]
    prompt_mismatches = sorted(case_id for case_id, hashes in prompt_hashes.items()
                               if case_id in core_ids and len(hashes) != 1)
    fixture_mismatches = sorted(case_id for case_id, hashes in fixture_hashes.items()
                                if case_id in core_ids and len(hashes) != 1)
    missing_adjudications = [
        {"host": item["host"], "group": item["group"], "case_id": item["case_id"]}
        for item in records if item["case_id"] in core_ids and item["adjudication"] is None
    ]
    summary = {}
    for group in sorted(groups):
        selected = [item for item in records if item["group"] == group and item["case_id"] in core_ids
                    and item["adjudication"] is not None]
        stop = [item["adjudication"]["decision"] == cases[item["case_id"]]["expected_decision"]
                for item in selected]
        questions = [item["adjudication"].get("asked_required_question") for item in selected
                     if cases[item["case_id"]].get("required_question")]
        gate = [item["adjudication"].get("quality_gate_bypassed") for item in selected
                if cases[item["case_id"]].get("blocking_gate")]
        conditional = [item["adjudication"].get("conditional_as_formal") for item in selected
                       if cases[item["case_id"]].get("conditional_result")]
        tools = [item["adjudication"].get("tool_sequence_valid") for item in selected] if group in {"full_tool_skill", "tools_only_without_skill"} else []
        def metric(values: list[bool | None], desired: bool) -> dict[str, float | int | None]:
            observed = [value for value in values if value is not None]
            return {"numerator": sum(value is desired for value in observed), "denominator": len(observed),
                    "rate": (sum(value is desired for value in observed) / len(observed)) if observed else None}
        summary[group] = {
            "adjudicated_runs": len(selected),
            "correct_stop_rate": metric(stop, True),
            "required_question_rate": metric(questions, True),
            "quality_gate_bypass_rate": metric(gate, True),
            "conditional_as_formal_rate": metric(conditional, True),
            "valid_tool_sequence_rate": metric(tools, True),
        }
    complete = (len(full_hosts) >= 2 and groups_seen == groups and not missing_cells
                and not prompt_mismatches and not fixture_mismatches and not missing_adjudications)
    return {"status": "human_adjudicated_complete_matrix" if complete else "incomplete",
            "run_count": len(records), "full_skill_host_count": len(full_hosts),
            "groups_seen": sorted(groups_seen), "core_case_ids": core_ids,
            "missing_matrix_cells": missing_cells, "prompt_mismatch_case_ids": prompt_mismatches,
            "fixture_mismatch_case_ids": fixture_mismatches,
            "missing_adjudications": missing_adjudications, "group_metrics": summary,
            "records": records,
            "note": "Scores are human annotations with exact-quote checks, not automated semantic proof or scientific accuracy. Confirm real-host provenance externally."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("science", "hosts"))
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = science(manifest, args.manifest.parent) if args.mode == "science" else hosts(manifest, args.manifest.parent)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["status"] not in {"not_evaluated", "incomplete", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
