"""Deterministic Agent-facing tools shared by the CLI and MCP adapter."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, ValidationError

from .analysis import AnalysisSettings, _resolve_calibration, analyze_batch
from .evidence import attach_evidence, file_identity, verify_evidence
from .exporters import export_pdf, export_png, export_xlsx
from .parsers import inspect_spectrum_metadata, parse_spectrum
from .quality import input_gate
from .report_validation import require_exportable_analysis
from ..version import TOOL_SCHEMA_VERSION


SKILL_ROOT = Path(__file__).resolve().parents[4]
TOOL_REGISTRY_FILE = SKILL_ROOT / "schemas" / "tool-registry.json"


def tool_registry() -> dict[str, Any]:
    return json.loads(TOOL_REGISTRY_FILE.read_text(encoding="utf-8"))


def tool_definition(name: str) -> dict[str, Any]:
    for definition in tool_registry()["tools"]:
        if definition["name"] == name:
            return definition
    raise KeyError(name)


def _contract_schema(fragment: dict[str, Any]) -> dict[str, Any]:
    registry = tool_registry()
    return {"$schema": registry["$schema"], "$defs": registry["$defs"], **fragment}


ERROR_CODES = {
    "invalid_request": "The request does not satisfy the tool contract.",
    "file_not_found": "An input file does not exist.",
    "unsupported_file": "The input file format is unsupported.",
    "blocked_quality_gate": "A mandatory scientific quality gate blocked quantification.",
    "analysis_failed": "The deterministic analysis failed.",
    "invalid_evidence": "The analysis evidence fingerprint is missing or invalid.",
    "export_failed": "The report could not be exported.",
}


def envelope(tool: str, status: str, *, data: Any = None, issues: list[dict[str, Any]] | None = None,
             error_code: str | None = None, message: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": TOOL_SCHEMA_VERSION,
        "tool": tool,
        "status": status,
        "error_code": error_code,
        "message": message,
        "issues": issues or [],
        "data": data,
    }


def _required(request: dict[str, Any], name: str) -> Any:
    if name not in request:
        raise ValueError(f"Missing required field: {name}")
    return request[name]


def _read(path_value: str) -> tuple[Path, bytes]:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path, path.read_bytes()


def inspect_spectrum(request: dict[str, Any]) -> dict[str, Any]:
    path, payload = _read(str(_required(request, "path")))
    metadata = inspect_spectrum_metadata(path.name, payload)
    parsed = None
    if metadata.get("live_time_s") or request.get("live_time_s"):
        parsed = parse_spectrum(path.name, payload, request.get("live_time_s"))
    data = {
        "file": file_identity(path.name, payload, "spectrum"),
        "metadata": metadata,
        "spectrum": ({
            "channel_count": int(len(parsed.channels)),
            "first_channel": float(parsed.channels[0]),
            "last_channel": float(parsed.channels[-1]),
            "total_counts": float(parsed.counts.sum()),
            "live_time_s": parsed.live_time,
            "real_time_s": parsed.real_time,
            "dead_time_fraction": parsed.dead_time_fraction,
        } if parsed is not None else None),
        "instruction_like_document_text_ignored": True,
    }
    return envelope("inspect_spectrum", "ok", data=data)


def _settings(request: dict[str, Any]) -> AnalysisSettings:
    values = request.get("settings") or {}
    return AnalysisSettings(
        calibration_mass_g=float(values.get("calibration_mass_g", 337.76)),
        reference_date=str(values.get("reference_date", "2015-01-25")),
        reference_activities_bq={
            "Ra226": float((values.get("reference_activities_bq") or {}).get("Ra226", 903.0)),
            "Th232": float((values.get("reference_activities_bq") or {}).get("Th232", 483.0)),
            "K40": float((values.get("reference_activities_bq") or {}).get("K40", 668.0)),
        },
        roi_half_width_keV=float(values.get("roi_half_width_keV", 2.4)),
        background_gap_keV=float(values.get("background_gap_keV", 1.5)),
        background_width_keV=float(values.get("background_width_keV", 3.6)),
        correct_k_interference=bool(values.get("correct_k_interference", True)),
        assume_chain_equilibrium=bool(values.get("assume_chain_equilibrium", False)),
        apply_builtin_validation_profile=bool(values.get("apply_legacy_empirical_profile", False)),
        source_kind=str(values.get("source_kind", "custom")),
        standard_certificate_id=values.get("standard_certificate_id"),
        standard_traceable=bool(values.get("standard_traceable", False)),
        geometry_match=values.get("geometry_match"),
        matrix_match=values.get("matrix_match"),
        multi_peak_max_relative_deviation_percent=float(
            values.get("multi_peak_max_relative_deviation_percent", 30.0)
        ),
    )


def _load_analysis_inputs(request: dict[str, Any]) -> tuple[Any, list[Any], list[float], AnalysisSettings, list[dict[str, Any]]]:
    calibration_request = _required(request, "calibration")
    samples_request = _required(request, "samples")
    if not isinstance(calibration_request, dict) or not isinstance(samples_request, list) or not samples_request:
        raise ValueError("calibration must be an object and samples must be a non-empty array")
    calibration_path, calibration_payload = _read(str(_required(calibration_request, "path")))
    standard = parse_spectrum(calibration_path.name, calibration_payload, calibration_request.get("live_time_s"))
    samples = []
    masses: list[float] = []
    identities = [file_identity(calibration_path.name, calibration_payload, "calibration")]
    for item in samples_request:
        if not isinstance(item, dict):
            raise ValueError("Each sample must be an object")
        path, payload = _read(str(_required(item, "path")))
        samples.append(parse_spectrum(path.name, payload, item.get("live_time_s")))
        mass = item.get("mass_g")
        masses.append(float(mass) if mass is not None else float("nan"))
        identities.append(file_identity(path.name, payload, "sample"))
    return standard, samples, masses, _settings(request), identities


def validate_inputs(request: dict[str, Any]) -> dict[str, Any]:
    calibration_request = _required(request, "calibration")
    samples_request = _required(request, "samples")
    settings = _settings(request)
    calibration_path, calibration_payload = _read(str(_required(calibration_request, "path")))
    calibration_metadata = inspect_spectrum_metadata(calibration_path.name, calibration_payload)
    calibration_live = calibration_request.get("live_time_s") or calibration_metadata.get("live_time_s")
    identities = [file_identity(calibration_path.name, calibration_payload, "calibration")]
    masses: list[float | None] = []
    sample_live_times: list[float | None] = []
    for item in samples_request:
        path, payload = _read(str(_required(item, "path")))
        metadata = inspect_spectrum_metadata(path.name, payload)
        sample_live_times.append(item.get("live_time_s") or metadata.get("live_time_s"))
        masses.append(item.get("mass_g"))
        identities.append(file_identity(path.name, payload, "sample"))
    gate = input_gate({
        "sample_masses_g": masses,
        "sample_live_times_s": sample_live_times,
        "calibration_live_time_s": calibration_live,
        "reference_activities_bq": settings.reference_activities_bq,
    })
    supplemental: list[dict[str, Any]] = []
    if not calibration_metadata.get("acquired_at"):
        supplemental.append({
            "code": "conditional_missing_standard_acquisition_time", "severity": "conditional", "scope": "standard",
            "message": "Standard acquisition time is absent; decay correction to measurement time cannot be verified.",
        })
    if not (settings.standard_traceable and str(settings.standard_certificate_id or "").strip()):
        supplemental.append({
            "code": "conditional_unverified_standard", "severity": "conditional", "scope": "standard",
            "message": "No complete traceable certificate identity was supplied.",
        })
    if settings.geometry_match is not True:
        supplemental.append({
            "code": "conditional_unmatched_geometry", "severity": "conditional", "scope": "analysis",
            "message": "Geometry matching was not affirmatively verified.",
        })
    if settings.matrix_match is not True:
        supplemental.append({
            "code": "conditional_unmatched_matrix", "severity": "conditional", "scope": "analysis",
            "message": "Matrix compatibility was not affirmatively verified.",
        })
    if settings.apply_builtin_validation_profile:
        default_payload = (SKILL_ROOT / "assets" / "app" / "data" / "default_calibration_source.xls").read_bytes()
        if settings.source_kind != "bundled" or identities[0]["sha256"] != file_identity(
            "default_calibration_source.xls", default_payload, "calibration"
        )["sha256"]:
            gate["issues"].append({
                "code": "blocked_empirical_profile_out_of_scope", "severity": "blocking", "scope": "standard",
                "message": "The legacy empirical profile is restricted to the bundled calibration-source file.",
            })
            gate["workflow_status"] = "blocked"
    issues = gate["issues"] + supplemental
    status = "blocked" if gate["workflow_status"] == "blocked" else ("conditional_result" if issues else "ready_for_quantification")
    return envelope("validate_inputs", "ok", data={
        "workflow_status": status,
        "issues": issues,
        "input_files": identities,
        "parsed": {
            "calibration_live_time_s": calibration_live,
            "sample_live_times_s": sample_live_times,
            "sample_masses_g": masses,
        },
    }, issues=issues)


def fit_energy_calibration(request: dict[str, Any]) -> dict[str, Any]:
    path, payload = _read(str(_required(request, "path")))
    spectrum = parse_spectrum(path.name, payload, request.get("live_time_s"))
    calibration = _resolve_calibration(spectrum, request.get("calibration_spec"))
    blocked = calibration.slope <= 0 or calibration.rms_keV > 0.5
    issues = ([{
        "code": "blocked_calibration_failure", "severity": "blocking", "scope": path.name,
        "message": "Calibration slope is invalid or RMS residual exceeds 0.5 keV.",
    }] if blocked else [])
    return envelope("fit_energy_calibration", "ok", data={
        "workflow_status": "blocked" if blocked else "ready_for_quantification",
        "calibration": asdict(calibration),
        "file": file_identity(path.name, payload, "spectrum"),
    }, issues=issues)


def analyze_ra_th_k(request: dict[str, Any]) -> dict[str, Any]:
    preflight = validate_inputs(request)
    if preflight["data"]["workflow_status"] == "blocked":
        return envelope(
            "analyze_ra_th_k", "error", data={"workflow_status": "blocked"},
            issues=preflight["issues"], error_code="blocked_quality_gate",
            message="Mandatory input quality gates blocked quantification.",
        )
    standard, samples, masses, settings, identities = _load_analysis_inputs(request)
    analysis = analyze_batch(standard, samples, masses, settings, request.get("calibration_specs"))
    standard_identity = {
        "certificate_id": settings.standard_certificate_id,
        "traceable": settings.standard_traceable,
        "source_kind": settings.source_kind,
        "reference_date": settings.reference_date,
        "activities_bq": settings.reference_activities_bq,
        "geometry_match": settings.geometry_match,
        "matrix_match": settings.matrix_match,
    }
    analysis = attach_evidence(
        analysis,
        input_files=identities,
        parameters={"settings": asdict(settings), "calibration_specs": request.get("calibration_specs")},
        standard_identity=standard_identity,
    )
    issues = analysis.get("quality", {}).get("issues", [])
    blocked = analysis.get("quality", {}).get("workflow_status") == "blocked"
    return envelope(
        "analyze_ra_th_k", "error" if blocked else "ok", data=analysis, issues=issues,
        error_code="blocked_quality_gate" if blocked else None,
        message="Post-analysis quality gates blocked reportable quantification." if blocked else None,
    )


def _analysis_from_request(request: dict[str, Any]) -> dict[str, Any]:
    if isinstance(request.get("analysis"), dict):
        return request["analysis"]
    path, payload = _read(str(_required(request, "analysis_path")))
    loaded = json.loads(payload.decode("utf-8"))
    if isinstance(loaded, dict) and loaded.get("tool") == "analyze_ra_th_k":
        loaded = loaded.get("data")
    if not isinstance(loaded, dict):
        raise ValueError(f"Analysis JSON is not an object: {path}")
    return loaded


def validate_analysis(request: dict[str, Any]) -> dict[str, Any]:
    analysis = _analysis_from_request(request)
    valid, actual = verify_evidence(analysis)
    issues = list(analysis.get("quality", {}).get("issues", []))
    if not valid:
        issues.append({
            "code": "invalid_evidence", "severity": "blocking", "scope": "evidence",
            "message": "Evidence fingerprint verification failed.",
        })
    return envelope("validate_analysis", "error" if not valid else "ok", data={
        "evidence_valid": valid,
        "actual_snapshot_sha256": actual,
        "recorded_snapshot_sha256": (analysis.get("evidence") or {}).get("snapshot_sha256"),
        "workflow_status": "blocked" if not valid else analysis.get("quality", {}).get("workflow_status"),
        "issues": issues,
    }, issues=issues, error_code="invalid_evidence" if not valid else None,
                    message="Evidence fingerprint verification failed." if not valid else None)


def export_report(request: dict[str, Any]) -> dict[str, Any]:
    analysis = _analysis_from_request(request)
    require_exportable_analysis(analysis)
    format_name = str(request.get("format", "json")).lower()
    language = str(request.get("language", "zh"))
    directory = Path(str(request.get("output_directory") or Path.home() / "Desktop")).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("output_directory must be an existing directory")
    stem = str(request.get("filename_stem", "ra-th-k-analysis"))
    if stem in {".", ".."} or Path(stem).name != stem:
        raise ValueError("filename_stem must be a plain file name without path segments")
    exporters: dict[str, Callable[[dict[str, Any], str], bytes]] = {
        "xlsx": export_xlsx, "png": export_png, "pdf": export_pdf,
    }
    if format_name == "json":
        payload = json.dumps(analysis, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    elif format_name in exporters:
        payload = exporters[format_name](analysis, language)
    else:
        raise ValueError("format must be one of: json, xlsx, png, pdf")
    destination = (directory / f"{stem}.{format_name}").resolve()
    if destination.parent != directory:
        raise ValueError("Export destination escapes output_directory")
    if destination.exists() and not bool(request.get("overwrite", False)):
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
    sidecar = directory / f"{stem}.evidence.json"
    if sidecar.exists() and not bool(request.get("overwrite", False)):
        raise FileExistsError(f"Refusing to overwrite existing file: {sidecar}")
    destination.write_bytes(payload)
    sidecar.write_text(json.dumps(analysis["evidence"], ensure_ascii=False, indent=2), encoding="utf-8")
    return envelope("export_report", "ok", data={
        "report_path": str(destination),
        "evidence_path": str(sidecar),
        "snapshot_sha256": analysis["evidence"]["snapshot_sha256"],
        "workflow_status": analysis.get("quality", {}).get("workflow_status"),
    }, issues=analysis.get("quality", {}).get("issues", []))


TOOLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "inspect_spectrum": inspect_spectrum,
    "validate_inputs": validate_inputs,
    "fit_energy_calibration": fit_energy_calibration,
    "analyze_ra_th_k": analyze_ra_th_k,
    "validate_analysis": validate_analysis,
    "export_report": export_report,
}


def invoke_tool(name: str, request: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        return envelope(name, "error", error_code="invalid_request", message=f"Unknown tool: {name}")
    try:
        definition = tool_definition(name)
        Draft202012Validator(_contract_schema(definition["inputSchema"])).validate(request)
        result = TOOLS[name](request)
        Draft202012Validator(_contract_schema(definition["outputSchema"])).validate(result)
        return result
    except FileNotFoundError as exc:
        return envelope(name, "error", error_code="file_not_found", message=str(exc))
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, ValidationError) as exc:
        lowered = str(exc).lower()
        if "fingerprint" in lowered:
            code = "invalid_evidence"
        elif "blocking quality" in lowered or "quality status" in lowered or "marked reportable" in lowered:
            code = "blocked_quality_gate"
        elif "unsupported" in lowered or "not supported" in lowered or "仅支持" in str(exc):
            code = "unsupported_file"
        elif name == "export_report":
            code = "export_failed"
        else:
            code = "invalid_request"
        return envelope(name, "error", error_code=code, message=str(exc))
    except FileExistsError as exc:
        return envelope(name, "error", error_code="export_failed", message=str(exc))
    except OSError as exc:
        return envelope(name, "error", error_code="export_failed" if name == "export_report" else "analysis_failed",
                        message=str(exc))
