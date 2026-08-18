from __future__ import annotations

from io import BytesIO
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_LANGUAGES = {"zh", "zht", "en", "fr"}

_TEXT = {
    "zh": {
        "channel": "道址 CH", "energy": "能量 / keV", "fitted_line": "拟合直线", "matched_points": "刻度匹配点",
        "summary_sheet": "结果总览", "summary_title": "镭、钍、钾含量分析结果总览表", "spectrum": "谱线编号", "file": "文件名", "mass_g": "质量 (g)",
        "activity_sheet": "比活度", "activity_title": "测试样镭钍钾比活度结果", "sample": "样品", "mass_kg": "质量 / kg", "activity_comparison": "多样品比活度对比",
        "peak_sheet": "特征峰参考", "analyte": "分析核素", "emitter": "实际发射体", "reference_energy": "参考能量 (keV)", "default_channel": "默认源参考道址",
        "calibration_sheet": "能量刻度", "calibration_equation": "刻度方程", "correlation": "相关系数 R", "deviation": "偏差 (%)", "matched_count": "匹配点数",
        "calibration_charts": "能量刻度拟合图", "editable_chart": "可编辑图表", "process_sheet": "过程明细", "observed_channel": "实际峰位道址", "converted_energy": "换算能量 (keV)",
        "gross": "总计数", "background": "本底计数", "net": "净计数", "net_rate": "净计数率 (cps)", "method_sheet": "方法与质控", "method": "方法", "validity": "适用条件", "machine_record": "完整机器记录",
        "ra_conversion": "Ra 换算", "th_conversion": "Th 换算", "k_conversion": "K 换算", "content_results": "镭、钍、钾含量结果", "calibration_qc": "能量刻度拟合质控", "calibration_curves": "能量刻度拟合曲线",
        "peak_analysis": "特征峰数据分析", "analyte_emitter": "分析对象（发射体）", "reference": "参考能量", "observed_short": "实际道址", "converted_short": "换算能量",
        "note": "注：Ra/Th 由子体峰估计；需满足衰变链平衡及样品—校准源几何/基质匹配。", "report_title": "镭、钍、钾定量分析报告", "traceable_detail": "分析过程与可追溯中间量", "primary_reference": "主要特征峰参考数据",
        "method_value": "经验证的同几何比较法；K-40 使用 Ra/Th 幂律效率外推", "validity_value": "Ra/Th由子体峰估计；结果有效性依赖衰变链平衡、几何与基质匹配。",
    },
    "zht": {
        "channel": "道址 CH", "energy": "能量 / keV", "fitted_line": "擬合直線", "matched_points": "刻度匹配點",
        "summary_sheet": "結果總覽", "summary_title": "鐳、釷、鉀含量分析結果總覽表", "spectrum": "譜線編號", "file": "檔案名稱", "mass_g": "質量 (g)",
        "activity_sheet": "比活度", "activity_title": "測試樣鐳釷鉀比活度結果", "sample": "樣品", "mass_kg": "質量 / kg", "activity_comparison": "多樣品比活度比較",
        "peak_sheet": "特徵峰參考", "analyte": "分析核素", "emitter": "實際發射體", "reference_energy": "參考能量 (keV)", "default_channel": "預設源參考道址",
        "calibration_sheet": "能量刻度", "calibration_equation": "刻度方程", "correlation": "相關係數 R", "deviation": "偏差 (%)", "matched_count": "匹配點數",
        "calibration_charts": "能量刻度擬合圖", "editable_chart": "可編輯圖表", "process_sheet": "過程明細", "observed_channel": "實際峰位道址", "converted_energy": "換算能量 (keV)",
        "gross": "總計數", "background": "本底計數", "net": "淨計數", "net_rate": "淨計數率 (cps)", "method_sheet": "方法與品管", "method": "方法", "validity": "適用條件", "machine_record": "完整機器紀錄",
        "ra_conversion": "Ra 換算", "th_conversion": "Th 換算", "k_conversion": "K 換算", "content_results": "鐳、釷、鉀含量結果", "calibration_qc": "能量刻度擬合品管", "calibration_curves": "能量刻度擬合曲線",
        "peak_analysis": "特徵峰資料分析", "analyte_emitter": "分析對象（發射體）", "reference": "參考能量", "observed_short": "實際道址", "converted_short": "換算能量",
        "note": "註：Ra/Th 由子體峰估計；需滿足衰變鏈平衡及樣品—校準源幾何/基質匹配。", "report_title": "鐳、釷、鉀定量分析報告", "traceable_detail": "分析過程與可追溯中間量", "primary_reference": "主要特徵峰參考資料",
        "method_value": "經驗證的同幾何比較法；K-40 使用 Ra/Th 冪律效率外推", "validity_value": "Ra/Th 由子體峰估計；結果有效性依賴衰變鏈平衡、幾何與基質匹配。",
    },
    "en": {
        "channel": "Channel CH", "energy": "Energy / keV", "fitted_line": "Fitted line", "matched_points": "Matched points",
        "summary_sheet": "Summary", "summary_title": "Ra, Th and K Quantitative Results", "spectrum": "Spectrum", "file": "File", "mass_g": "Mass (g)",
        "activity_sheet": "Specific Activity", "activity_title": "Sample Ra-Th-K Specific Activity Results", "sample": "Sample", "mass_kg": "Mass / kg", "activity_comparison": "Specific Activity Comparison",
        "peak_sheet": "Peak Reference", "analyte": "Analyte", "emitter": "Actual emitter", "reference_energy": "Reference energy (keV)", "default_channel": "Default-source channel",
        "calibration_sheet": "Energy Calibration", "calibration_equation": "Calibration equation", "correlation": "Correlation R", "deviation": "Deviation (%)", "matched_count": "Matched points",
        "calibration_charts": "Calibration Fit Charts", "editable_chart": "Editable chart", "process_sheet": "Process Detail", "observed_channel": "Observed channel", "converted_energy": "Converted energy (keV)",
        "gross": "Gross", "background": "Background", "net": "Net", "net_rate": "Net rate (cps)", "method_sheet": "Method & QC", "method": "Method", "validity": "Validity", "machine_record": "Machine record",
        "ra_conversion": "Ra conversion", "th_conversion": "Th conversion", "k_conversion": "K conversion", "content_results": "Ra, Th and K Content Results", "calibration_qc": "Energy Calibration Fit QC", "calibration_curves": "Energy Calibration Fit Curves",
        "peak_analysis": "Gamma-line Analysis", "analyte_emitter": "Analyte (emitter)", "reference": "Reference", "observed_short": "Channel", "converted_short": "Converted",
        "note": "Note: Ra/Th use daughter peaks; chain equilibrium and matched geometry/matrix are required.", "report_title": "Ra, Th and K Quantitative Analysis Report", "traceable_detail": "Traceable Analysis Detail", "primary_reference": "Primary Gamma-line Reference",
        "method_value": "validated same-geometry comparison; K-40 uses Ra/Th power-law efficiency extrapolation", "validity_value": "Ra/Th are inferred from daughter peaks; validity requires chain equilibrium and matched geometry/matrix.",
    },
    "fr": {
        "channel": "Canal CH", "energy": "Énergie / keV", "fitted_line": "Droite ajustée", "matched_points": "Points appariés",
        "summary_sheet": "Synthèse", "summary_title": "Résultats quantitatifs Ra, Th et K", "spectrum": "Spectre", "file": "Fichier", "mass_g": "Masse (g)",
        "activity_sheet": "Activité massique", "activity_title": "Activités massiques Ra–Th–K des échantillons", "sample": "Échantillon", "mass_kg": "Masse / kg", "activity_comparison": "Comparaison des activités massiques",
        "peak_sheet": "Référence des raies", "analyte": "Analyte", "emitter": "Émetteur réel", "reference_energy": "Énergie de référence (keV)", "default_channel": "Canal de la source intégrée",
        "calibration_sheet": "Étalonnage en énergie", "calibration_equation": "Équation d’étalonnage", "correlation": "Corrélation R", "deviation": "Écart (%)", "matched_count": "Points appariés",
        "calibration_charts": "Courbes d’étalonnage", "editable_chart": "Graphique modifiable", "process_sheet": "Détails du traitement", "observed_channel": "Canal observé", "converted_energy": "Énergie convertie (keV)",
        "gross": "Brut", "background": "Fond", "net": "Net", "net_rate": "Taux net (cps)", "method_sheet": "Méthode et CQ", "method": "Méthode", "validity": "Validité", "machine_record": "Enregistrement machine",
        "ra_conversion": "Conversion Ra", "th_conversion": "Conversion Th", "k_conversion": "Conversion K", "content_results": "Teneurs en Ra, Th et K", "calibration_qc": "CQ de l’étalonnage en énergie", "calibration_curves": "Courbes d’ajustement en énergie",
        "peak_analysis": "Analyse des raies gamma", "analyte_emitter": "Analyte (émetteur)", "reference": "Référence", "observed_short": "Canal", "converted_short": "Énergie calculée",
        "note": "Note : Ra/Th sont estimés par les raies des descendants ; l’équilibre et l’adéquation géométrie/matrice sont requis.", "report_title": "Rapport d’analyse quantitative Ra, Th et K", "traceable_detail": "Détails traçables de l’analyse", "primary_reference": "Référence des principales raies gamma",
        "method_value": "comparaison validée à géométrie identique ; K-40 utilise une extrapolation d’efficacité en loi de puissance Ra/Th", "validity_value": "Ra/Th sont estimés à partir des descendants ; la validité exige l’équilibre des chaînes et l’adéquation de la géométrie et de la matrice.",
    },
}


def _tr(language: str, key: str) -> str:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported export language: {language}")
    return _TEXT[language][key]


def _number(value: Any, digits: int = 4) -> str:
    if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
        return "—"
    return f"{value:.{digits}g}"


def _nuclide_label(value: Any) -> str:
    """Use the conventional hyphenated mass-number notation in reports."""
    text = str(value)
    return {"Ra226": "Ra-226", "Th232": "Th-232", "K40": "K-40"}.get(text, text)


def _calibration_plot_data(item: dict[str, Any]) -> tuple[list[tuple[float, float]], float, float, float, float]:
    """Return finite calibration points and two endpoints for the fitted line."""
    calibration = item.get("calibration", {})
    points: list[tuple[float, float]] = []
    for point in calibration.get("matched_points", []) or []:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        channel, energy = point[0], point[1]
        if isinstance(channel, (int, float)) and isinstance(energy, (int, float)) and math.isfinite(channel) and math.isfinite(energy):
            points.append((float(channel), float(energy)))
    preview_channels = [value for value in item.get("preview", {}).get("channels", [])
                        if isinstance(value, (int, float)) and math.isfinite(value)]
    candidates = [point[0] for point in points] + preview_channels
    x_min = min(candidates, default=0.0)
    x_max = max(candidates, default=1.0)
    if x_max <= x_min:
        x_max = x_min + 1.0
    slope = calibration.get("slope")
    intercept = calibration.get("intercept")
    slope = float(slope) if isinstance(slope, (int, float)) and math.isfinite(slope) else 1.0
    intercept = float(intercept) if isinstance(intercept, (int, float)) and math.isfinite(intercept) else 0.0
    return points, x_min, x_max, slope * x_min + intercept, slope * x_max + intercept


def _calibration_fit_image(item: dict[str, Any], language: str) -> BytesIO:
    """Render a compatibility-first calibration plot for embedding in Excel/WPS."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1200, 480
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype(_font_path(), 18)
    small = ImageFont.truetype(_font_path(), 15)
    points, x_min, x_max, fitted_min, fitted_max = _calibration_plot_data(item)
    observed = [point[1] for point in points]
    y_min = min([fitted_min, fitted_max, *observed], default=0.0)
    y_max = max([fitted_min, fitted_max, *observed], default=1.0)
    if y_max <= y_min:
        y_max = y_min + 1.0
    left, right, top, bottom = 94, width - 38, 66, height - 62
    x_span, y_span = x_max - x_min, y_max - y_min
    px = lambda value: left + (value - x_min) / x_span * (right - left)
    py = lambda value: bottom - (value - y_min) / y_span * (bottom - top)
    for tick in range(6):
        x_value = x_min + x_span * tick / 5
        y_value = y_min + y_span * tick / 5
        xx, yy = px(x_value), py(y_value)
        draw.line((xx, top, xx, bottom), fill="#DFE8E6", width=1)
        draw.line((left, yy, right, yy), fill="#DFE8E6", width=1)
        draw.text((xx, bottom + 22), _number(x_value, 5), font=small, fill="#627782", anchor="mm")
        draw.text((left - 11, yy), _number(y_value, 5), font=small, fill="#627782", anchor="rm")
    draw.line((px(x_min), py(fitted_min), px(x_max), py(fitted_max)), fill="#176B70", width=4)
    for channel, energy in points:
        xx, yy = px(channel), py(energy)
        draw.ellipse((xx - 6, yy - 6, xx + 6, yy + 6), fill="#CF7A14", outline="#FFFFFF", width=2)
    draw.text(((left + right) / 2, height - 18), _tr(language, "channel"), font=regular, fill="#506873", anchor="mm")
    draw.text((20, (top + bottom) / 2), _tr(language, "energy"), font=regular, fill="#506873", anchor="lm")
    draw.line((width - 430, 28, width - 395, 28), fill="#176B70", width=4)
    draw.text((width - 382, 28), _tr(language, "fitted_line"), font=regular, fill="#506873", anchor="lm")
    draw.ellipse((width - 205, 21, width - 191, 35), fill="#CF7A14", outline="#FFFFFF", width=2)
    draw.text((width - 180, 28), f"{_tr(language, 'matched_points')} ({len(points)})", font=regular, fill="#506873", anchor="lm")
    stream = BytesIO()
    image.save(stream, "PNG", dpi=(160, 160))
    stream.seek(0)
    return stream


def export_xlsx(analysis: dict[str, Any], language: str = "zh") -> bytes:
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, Reference, ScatterChart, Series
    from openpyxl.drawing.image import Image as SpreadsheetImage
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    _tr(language, "summary_title")
    wb = Workbook()
    ws = wb.active
    ws.title = _tr(language, "summary_sheet")
    title = _tr(language, "summary_title")
    headers = [_tr(language, "spectrum"), _tr(language, "file"), "Ra (ppm)", "Th (ppm)", "K (%)", _tr(language, "mass_g")]
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    ws.cell(1, 1, title)
    ws.cell(1, 1).font = Font(size=16, bold=True, color="17324D")
    ws.cell(1, 1).alignment = Alignment(horizontal="center")
    for col, value in enumerate(headers, 1):
        cell = ws.cell(3, col, value)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="176B70")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for row, item in enumerate(analysis.get("results", []), 4):
        values = [item.get("spectrum_no"), item.get("name"), item.get("ra_ppm"), item.get("th_ppm"),
                  item.get("k_percent"), item.get("mass_g")]
        for col, value in enumerate(values, 1):
            ws.cell(row, col, value)
            ws.cell(row, col).alignment = Alignment(horizontal="center")
    thin = Side(style="thin", color="7C8C96")
    for row in ws.iter_rows(min_row=3, max_row=max(3, ws.max_row), min_col=1, max_col=len(headers)):
        for cell in row:
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    widths = [13, 28, 18, 18, 18, 14]
    for index, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + index)].width = width
    ws.freeze_panes = "A4"

    activity = wb.create_sheet(_tr(language, "activity_sheet"))
    activity_title = _tr(language, "activity_title")
    activity_headers = [_tr(language, "sample"), _tr(language, "mass_kg"), "Th-232 / (Bq/kg)", "Ra-226 / (Bq/kg)", "K-40 / (Bq/kg)"]
    activity.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    activity.cell(1, 1, activity_title)
    activity.cell(1, 1).font = Font(size=16, bold=True, color="17324D")
    activity.cell(1, 1).alignment = Alignment(horizontal="center")
    for col, value in enumerate(activity_headers, 1):
        cell = activity.cell(3, col, value)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="176B70")
        cell.alignment = Alignment(horizontal="center")
    for row, item in enumerate(analysis.get("results", []), 4):
        values = [item.get("name"), item.get("mass_g", 0) / 1000,
                  item.get("activity_bq_kg", {}).get("Th232"), item.get("activity_bq_kg", {}).get("Ra226"),
                  item.get("activity_bq_kg", {}).get("K40")]
        for col, value in enumerate(values, 1):
            activity.cell(row, col, value)
            activity.cell(row, col).alignment = Alignment(horizontal="center")
    for row in activity.iter_rows(min_row=3, max_row=max(3, activity.max_row), min_col=1, max_col=5):
        for cell in row:
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for column, width in zip("ABCDE", [28, 16, 25, 25, 25]):
        activity.column_dimensions[column].width = width
    if len(analysis.get("results", [])) > 1:
        chart = BarChart()
        chart.type = "col"
        chart.style = 10
        chart.title = _tr(language, "activity_comparison")
        chart.y_axis.title = "Bq/kg"
        chart.x_axis.title = _tr(language, "sample")
        chart.add_data(Reference(activity, min_col=3, max_col=5, min_row=3, max_row=activity.max_row), titles_from_data=True)
        chart.set_categories(Reference(activity, min_col=1, min_row=4, max_row=activity.max_row))
        chart.height = 10
        chart.width = 22
        activity.add_chart(chart, "A10")

    reference = wb.create_sheet(_tr(language, "peak_sheet"))
    reference_headers = [_tr(language, "analyte"), _tr(language, "emitter"), _tr(language, "reference_energy"), _tr(language, "default_channel")]
    reference.append(reference_headers)
    for peak in analysis.get("peak_references", []):
        reference.append([_nuclide_label(peak.get("nuclide")), peak.get("emitter"), peak.get("energy_keV"), peak.get("default_reference_channel")])
    for cell in reference[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="176B70")
    for column in "ABCD":
        reference.column_dimensions[column].width = 26

    calibration_sheet = wb.create_sheet(_tr(language, "calibration_sheet"))
    calibration_headers = [_tr(language, "spectrum"), _tr(language, "file"), _tr(language, "calibration_equation"), _tr(language, "correlation"), _tr(language, "deviation"), "RMS (keV)", _tr(language, "matched_count")]
    calibration_sheet.append(calibration_headers)
    for item in analysis.get("results", []):
        calibration = item.get("calibration", {})
        formula = f"E = {_number(calibration.get('slope'), 8)} × CH + {_number(calibration.get('intercept'), 8)} keV"
        calibration_sheet.append([
            item.get("spectrum_no"), item.get("name"), formula, calibration.get("correlation_r"),
            calibration.get("relative_deviation_percent"), calibration.get("rms_keV"),
            len(calibration.get("matched_points", [])),
        ])
    for cell in calibration_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="176B70")
    for column, width in zip("ABCDEFG", [14, 28, 52, 18, 18, 16, 14]):
        calibration_sheet.column_dimensions[column].width = width
    calibration_sheet.freeze_panes = "A2"

    calibration_charts = wb.create_sheet(_tr(language, "calibration_charts"))
    calibration_charts.sheet_view.showGridLines = False
    image_streams: list[BytesIO] = []
    for index, item in enumerate(analysis.get("results", [])):
        points, x_min, x_max, y_min, y_max = _calibration_plot_data(item)
        data_col = 45 + index * 5
        headers_row = 1
        calibration_charts.cell(headers_row, data_col, "CH")
        calibration_charts.cell(headers_row, data_col + 1, "Energy / keV")
        calibration_charts.cell(headers_row, data_col + 2, "Fit CH")
        calibration_charts.cell(headers_row, data_col + 3, "Fit energy / keV")
        for row_index, (channel, energy) in enumerate(points, 2):
            calibration_charts.cell(row_index, data_col, channel)
            calibration_charts.cell(row_index, data_col + 1, energy)
        calibration_charts.cell(2, data_col + 2, x_min)
        calibration_charts.cell(2, data_col + 3, y_min)
        calibration_charts.cell(3, data_col + 2, x_max)
        calibration_charts.cell(3, data_col + 3, y_max)
        chart = ScatterChart()
        chart.title = f"{item.get('spectrum_no')}. {item.get('name')}"
        chart.style = 13
        chart.x_axis.title = _tr(language, "channel")
        chart.y_axis.title = _tr(language, "energy")
        chart.height = 10
        chart.width = 22
        chart.visible_cells_only = False
        if points:
            point_series = Series(
                Reference(calibration_charts, min_col=data_col + 1, min_row=2, max_row=len(points) + 1),
                Reference(calibration_charts, min_col=data_col, min_row=2, max_row=len(points) + 1),
                title=_tr(language, "matched_points"),
            )
            point_series.marker.symbol = "circle"
            point_series.graphicalProperties.line.noFill = True
            chart.series.append(point_series)
        fit_series = Series(
            Reference(calibration_charts, min_col=data_col + 3, min_row=2, max_row=3),
            Reference(calibration_charts, min_col=data_col + 2, min_row=2, max_row=3),
            title=_tr(language, "fitted_line"),
        )
        fit_series.marker.symbol = "none"
        fit_series.graphicalProperties.line.solidFill = "176B70"
        fit_series.graphicalProperties.line.width = 22000
        chart.series.append(fit_series)
        calibration = item.get("calibration", {})
        formula = f"E = {_number(calibration.get('slope'), 8)} × CH + {_number(calibration.get('intercept'), 8)} keV"
        quality = f"{_tr(language, 'correlation')} = {_number(calibration.get('correlation_r'), 8)} / {_tr(language, 'deviation')} = {_number(calibration.get('relative_deviation_percent'), 6)}% / RMS = {_number(calibration.get('rms_keV'), 6)} keV"
        anchor_row = 1 + index * 32
        calibration_charts.cell(anchor_row, 1, formula).font = Font(bold=True, color="17324D")
        calibration_charts.cell(anchor_row + 1, 1, quality).font = Font(color="176B70")
        image_stream = _calibration_fit_image(item, language)
        image_streams.append(image_stream)
        plot_image = SpreadsheetImage(image_stream)
        plot_image.width = 900
        plot_image.height = 360
        calibration_charts.add_image(plot_image, f"A{anchor_row + 2}")
        calibration_charts.cell(anchor_row, 14, _tr(language, "editable_chart")).font = Font(bold=True, color="17324D")
        calibration_charts.add_chart(chart, f"N{anchor_row + 2}")
    calibration_charts.column_dimensions["A"].width = 100

    detail = wb.create_sheet(_tr(language, "process_sheet"))
    detail_headers = [_tr(language, "spectrum"), _tr(language, "analyte"), _tr(language, "emitter"), _tr(language, "reference_energy"), _tr(language, "observed_channel"), _tr(language, "converted_energy"), _tr(language, "gross"), _tr(language, "background"), _tr(language, "net"), _tr(language, "net_rate")]
    detail.append(detail_headers)
    for item in analysis.get("results", []):
        for nuclide, peaks in item.get("peaks", {}).items():
            for peak in peaks:
                center = peak.get("center_channel")
                detail.append([item.get("spectrum_no"), _nuclide_label(nuclide), peak.get("emitter"), peak.get("energy_keV"), center,
                               peak.get("converted_energy_keV"),
                               peak.get("gross_counts"), peak.get("background_counts"), peak.get("net_counts"), peak.get("net_cps")])
    for cell in detail[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="176B70")
    detail.freeze_panes = "A2"
    for col in range(1, len(detail_headers) + 1):
        detail.column_dimensions[chr(64 + col)].width = 20

    meta = wb.create_sheet(_tr(language, "method_sheet"))
    method_rows = [
        (_tr(language, "method"), _tr(language, "method_value")),
        (_tr(language, "ra_conversion"), "Ra (ppm) = A(Ra-226) / 36600"),
        (_tr(language, "th_conversion"), "Th (ppm) = A(Th-232) / 4.056"),
        (_tr(language, "k_conversion"), "K (%) = A(K-40) / 311"),
        (_tr(language, "validity"), _tr(language, "validity_value")),
        (_tr(language, "machine_record"), json.dumps(analysis.get("constants", {}), ensure_ascii=False)),
    ]
    for row in method_rows:
        meta.append(row)
    meta.column_dimensions["A"].width = 22
    meta.column_dimensions["B"].width = 110
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


def _font_path() -> str:
    candidates = [Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/arial.ttf")]
    return str(next((path for path in candidates if path.exists()), candidates[-1]))


def export_png(analysis: dict[str, Any], language: str = "zh") -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    _tr(language, "report_title")
    rows = analysis.get("results", [])
    peak_count = sum(len(peaks) for item in rows for peaks in item.get("peaks", {}).values())
    width, row_h = 1600, 58
    chart_height = 470 if len(rows) > 1 else 0
    fit_charts_height = len(rows) * 500
    height = max(1000, 150 + (len(rows) + 1) * row_h * 3 + fit_charts_height + chart_height + (peak_count + 1) * row_h + 430)
    image = Image.new("RGB", (width, height), "#F7F9F8")
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype(_font_path(), 22)
    small = ImageFont.truetype(_font_path(), 18)
    bold = ImageFont.truetype(_font_path(), 24)
    title_font = ImageFont.truetype(_font_path(), 40)
    title = _tr(language, "report_title")
    draw.text((width / 2, 62), title, font=title_font, fill="#17324D", anchor="mm")

    def table(y: int, section_title: str, headers: list[str], values: list[list[Any]], widths: list[int]) -> int:
        draw.text((50, y), section_title, font=bold, fill="#17324D")
        y += 42
        positions = [50]
        for cell_width in widths:
            positions.append(positions[-1] + cell_width)
        draw.rounded_rectangle((50, y, positions[-1], y + row_h), 9, fill="#176B70")
        for col, header in enumerate(headers):
            draw.text(((positions[col] + positions[col + 1]) / 2, y + row_h / 2), header, font=small, fill="white", anchor="mm")
        for ridx, row in enumerate(values, 1):
            current_y = y + ridx * row_h
            draw.rectangle((50, current_y, positions[-1], current_y + row_h), fill="#FFFFFF" if ridx % 2 else "#EAF1EF")
            for col, value in enumerate(row):
                text_value = str(value)
                if len(text_value) > 24:
                    text_value = text_value[:22] + "…"
                draw.text(((positions[col] + positions[col + 1]) / 2, current_y + row_h / 2), text_value, font=small, fill="#243B4A", anchor="mm")
        bottom = y + (len(values) + 1) * row_h
        for x in positions:
            draw.line((x, y, x, bottom), fill="#799099", width=1)
        draw.line((50, bottom, positions[-1], bottom), fill="#799099", width=1)
        return bottom + 34

    y = 125
    content_headers = [_tr(language, "spectrum"), _tr(language, "file"), "Ra (ppm)", "Th (ppm)", "K (%)"]
    content_values = [[item.get("spectrum_no"), item.get("name"), _number(item.get("ra_ppm")),
                       _number(item.get("th_ppm")), _number(item.get("k_percent"))] for item in rows]
    y = table(y, _tr(language, "content_results"), content_headers, content_values,
              [170, 530, 280, 280, 280])
    activity_headers = [_tr(language, "sample"), _tr(language, "mass_kg"), "Th-232 / Bq/kg", "Ra-226 / Bq/kg", "K-40 / Bq/kg"]
    activity_values = [[item.get("name"), _number(item.get("mass_g", 0) / 1000, 6),
                        _number(item.get("activity_bq_kg", {}).get("Th232"), 7),
                        _number(item.get("activity_bq_kg", {}).get("Ra226"), 7),
                        _number(item.get("activity_bq_kg", {}).get("K40"), 7)] for item in rows]
    y = table(y, _tr(language, "activity_title"), activity_headers,
              activity_values, [360, 220, 320, 320, 320])

    calibration_headers = [_tr(language, "sample"), _tr(language, "calibration_equation"), _tr(language, "correlation"), _tr(language, "deviation"), "RMS / keV"]
    calibration_values = []
    for item in rows:
        calibration = item.get("calibration", {})
        formula = f"E = {_number(calibration.get('slope'), 8)} × CH + {_number(calibration.get('intercept'), 8)}"
        calibration_values.append([
            item.get("name"), formula, _number(calibration.get("correlation_r"), 8),
            _number(calibration.get("relative_deviation_percent"), 6), _number(calibration.get("rms_keV"), 6),
        ])
    y = table(y, _tr(language, "calibration_qc"), calibration_headers,
              calibration_values, [260, 570, 240, 220, 250])

    if rows:
        draw.text((50, y), _tr(language, "calibration_curves"), font=bold, fill="#17324D")
        y += 46
    for item in rows:
        calibration = item.get("calibration", {})
        points, x_min, x_max, fitted_min, fitted_max = _calibration_plot_data(item)
        plot_left, plot_right = 150, 1520
        plot_top, plot_bottom = y + 78, y + 390
        observed_energies = [point[1] for point in points]
        y_min = min([fitted_min, fitted_max, *observed_energies], default=0.0)
        y_max = max([fitted_min, fitted_max, *observed_energies], default=1.0)
        if y_max <= y_min:
            y_max = y_min + 1.0
        x_span, y_span = x_max - x_min, y_max - y_min
        px = lambda value: plot_left + (value - x_min) / x_span * (plot_right - plot_left)
        py = lambda value: plot_bottom - (value - y_min) / y_span * (plot_bottom - plot_top)
        formula = f"E = {_number(calibration.get('slope'), 8)} × CH + {_number(calibration.get('intercept'), 8)} keV"
        quality = f"{_tr(language, 'correlation')} = {_number(calibration.get('correlation_r'), 8)} / {_tr(language, 'deviation')} = {_number(calibration.get('relative_deviation_percent'), 6)}% / RMS = {_number(calibration.get('rms_keV'), 6)} keV"
        draw.text((50, y), f"{item.get('spectrum_no')}. {item.get('name')}", font=bold, fill="#17324D")
        draw.text((420, y + 2), formula, font=small, fill="#176B70")
        draw.text((420, y + 31), quality, font=small, fill="#506873")
        draw.rounded_rectangle((50, y + 62, 1550, y + 430), 8, fill="#FFFFFF", outline="#C7D6D4", width=1)
        for tick in range(6):
            x_value = x_min + x_span * tick / 5
            y_value = y_min + y_span * tick / 5
            xx, yy = px(x_value), py(y_value)
            draw.line((xx, plot_top, xx, plot_bottom), fill="#DFE8E6", width=1)
            draw.line((plot_left, yy, plot_right, yy), fill="#DFE8E6", width=1)
            draw.text((xx, plot_bottom + 22), _number(x_value, 5), font=small, fill="#627782", anchor="mm")
            draw.text((plot_left - 14, yy), _number(y_value, 5), font=small, fill="#627782", anchor="rm")
        draw.line((px(x_min), py(fitted_min), px(x_max), py(fitted_max)), fill="#176B70", width=4)
        for channel, energy in points:
            xx, yy = px(channel), py(energy)
            draw.ellipse((xx - 6, yy - 6, xx + 6, yy + 6), fill="#CF7A14", outline="#FFFFFF", width=2)
        draw.text(((plot_left + plot_right) / 2, plot_bottom + 52), _tr(language, "channel"), font=small, fill="#506873", anchor="mm")
        draw.text((72, (plot_top + plot_bottom) / 2), _tr(language, "energy"), font=small, fill="#506873", anchor="mm")
        y += 470

    if len(rows) > 1:
        draw.text((50, y), f"{_tr(language, 'activity_comparison')} (Bq/kg)", font=bold, fill="#17324D")
        chart_top, chart_bottom, chart_left, chart_right = y + 50, y + 410, 130, 1530
        series = [("Th232", "Th-232", "#3B6B82"), ("Ra226", "Ra-226", "#CF7A14"), ("K40", "K-40", "#3F8F3A")]
        finite = [item.get("activity_bq_kg", {}).get(key) for item in rows for key, _, _ in series]
        maximum = max([value for value in finite if isinstance(value, (int, float)) and math.isfinite(value)] or [1]) * 1.12
        for tick in range(6):
            yy = chart_bottom - (chart_bottom - chart_top) * tick / 5
            draw.line((chart_left, yy, chart_right, yy), fill="#D6E0DD", width=1)
            draw.text((chart_left - 16, yy), _number(maximum * tick / 5, 4), font=small, fill="#627782", anchor="rm")
        group_width = (chart_right - chart_left) / len(rows)
        bar_width = min(42, group_width / 5)
        for index, item in enumerate(rows):
            center = chart_left + group_width * (index + 0.5)
            for series_index, (key, _, color) in enumerate(series):
                value = item.get("activity_bq_kg", {}).get(key)
                value = value if isinstance(value, (int, float)) and math.isfinite(value) else 0
                bar_height = value / maximum * (chart_bottom - chart_top)
                x = center + (series_index - 1) * bar_width - bar_width * 0.42
                draw.rectangle((x, chart_bottom - bar_height, x + bar_width * 0.84, chart_bottom), fill=color)
            draw.text((center, chart_bottom + 25), str(item.get("name"))[:14], font=small, fill="#344C58", anchor="mm")
        for index, (_, label, color) in enumerate(series):
            legend_x = 570 + index * 190
            draw.rectangle((legend_x, y + 8, legend_x + 22, y + 28), fill=color)
            draw.text((legend_x + 30, y + 19), label, font=small, fill="#344C58", anchor="lm")
        y += chart_height

    peak_headers = [_tr(language, "sample"), _tr(language, "analyte_emitter"), _tr(language, "reference"), _tr(language, "observed_short"), _tr(language, "converted_short"), _tr(language, "gross"), _tr(language, "background"), _tr(language, "net")]
    peak_values: list[list[Any]] = []
    for item in rows:
        for nuclide, peaks in item.get("peaks", {}).items():
            for peak in peaks:
                peak_values.append([item.get("name"), f"{_nuclide_label(nuclide)} ({peak.get('emitter')})", _number(peak.get("energy_keV"), 7),
                                    _number(peak.get("center_channel"), 8), _number(peak.get("converted_energy_keV"), 8),
                                    _number(peak.get("gross_counts")), _number(peak.get("background_counts")), _number(peak.get("net_counts"))])
    y = table(y, _tr(language, "peak_analysis"), peak_headers, peak_values,
              [190, 260, 180, 180, 180, 170, 170, 170])
    note = _tr(language, "note")
    draw.text((50, y + 5), note, font=small, fill="#506873")
    stream = BytesIO()
    image.save(stream, "PNG", dpi=(180, 180))
    return stream.getvalue()


def export_pdf(analysis: dict[str, Any], language: str = "zh") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    _tr(language, "summary_title")
    stream = BytesIO()
    font_name = "RTKFont"
    pdfmetrics.registerFont(TTFont(font_name, _font_path(), subfontIndex=0))
    doc = SimpleDocTemplate(stream, pagesize=landscape(A4), leftMargin=16 * mm, rightMargin=16 * mm, topMargin=13 * mm, bottomMargin=13 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("RTKTitle", parent=styles["Title"], fontName=font_name, fontSize=20, leading=26, alignment=TA_CENTER, textColor=colors.HexColor("#17324D"))
    body_style = ParagraphStyle("RTKBody", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=13)

    def calibration_drawing(item: dict[str, Any]) -> Drawing:
        points, x_min, x_max, fitted_min, fitted_max = _calibration_plot_data(item)
        observed_energies = [point[1] for point in points]
        y_min = min([fitted_min, fitted_max, *observed_energies], default=0.0)
        y_max = max([fitted_min, fitted_max, *observed_energies], default=1.0)
        if y_max <= y_min:
            y_max = y_min + 1.0
        drawing = Drawing(700, 235)
        left, bottom, plot_width, plot_height = 65, 42, 595, 155
        x_span, y_span = x_max - x_min, y_max - y_min
        px = lambda value: left + (value - x_min) / x_span * plot_width
        py = lambda value: bottom + (value - y_min) / y_span * plot_height
        for tick in range(6):
            xx = left + plot_width * tick / 5
            yy = bottom + plot_height * tick / 5
            drawing.add(Line(xx, bottom, xx, bottom + plot_height, strokeColor=colors.HexColor("#DFE8E6"), strokeWidth=0.5))
            drawing.add(Line(left, yy, left + plot_width, yy, strokeColor=colors.HexColor("#DFE8E6"), strokeWidth=0.5))
            drawing.add(String(xx, 25, _number(x_min + x_span * tick / 5, 5), textAnchor="middle", fontName=font_name, fontSize=7, fillColor=colors.HexColor("#627782")))
            drawing.add(String(left - 8, yy - 3, _number(y_min + y_span * tick / 5, 5), textAnchor="end", fontName=font_name, fontSize=7, fillColor=colors.HexColor("#627782")))
        drawing.add(Line(px(x_min), py(fitted_min), px(x_max), py(fitted_max), strokeColor=colors.HexColor("#176B70"), strokeWidth=2.2))
        for channel, energy in points:
            drawing.add(Circle(px(channel), py(energy), 3.7, fillColor=colors.HexColor("#CF7A14"), strokeColor=colors.white, strokeWidth=0.8))
        drawing.add(String(left + plot_width / 2, 8, _tr(language, "channel"), textAnchor="middle", fontName=font_name, fontSize=8, fillColor=colors.HexColor("#506873")))
        drawing.add(String(5, bottom + plot_height / 2, _tr(language, "energy"), fontName=font_name, fontSize=8, fillColor=colors.HexColor("#506873")))
        drawing.add(Line(440, 217, 465, 217, strokeColor=colors.HexColor("#176B70"), strokeWidth=2.2))
        drawing.add(String(471, 213, _tr(language, "fitted_line"), fontName=font_name, fontSize=8, fillColor=colors.HexColor("#506873")))
        drawing.add(Circle(565, 217, 3.7, fillColor=colors.HexColor("#CF7A14"), strokeColor=colors.white, strokeWidth=0.8))
        drawing.add(String(574, 213, f"{_tr(language, 'matched_points')} ({len(points)})", fontName=font_name, fontSize=8, fillColor=colors.HexColor("#506873")))
        return drawing
    title = _tr(language, "summary_title")
    headers = [_tr(language, "spectrum"), _tr(language, "file"), "Ra (ppm)", "Th (ppm)", "K (%)"]
    data = [headers]
    for item in analysis.get("results", []):
        data.append([item.get("spectrum_no"), item.get("name"), _number(item.get("ra_ppm")), _number(item.get("th_ppm")), _number(item.get("k_percent"))])
    table = Table(data, colWidths=[32 * mm, 82 * mm, 46 * mm, 46 * mm, 46 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B70")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#799099")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF1EF")]),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    note = _tr(language, "validity_value")
    activity_headers = [_tr(language, "sample"), _tr(language, "mass_kg"), "Th-232 / Bq/kg", "Ra-226 / Bq/kg", "K-40 / Bq/kg"]
    activity_data = [activity_headers]
    for item in analysis.get("results", []):
        activity_data.append([item.get("name"), _number(item.get("mass_g", 0) / 1000, 6),
                              _number(item.get("activity_bq_kg", {}).get("Th232"), 7),
                              _number(item.get("activity_bq_kg", {}).get("Ra226"), 7),
                              _number(item.get("activity_bq_kg", {}).get("K40"), 7)])
    activity_table = Table(activity_data, colWidths=[65 * mm, 35 * mm, 48 * mm, 48 * mm, 48 * mm], repeatRows=1)
    activity_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B70")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#799099")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF1EF")]),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story = [Paragraph(title, title_style), Spacer(1, 7 * mm), table, Spacer(1, 7 * mm),
             Paragraph(_tr(language, "activity_title"), title_style),
             Spacer(1, 4 * mm), activity_table]
    if len(analysis.get("results", [])) > 1:
        results = analysis["results"]
        chart = Drawing(700, 235)
        left, bottom, chart_width, chart_height = 55, 42, 620, 155
        series = [("Th232", "Th-232", colors.HexColor("#3B6B82")),
                  ("Ra226", "Ra-226", colors.HexColor("#CF7A14")),
                  ("K40", "K-40", colors.HexColor("#3F8F3A"))]
        finite = [item.get("activity_bq_kg", {}).get(key) for item in results for key, _, _ in series]
        maximum = max([value for value in finite if isinstance(value, (int, float)) and math.isfinite(value)] or [1]) * 1.12
        for tick in range(6):
            yy = bottom + chart_height * tick / 5
            chart.add(Line(left, yy, left + chart_width, yy, strokeColor=colors.HexColor("#D6E0DD"), strokeWidth=0.5))
            chart.add(String(left - 8, yy - 3, _number(maximum * tick / 5, 4), textAnchor="end", fontName=font_name, fontSize=7))
        group_width = chart_width / len(results)
        bar_width = min(18, group_width / 5)
        for index, item in enumerate(results):
            center = left + group_width * (index + 0.5)
            for series_index, (key, _, color) in enumerate(series):
                value = item.get("activity_bq_kg", {}).get(key)
                value = value if isinstance(value, (int, float)) and math.isfinite(value) else 0
                bar_height = value / maximum * chart_height
                chart.add(Rect(center + (series_index - 1) * bar_width - bar_width * 0.42, bottom,
                               bar_width * 0.84, bar_height, fillColor=color, strokeColor=None))
            chart.add(String(center, 24, str(item.get("name"))[:18], textAnchor="middle", fontName=font_name, fontSize=7))
        for index, (_, label, color) in enumerate(series):
            legend_x = 235 + index * 105
            chart.add(Rect(legend_x, 215, 12, 9, fillColor=color, strokeColor=None))
            chart.add(String(legend_x + 17, 216, label, fontName=font_name, fontSize=8))
        story.extend([Spacer(1, 5 * mm), Paragraph(_tr(language, "activity_comparison"), body_style), chart])
    story.extend([Spacer(1, 5 * mm), Paragraph(note, body_style), PageBreak()])
    story.append(Paragraph(_tr(language, "traceable_detail"), title_style))
    reference_headers = [_tr(language, "analyte"), _tr(language, "emitter"), _tr(language, "reference_energy"), _tr(language, "default_channel")]
    reference_data = [reference_headers] + [[_nuclide_label(peak.get("nuclide")), peak.get("emitter"), peak.get("energy_keV"),
                                             peak.get("default_reference_channel")] for peak in analysis.get("peak_references", [])]
    reference_table = Table(reference_data, colWidths=[42 * mm, 52 * mm, 52 * mm, 55 * mm], repeatRows=1)
    reference_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font_name),
                                         ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D7E8E5")),
                                         ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#8BA1A8")),
                                         ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.extend([Spacer(1, 4 * mm), Paragraph(_tr(language, "primary_reference"), body_style),
                  Spacer(1, 2 * mm), reference_table])
    for item in analysis.get("results", []):
        cal = item.get("calibration", {})
        formula = f"E = {_number(cal.get('slope'), 8)} × CH + {_number(cal.get('intercept'), 8)} keV"
        quality = f"{_tr(language, 'correlation')} = {_number(cal.get('correlation_r'), 8)} / {_tr(language, 'deviation')} = {_number(cal.get('relative_deviation_percent'), 6)}% / RMS = {_number(cal.get('rms_keV'), 6)} keV"
        story.extend([Spacer(1, 4 * mm), Paragraph(f"{item.get('spectrum_no')}. {item.get('name')}　{formula}<br/>{quality}", body_style),
                      Spacer(1, 2 * mm), calibration_drawing(item)])
        detail_headers = [_tr(language, "analyte_emitter"), _tr(language, "reference_energy"), _tr(language, "observed_channel"), _tr(language, "converted_energy"), _tr(language, "gross"), _tr(language, "background"), _tr(language, "net"), _tr(language, "net_rate")]
        detail = [detail_headers]
        for nuclide, peaks in item.get("peaks", {}).items():
            for peak in peaks:
                detail.append([f"{_nuclide_label(nuclide)} ({peak.get('emitter')})", _number(peak.get("energy_keV"), 7),
                               _number(peak.get("center_channel"), 8), _number(peak.get("converted_energy_keV"), 8),
                               _number(peak.get("gross_counts")), _number(peak.get("background_counts")),
                               _number(peak.get("net_counts")), _number(peak.get("net_cps"))])
        detail_table = Table(detail, colWidths=[42 * mm, 27 * mm, 34 * mm, 34 * mm, 28 * mm, 31 * mm, 28 * mm, 28 * mm], repeatRows=1)
        detail_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                                          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D7E8E5")),
                                          ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#8BA1A8")),
                                          ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(detail_table)
    doc.build(story)
    return stream.getvalue()
