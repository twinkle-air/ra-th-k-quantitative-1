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
    groups = {"general_model_without_skill", "instruction_only_skill", "full_tool_skill"}
    records = []
    for run in runs:
        if run.get("group") not in groups or not all(run.get(key) for key in
            ("host", "host_version", "case_id", "raw_prompt_path", "trace_path", "result_path")):
            raise ValueError("Every host run needs group, host/version, case, raw prompt, trace and result paths")
        artifacts = {}
        for key in ("raw_prompt_path", "trace_path", "result_path"):
            path = (base / run[key]).resolve()
            artifacts[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append({"host": run["host"], "host_version": run["host_version"],
                        "group": run["group"], "case_id": run["case_id"], "sha256": artifacts})
    full_hosts = {item["host"] for item in records if item["group"] == "full_tool_skill"}
    groups_seen = {item["group"] for item in records}
    return {"status": "protocol_complete" if len(full_hosts) >= 2 and groups_seen == groups else "incomplete",
            "run_count": len(records), "full_skill_host_count": len(full_hosts),
            "groups_seen": sorted(groups_seen), "records": records,
            "note": "This inventories immutable raw traces; scientific scoring and host-behavior adjudication remain separate."}


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
