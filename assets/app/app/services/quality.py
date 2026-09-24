"""Executable quality gates for Ra-Th-K quantification."""

from __future__ import annotations

import math
from typing import Any


STATUS_RANK = {"ready_for_quantification": 0, "conditional_result": 1, "blocked": 2}


def issue(code: str, severity: str, message: str, scope: str = "analysis") -> dict[str, str]:
    return {"code": code, "severity": severity, "scope": scope, "message": message}


def overall_status(issues: list[dict[str, Any]]) -> str:
    if any(item["severity"] == "blocking" for item in issues):
        return "blocked"
    if any(item["severity"] == "conditional" for item in issues):
        return "conditional_result"
    return "ready_for_quantification"


def input_gate(context: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    masses = context.get("sample_masses_g") or []
    live_times = context.get("sample_live_times_s") or []
    if not masses or any(value is None or float(value) <= 0 for value in masses):
        issues.append(issue("blocked_missing_mass", "blocking", "Every sample requires a positive net mass."))
    if not live_times or any(value is None or float(value) <= 0 for value in live_times):
        issues.append(issue("blocked_missing_live_time", "blocking", "Every spectrum requires a positive live time."))
    if not context.get("calibration_live_time_s") or float(context["calibration_live_time_s"]) <= 0:
        issues.append(issue("blocked_missing_live_time", "blocking", "The calibration spectrum requires live time.", "standard"))
    if not context.get("reference_activities_bq"):
        issues.append(issue("blocked_unverified_standard", "blocking", "Calibration-source activities are missing.", "standard"))
    return {"workflow_status": overall_status(issues), "issues": issues}


def _detection_status(row: dict[str, Any], nuclide: str) -> str:
    peaks = row.get("peaks", {}).get(nuclide, [])
    return "detected" if any(bool(peak.get("detected")) for peak in peaks) else "not_detected"


def _multi_peak_deviation(detail: list[dict[str, Any]]) -> float | None:
    values = [float(item["activity_bq_kg"]) for item in detail if math.isfinite(float(item["activity_bq_kg"]))]
    if len(values) < 2:
        return None
    center = sum(values) / len(values)
    if center == 0:
        return math.inf
    return max(abs(value - center) / abs(center) * 100.0 for value in values)


def apply_quality_gates(analysis: dict[str, Any], settings: Any) -> dict[str, Any]:
    """Mutate an analysis result with non-bypassable reportability decisions."""
    global_issues: list[dict[str, str]] = []
    standard_cal = analysis.get("standard", {}).get("calibration", {})
    if float(standard_cal.get("slope", 0.0) or 0.0) <= 0 or float(standard_cal.get("rms_keV", 0.0) or 0.0) > 0.5:
        global_issues.append(issue(
            "blocked_calibration_failure", "blocking",
            "Energy calibration is invalid or its RMS residual exceeds the 0.5 keV project policy.", "standard",
        ))
    if not (bool(getattr(settings, "standard_traceable", False)) and
            str(getattr(settings, "standard_certificate_id", "") or "").strip()):
        global_issues.append(issue(
            "conditional_unverified_standard", "conditional",
            "The standard source lacks a complete traceable certificate identity; results are conditional estimates.", "standard",
        ))
    if not analysis.get("standard", {}).get("acquired_at"):
        global_issues.append(issue(
            "conditional_missing_standard_acquisition_time", "conditional",
            "Calibration-source acquisition time is missing; reference-date activity was used without decay correction.",
            "standard",
        ))
    if getattr(settings, "geometry_match", None) is not True:
        global_issues.append(issue(
            "conditional_unmatched_geometry", "conditional",
            "Matching detector, container, fill height and counting geometry were not affirmatively verified.",
        ))
    if getattr(settings, "matrix_match", None) is not True:
        global_issues.append(issue(
            "conditional_unmatched_matrix", "conditional",
            "Matrix density and self-attenuation compatibility were not affirmatively verified.",
        ))
    profile = analysis.get("constants", {}).get("validation_profile")
    if profile:
        global_issues.append(issue(
            "conditional_legacy_empirical_profile", "conditional",
            "A legacy five-sample empirical profile is enabled; it is not independent validation evidence.",
        ))

    all_issues = list(global_issues)
    threshold = float(getattr(settings, "multi_peak_max_relative_deviation_percent", 30.0))
    for row in analysis.get("results", []):
        row_issues = list(global_issues)
        if not row.get("live_time_s") or float(row["live_time_s"]) <= 0:
            row_issues.append(issue("blocked_missing_live_time", "blocking", "Sample live time is missing.", row["name"]))
        if not row.get("mass_g") or float(row["mass_g"]) <= 0:
            row_issues.append(issue("blocked_missing_mass", "blocking", "Sample mass is missing.", row["name"]))
        sample_cal = row.get("calibration", {})
        if float(sample_cal.get("slope", 0.0) or 0.0) <= 0 or float(sample_cal.get("rms_keV", 0.0) or 0.0) > 0.5:
            row_issues.append(issue(
                "blocked_calibration_failure", "blocking",
                "Sample energy calibration is invalid or exceeds the 0.5 keV RMS project policy.", row["name"],
            ))
        base_row_issues = list(row_issues)
        nuclide_status: dict[str, Any] = {}
        for nuclide in ("Ra226", "Th232", "K40"):
            detection = _detection_status(row, nuclide)
            detail = row.get("per_peak_results", {}).get(nuclide, [])
            deviation = _multi_peak_deviation(detail) if nuclide != "K40" else None
            local_issues: list[dict[str, str]] = []
            if nuclide != "K40" and not bool(getattr(settings, "assume_chain_equilibrium", False)):
                local_issues.append(issue(
                    "conditional_unconfirmed_equilibrium", "conditional",
                    "Ra-226 and Th-232 are daughter-equivalent estimates, not direct parent activities.", nuclide,
                ))
            if detection == "not_detected":
                local_issues.append(issue(
                    "not_detected", "conditional",
                    "No selected peak exceeded the decision threshold; do not report a detected activity.", nuclide,
                ))
            if deviation is not None and deviation > threshold:
                local_issues.append(issue(
                    "conditional_multi_peak_inconsistency", "conditional",
                    f"Maximum per-peak deviation {deviation:.3g}% exceeds the {threshold:g}% project policy.", nuclide,
                ))
            parent_claim = "direct" if nuclide == "K40" else (
                "parent_activity_assumed_from_daughters" if settings.assume_chain_equilibrium else "daughter_equivalent_only"
            )
            combined = base_row_issues + local_issues
            reportable = detection == "detected" and overall_status(combined) == "ready_for_quantification"
            value = row.get("activity_bq_kg", {}).get(nuclide)
            estimate = value if value is not None and math.isfinite(float(value)) else None
            nuclide_status[nuclide] = {
                "workflow_status": overall_status(combined),
                "detection_status": detection,
                "activity_claim": parent_claim,
                "estimated_activity_bq_kg": estimate,
                "reportable_activity_bq_kg": estimate if reportable else None,
                "multi_peak_max_relative_deviation_percent": deviation,
                "issues": local_issues,
            }
            row_issues.extend(local_issues)

        row["quality"] = {
            "workflow_status": overall_status(row_issues),
            "issues": row_issues,
            "nuclides": nuclide_status,
            "policy": {
                "energy_calibration_max_rms_keV": 0.5,
                "multi_peak_max_relative_deviation_percent": threshold,
                "policy_status": "project-policy-not-normative-standard",
            },
        }
        row["counting_standard_uncertainty_bq_kg"] = row.pop("standard_uncertainty_bq_kg", {})
        row["uncertainty"] = {
            "scope": "counting_statistics_only",
            "included_components": ["sample_peak_counting", "standard_peak_counting", "observed_between-peak_scatter"],
            "excluded_components": [
                "standard_source_activity", "gamma_emission_probability", "sample_mass", "decay_correction",
                "peak_model", "efficiency_fit", "geometry_repeatability", "matrix_self_attenuation",
                "K40_interference_model",
            ],
            "combined_measurement_uncertainty_available": False,
        }
        all_issues.extend(item for item in row_issues if item not in global_issues)

    analysis["quality"] = {"workflow_status": overall_status(all_issues), "issues": all_issues}
    analysis["reporting_semantics"] = {
        "formal_activity_field": "results[*].quality.nuclides[nuclide].reportable_activity_bq_kg",
        "conditional_estimate_field": "results[*].quality.nuclides[nuclide].estimated_activity_bq_kg",
        "legacy_raw_intermediates_not_formal_results": ["results[*].activity_bq_kg", "results[*].ra_ppm",
                                                "results[*].th_ppm", "results[*].k_percent"],
        "conditional_or_undetected_formal_value": None,
    }
    return analysis
