from __future__ import annotations

import base64
import binascii
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .services.analysis import AnalysisSettings, analyze_batch
from .services.evidence import attach_evidence, file_identity
from .services.exporters import export_pdf, export_png, export_xlsx
from .services.parameter_import import parse_analysis_parameters
from .services.parsers import inspect_spectrum_metadata, parse_spectrum
from .services.report_templates import (
    example_pdf_report_template,
    example_report_template,
    inspect_report_template,
    render_report_template,
)
from .services.report_validation import require_exportable_analysis
from .version import SKILL_VERSION


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DEFAULT_CALIBRATION_FILE = APP_DIR.parent / "data" / "default_calibration_source.xls"
PROJECT_EXPORT_DIR = APP_DIR.parents[2] / "exports"
app = FastAPI(title="Ra-Th-K Spectrum Agent", version=SKILL_VERSION)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def disable_browser_cache(request, call_next):
    """The local workbench must always load the matching HTML, CSS and JavaScript."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


class ExportRequest(BaseModel):
    analysis: dict[str, Any]
    language: Literal["zh", "zht", "en", "fr"] = "zh"
    template_name: str | None = None
    template_base64: str | None = None


class ExportSaveRequest(ExportRequest):
    directory: str


def _default_export_directory() -> Path:
    """Use the user's Desktop by default; keep the project folder as fallback."""
    home = Path.home()
    for candidate in (home / "Desktop", home / "桌面"):
        if candidate.is_dir():
            return candidate
    PROJECT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECT_EXPORT_DIR


def _unique_export_destination(directory: Path, format_name: str) -> Path:
    """Never overwrite a report that may be open and locked by Windows."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    candidate = directory / f"镭钍钾定量分析结果_{timestamp}.{format_name}"
    sequence = 1
    while candidate.exists():
        candidate = directory / f"镭钍钾定量分析结果_{timestamp}_{sequence}.{format_name}"
        sequence += 1
    return candidate


def _template_bytes(request: ExportRequest) -> tuple[str, bytes]:
    if not request.template_name or not request.template_base64:
        raise ValueError("请先在第 4 部分导入 DOCX 或可填写 PDF 报告模板。")
    try:
        content = base64.b64decode(request.template_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("报告模板数据无效，请重新导入模板。") from exc
    return request.template_name, content


def _render_export(format_name: str, request: ExportRequest) -> tuple[bytes, str]:
    require_exportable_analysis(request.analysis)
    exporters = {"xlsx": export_xlsx, "png": export_png, "pdf": export_pdf}
    if format_name in exporters:
        return exporters[format_name](request.analysis, request.language), format_name
    if format_name == "template":
        filename, template = _template_bytes(request)
        suffix = Path(filename).suffix.lower().lstrip(".")
        return render_report_template(filename, template, request.analysis, request.language), suffix
    raise KeyError(format_name)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/export-directory")
def export_directory() -> dict[str, str]:
    return {"directory": str(_default_export_directory())}


@app.post("/api/inspect")
async def inspect_files(files: list[UploadFile] = File(...)) -> dict[str, list[dict[str, Any]]]:
    inspected: list[dict[str, Any]] = []
    for upload in files:
        filename = upload.filename or "spectrum.txt"
        try:
            result = inspect_spectrum_metadata(filename, await upload.read())
            inspected.append({"name": filename, **result, "error": None})
        except (ValueError, OSError) as exc:
            inspected.append({"name": filename, "live_time_s": None, "live_time_source": None, "error": str(exc)})
    return {"files": inspected}


@app.post("/api/import-parameters")
async def import_parameters(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or "parameters.xlsx"
    try:
        return parse_analysis_parameters(filename, await file.read())
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/report-template/inspect")
async def inspect_template(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or "report-template.docx"
    try:
        return inspect_report_template(filename, await file.read())
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/report-template/example/{language}")
def download_example_template(language: Literal["zh", "zht", "en", "fr"] = "zh") -> Response:
    data = example_report_template(language)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="ra-th-k-report-template.docx"'},
    )


@app.get("/api/report-template/example-pdf")
def download_example_pdf_template() -> Response:
    return Response(
        example_pdf_report_template(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ra-th-k-fillable-report-template.pdf"'},
    )


@app.post("/api/analyze")
async def analyze(
    calibration: UploadFile | None = File(None),
    samples: list[UploadFile] = File(...),
    settings_json: str = Form("{}"),
) -> dict[str, Any]:
    try:
        request = json.loads(settings_json)
        masses = [float(value) for value in request.get("sample_masses_g", [])]
        if len(masses) != len(samples):
            raise ValueError("必须为每个样品填写质量。")
        live_times = request.get("live_times_s", {})
        use_default = bool(request.get("use_default_calibration", False))
        if use_default:
            if not DEFAULT_CALIBRATION_FILE.exists():
                raise ValueError("内置默认校准源文件不存在。")
            calibration_name = "土壤监测效率校准源.xls"
            calibration_data = DEFAULT_CALIBRATION_FILE.read_bytes()
        elif calibration is not None:
            calibration_name = calibration.filename or "calibration.txt"
            calibration_data = await calibration.read()
        else:
            raise ValueError("请选择默认刻度源或上传自定义刻度源。")
        standard = parse_spectrum(
            calibration_name, calibration_data,
            live_times.get("calibration"),
        )
        parsed_samples = []
        sample_identities: list[dict[str, Any]] = []
        for index, upload in enumerate(samples):
            content = await upload.read()
            sample_name = upload.filename or f"sample-{index + 1}.txt"
            sample_identities.append(file_identity(sample_name, content, "sample"))
            parsed_samples.append(parse_spectrum(
                sample_name, content,
                live_times.get(str(index)) or live_times.get(upload.filename or ""),
            ))
        option_data = request.get("analysis", {})
        settings = AnalysisSettings(
            calibration_mass_g=float(option_data.get("calibration_mass_g", 337.76)),
            reference_date=str(option_data.get("reference_date", "2015-01-25")),
            reference_activities_bq={
                "Ra226": float(option_data.get("ra_activity_bq", 903)),
                "Th232": float(option_data.get("th_activity_bq", 483)),
                "K40": float(option_data.get("k_activity_bq", 668)),
            },
            roi_half_width_keV=float(option_data.get("roi_half_width_keV", 2.4)),
            background_gap_keV=float(option_data.get("background_gap_keV", 1.5)),
            background_width_keV=float(option_data.get("background_width_keV", 3.6)),
            correct_k_interference=bool(option_data.get("correct_k_interference", True)),
            assume_chain_equilibrium=bool(option_data.get("assume_chain_equilibrium", True)),
            apply_builtin_validation_profile=bool(option_data.get("apply_legacy_empirical_profile", False)),
            source_kind="bundled" if use_default else "custom",
            standard_certificate_id=option_data.get("standard_certificate_id"),
            standard_traceable=bool(option_data.get("standard_traceable", False)),
            geometry_match=option_data.get("geometry_match"),
            matrix_match=option_data.get("matrix_match"),
            multi_peak_max_relative_deviation_percent=float(
                option_data.get("multi_peak_max_relative_deviation_percent", 30.0)
            ),
        )
        result = analyze_batch(standard, parsed_samples, masses, settings, request.get("calibration_specs"))
        standard_identity = {
            "certificate_id": settings.standard_certificate_id,
            "traceable": settings.standard_traceable,
            "source_kind": settings.source_kind,
            "reference_date": settings.reference_date,
            "activities_bq": settings.reference_activities_bq,
            "geometry_match": settings.geometry_match,
            "matrix_match": settings.matrix_match,
        }
        return attach_evidence(
            result,
            input_files=[file_identity(calibration_name, calibration_data, "calibration"), *sample_identities],
            parameters={"settings": asdict(settings), "calibration_specs": request.get("calibration_specs")},
            standard_identity=standard_identity,
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/export/{format_name}")
def export(format_name: str, request: ExportRequest) -> Response:
    formats = {
        "xlsx": (export_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "rtk-results.xlsx"),
        "png": (export_png, "image/png", "rtk-results.png"),
        "pdf": (export_pdf, "application/pdf", "rtk-results.pdf"),
        "template": (None, "application/octet-stream", "rtk-template-report"),
    }
    if format_name not in formats:
        raise HTTPException(status_code=404, detail="Unsupported export format")
    _, media_type, filename = formats[format_name]
    try:
        data, suffix = _render_export(format_name, request)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422 if isinstance(exc, ValueError) else 500, detail=str(exc)) from exc
    if format_name == "template":
        media_type = "application/pdf" if suffix == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"rtk-template-report.{suffix}"
    return Response(data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/export/save/{format_name}")
def save_export(format_name: str, request: ExportSaveRequest) -> dict[str, Any]:
    if format_name not in {"xlsx", "png", "pdf", "template"}:
        raise HTTPException(status_code=404, detail="Unsupported export format")
    directory = Path(request.directory).expanduser()
    if not directory.is_absolute() or not directory.is_dir():
        raise HTTPException(status_code=422, detail="导出位置必须是本机已存在的文件夹。")
    try:
        data, suffix = _render_export(format_name, request)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422 if isinstance(exc, ValueError) else 500, detail=str(exc)) from exc
    destination = _unique_export_destination(directory, suffix)
    fallback = False
    try:
        destination.write_bytes(data)
    except PermissionError:
        fallback_directory = _default_export_directory()
        destination = _unique_export_destination(fallback_directory, format_name)
        try:
            destination.write_bytes(data)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"所选目录和备用目录均无法写入：{exc}") from exc
        directory = fallback_directory
        fallback = True
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "path": str(destination), "directory": str(directory),
        "fallback": fallback, "requested_directory": request.directory,
    }
