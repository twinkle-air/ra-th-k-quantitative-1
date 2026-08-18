from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .services.analysis import AnalysisSettings, analyze_batch
from .services.exporters import export_pdf, export_png, export_xlsx
from .services.parsers import inspect_spectrum_metadata, parse_spectrum


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DEFAULT_CALIBRATION_FILE = APP_DIR.parent / "data" / "default_calibration_source.xls"
app = FastAPI(title="Ra-Th-K Spectrum Agent", version="0.1.0")
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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
            raise ValueError("请选择默认校准源或上传自定义校准源。")
        standard = parse_spectrum(
            calibration_name, calibration_data,
            live_times.get("calibration"),
        )
        parsed_samples = []
        for index, upload in enumerate(samples):
            content = await upload.read()
            parsed_samples.append(parse_spectrum(
                upload.filename or f"sample-{index + 1}.txt", content,
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
            apply_builtin_validation_profile=use_default,
        )
        return analyze_batch(standard, parsed_samples, masses, settings, request.get("calibration_specs"))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/export/{format_name}")
def export(format_name: str, request: ExportRequest) -> Response:
    formats = {
        "xlsx": (export_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "rtk-results.xlsx"),
        "png": (export_png, "image/png", "rtk-results.png"),
        "pdf": (export_pdf, "application/pdf", "rtk-results.pdf"),
    }
    if format_name not in formats:
        raise HTTPException(status_code=404, detail="Unsupported export format")
    exporter, media_type, filename = formats[format_name]
    try:
        data = exporter(request.analysis, request.language)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
