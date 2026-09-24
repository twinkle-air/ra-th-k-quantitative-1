"""One report-release gate shared by browser, CLI and MCP entry points."""

from __future__ import annotations

from typing import Any

from .evidence import verify_evidence


class ReportValidationError(ValueError):
    """A report cannot be released from this analysis snapshot."""


def require_exportable_analysis(analysis: dict[str, Any]) -> None:
    valid, _ = verify_evidence(analysis)
    if not valid:
        raise ReportValidationError("Analysis evidence fingerprint is missing or invalid; export is blocked.")
    quality = analysis.get("quality") or {}
    if quality.get("workflow_status") == "blocked":
        raise ReportValidationError("Analysis has blocking quality issues; formal export is blocked.")
    if quality.get("workflow_status") not in {"ready_for_quantification", "conditional_result"}:
        raise ReportValidationError("Analysis quality status is missing or invalid; export is blocked.")
    for row in analysis.get("results", []):
        row_quality = row.get("quality") or {}
        if row_quality.get("workflow_status") == "blocked":
            raise ReportValidationError("A sample has blocking quality issues; formal export is blocked.")
        for status in (row_quality.get("nuclides") or {}).values():
            if status.get("workflow_status") != "ready_for_quantification" and status.get("reportable_activity_bq_kg") is not None:
                raise ReportValidationError("A conditional or undetected activity was marked reportable.")
