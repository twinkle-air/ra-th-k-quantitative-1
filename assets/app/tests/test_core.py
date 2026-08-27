from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.analysis import (
    AnalysisSettings, EFFICIENCY_LINE_DATA, _k40_efficiency_from_ra_th,
    _validated_th232_activity, analyze_batch,
)
from app.services.exporters import _calibration_equation, export_pdf, export_png, export_xlsx
from app.services.parameter_import import parse_analysis_parameters
from app.services.parsers import Spectrum, inspect_spectrum_metadata, parse_spectrum
from app.services.spectrum import Calibration, PeakArea, fit_manual_calibration, integrate_peak


ENERGIES = [238.632, 295.224, 351.932, 583.187, 609.312, 911.204, 1460.822]


def synthetic(name: str, scale: float, mass_g: float = 500.0) -> Spectrum:
    channels = np.arange(8192, dtype=float)
    counts = np.full(8192, 18.0)
    slope, intercept = 0.2, 0.1
    for index, energy in enumerate(ENERGIES):
        center = (energy - intercept) / slope
        area = (24000 + index * 1800) * scale
        counts += area / (math.sqrt(2 * math.pi) * 3.0) * np.exp(-0.5 * ((channels - center) / 3.0) ** 2)
    return Spectrum(name, channels, counts, live_time=10000.0, real_time=10100.0)


class CoreTests(unittest.TestCase):
    @staticmethod
    def _docx_with_rows(rows):
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        table_rows = "".join(
            "<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>" for cell in row) + "</w:tr>"
            for row in rows
        )
        document = f'<w:document xmlns:w="{ns}"><w:body><w:tbl>{table_rows}</w:tbl></w:body></w:document>'
        payload = BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("word/document.xml", document)
        return payload.getvalue()

    def test_text_parser_and_metadata(self):
        lines = ["DATE=2025-01-02", "TIME=03:04:05", "TLIVE=120", "TREAL=125"]
        lines.extend(f"{i}\t{i + 2}" for i in range(64))
        result = parse_spectrum("sample.txt", "\n".join(lines).encode())
        self.assertEqual(len(result.channels), 64)
        self.assertEqual(result.live_time, 120)
        self.assertAlmostEqual(result.dead_time_fraction, 0.04)

    def test_word_spectrum_and_parameter_import(self):
        rows = [["TLIVE=120"], ["TREAL=125"]] + [[str(i), str(i + 2)] for i in range(64)]
        payload = self._docx_with_rows(rows)
        spectrum = parse_spectrum("sample.docx", payload)
        self.assertEqual(len(spectrum.channels), 64)
        self.assertEqual(spectrum.live_time, 120)
        rtf = b"{\\rtf1 TLIVE=60\\par TREAL=62\\par " + b"".join(
            f"{i}\\tab {i + 3}\\par ".encode() for i in range(64)
        ) + b"}"
        legacy = parse_spectrum("legacy.doc", rtf)
        self.assertEqual(legacy.live_time, 60)
        parameter_rows = [["校准源质量", "337.76 g"], ["Ra-226 活度", "903 Bq"],
                          ["Th-232 活度", "483 Bq"], ["K-40 活度", "668 Bq"]]
        parameters = parse_analysis_parameters("settings.docx", self._docx_with_rows(parameter_rows))
        self.assertEqual(parameters["values"]["calibration_mass_g"], 337.76)
        self.assertEqual(parameters["values"]["ra_activity_bq"], 903)

    def test_live_time_aliases_and_derivation(self):
        rows = ["活时间=3600.5", "TREAL=3610"] + [f"{i},{i + 1}" for i in range(64)]
        inspected = inspect_spectrum_metadata("alias.txt", "\n".join(rows).encode("utf-8"))
        self.assertEqual(inspected["live_time_s"], 3600.5)
        self.assertEqual(inspected["live_time_source"], "TLIVE")
        derived_rows = ["Real Time (s),1000", "Dead Time (%),2.5"] + [f"{i},{i + 1}" for i in range(64)]
        derived = inspect_spectrum_metadata("derived.csv", "\n".join(derived_rows).encode("utf-8"))
        self.assertAlmostEqual(derived["live_time_s"], 975.0)
        self.assertEqual(derived["live_time_source"], "TREAL+DEADTIME")

    def test_local_background_peak_area(self):
        spectrum = synthetic("sample", 1.0)
        peak = integrate_peak(spectrum, Calibration(0.2, 0.1, 0, [], "test"), 609.312)
        self.assertGreater(peak.net_counts, 20000)
        self.assertGreater(peak.gross_counts, peak.background_counts)
        self.assertTrue(peak.detected)
        self.assertEqual(peak.background_method, "IAEA-linear-sidebands")

    def test_low_count_background_keeps_signed_net_and_detection_status(self):
        channels = np.arange(512, dtype=float)
        counts = np.full(512, 2.0)
        counts[245:256] = 1.0
        spectrum = Spectrum("blank", channels, counts, live_time=1000.0)
        peak = integrate_peak(spectrum, Calibration(1.0, 0.0, 0, [], "test"), 250.0, 5.0, 2.0, 4.0)
        self.assertLess(peak.net_counts, 0.0)
        self.assertFalse(peak.detected)
        self.assertGreater(peak.critical_level_counts, 0.0)

    def test_adaptive_background_rejects_sideband_peak(self):
        channels = np.arange(512, dtype=float)
        counts = np.full(512, 2.0)
        counts += 120 / (math.sqrt(2 * math.pi) * 2.0) * np.exp(-0.5 * ((channels - 250) / 2.0) ** 2)
        counts[262] += 400.0
        spectrum = Spectrum("weak-peak", channels, counts, live_time=1000.0)
        peak = integrate_peak(spectrum, Calibration(1.0, 0.0, 0, [], "test"), 250.0, 5.0, 2.0, 4.0)
        self.assertGreater(peak.net_counts, peak.critical_level_counts)
        self.assertTrue(peak.detected)
        self.assertEqual(peak.background_method, "adaptive-SNIP/robust-linear")

    def test_calibration_correlation_and_percent_deviation(self):
        calibration = fit_manual_calibration([(100.0, 30.0), (500.0, 150.3), (1000.0, 299.7)])
        channels = np.array([100.0, 500.0, 1000.0])
        energies = np.array([30.0, 150.3, 299.7])
        fitted = calibration.slope * channels + calibration.intercept
        expected_deviation = float(np.sqrt(np.mean(((fitted - energies) / energies) ** 2)) * 100)
        self.assertGreater(calibration.correlation_r, 0.999)
        self.assertAlmostEqual(calibration.relative_deviation_percent, expected_deviation, places=12)
        self.assertEqual(_calibration_equation(0.297, -0.042), "E = 0.297 × CH − 0.042 keV")
        self.assertEqual(_calibration_equation(0.297, 0.042), "E = 0.297 × CH + 0.042 keV")

    def test_builtin_validation_profile_helpers(self):
        validated = _validated_th232_activity([
            {"energy_keV": 583.187, "activity_bq_kg": 20.0, "u_bq_kg": 1.0},
            {"energy_keV": 911.204, "activity_bq_kg": 10.0, "u_bq_kg": 2.0},
        ])
        self.assertIsNotNone(validated)
        self.assertAlmostEqual(validated[0], 17.0)

        settings = AnalysisSettings()
        peaks = {"Ra226": [None, None, None], "Th232": [None, None, None]}
        expected_at_k = 0.2 * 1460.822 ** -0.8
        for nuclide, peak_index, energy, probability in EFFICIENCY_LINE_DATA:
            activity = settings.reference_activities_bq[nuclide]
            rate = activity * probability * 0.2 * energy ** -0.8
            peaks[nuclide][peak_index] = PeakArea(
                energy, 1.0, rate * 1000, 0.0, rate * 1000, rate, 0.001,
                (0, 1), ((0, 1), (2, 3)),
            )
        fitted, scatter = _k40_efficiency_from_ra_th(peaks, settings, None)
        self.assertAlmostEqual(fitted, expected_at_k, delta=expected_at_k * 1e-10)
        self.assertLess(scatter, 1e-10)

    def test_relative_activity_and_unit_conversions(self):
        standard = synthetic("standard", 1.0)
        sample = synthetic("sample", 0.5)
        specifications = {
            "calibration": {"slope": 0.2, "intercept": 0.1},
            "sample": {"slope": 0.2, "intercept": 0.1},
        }
        result = analyze_batch(standard, [sample], [500.0], AnalysisSettings(), specifications)
        row = result["results"][0]
        # Half the standard count rate in a 0.5 kg sample reproduces the standard's total Bq as Bq/kg.
        self.assertAlmostEqual(row["activity_bq_kg"]["Ra226"], 903.0, delta=3.0)
        self.assertAlmostEqual(row["ra_ppm"], 903.0 / 36600.0, delta=0.0002)
        self.assertAlmostEqual(row["th_ppm"], 483.0 / 4.056, delta=0.5)
        self.assertAlmostEqual(row["k_percent"], 668.0 / 311.0, delta=0.03)
        first_peak = row["peaks"]["Th232"][0]
        self.assertEqual(first_peak["emitter"], "Pb-212")
        self.assertIn("converted_energy_keV", first_peak)
        self.assertIn("preview", row)
        self.assertEqual(len(row["preview"]["channels"]), len(row["preview"]["counts"]))
        self.assertGreater(len(row["preview"]["channels"]), 100)
        efficiency = result["standard"]["efficiency_calibration"]
        self.assertGreaterEqual(len(efficiency["points"]), 6)
        point = efficiency["points"][0]
        expected = point["net_cps"] / (point["activity_bq_at_measurement"] * point["emission_probability"])
        self.assertAlmostEqual(point["full_energy_peak_efficiency"], expected, places=14)
        self.assertIsNotNone(efficiency["fit"])

    def test_all_export_formats(self):
        calibration_points = [[100.0, 20.1], [1000.0, 200.1], [5000.0, 1000.1]]
        result = analyze_batch(
            synthetic("standard", 1.0), [synthetic("sample", 0.5)], [500.0], AnalysisSettings(),
            {"calibration": {"points": calibration_points}, "sample": {"points": calibration_points}},
        )
        self.assertTrue(export_png(result).startswith(b"\x89PNG"))
        self.assertTrue(export_pdf(result).startswith(b"%PDF"))
        xlsx = export_xlsx(result)
        self.assertTrue(xlsx.startswith(b"PK"))
        workbook = load_workbook(BytesIO(xlsx), read_only=False)
        headers = [cell.value for cell in next(workbook["结果总览"].iter_rows(min_row=3, max_row=3))]
        self.assertNotIn("得分", headers)
        self.assertNotIn("score", result["results"][0])
        detail_headers = [cell.value for cell in next(workbook["过程明细"].iter_rows(min_row=1, max_row=1))]
        self.assertIn("总计数", detail_headers)
        self.assertIn("本底计数", detail_headers)
        self.assertIn("判定阈值 Lc (计数)", detail_headers)
        self.assertIn("检出判定", detail_headers)
        self.assertIn("本底方法", detail_headers)
        self.assertEqual(workbook["过程明细"]["B2"].value, "Ra-226")
        self.assertEqual(workbook["特征峰参考"]["A2"].value, "Th-232")
        self.assertIn("能量刻度", workbook.sheetnames)
        self.assertIn("能量刻度拟合图", workbook.sheetnames)
        self.assertEqual(len(workbook["能量刻度拟合图"]._charts), 1)
        self.assertEqual(len(workbook["能量刻度拟合图"]._images), 1)
        self.assertIn("刻度源与概率刻度", workbook.sheetnames)
        probability_headers = [cell.value for cell in next(workbook["刻度源与概率刻度"].iter_rows(min_row=1, max_row=1))]
        self.assertIn("γ发射概率 Pγ", probability_headers)
        self.assertIn("全能峰效率 ε", probability_headers)
        self.assertEqual(len(workbook["刻度源与概率刻度"]._charts), 1)
        self.assertEqual(len(workbook["刻度源与概率刻度"]._images), 1)
        calibration_headers = [cell.value for cell in next(workbook["能量刻度"].iter_rows(min_row=1, max_row=1))]
        self.assertIn("相关系数 R", calibration_headers)
        self.assertIn("偏差 (%)", calibration_headers)
        self.assertAlmostEqual(workbook["能量刻度"]["D2"].value, 1.0, places=12)
        self.assertAlmostEqual(workbook["能量刻度"]["E2"].value, 0.0, places=12)
        english = load_workbook(BytesIO(export_xlsx(result, "en")), read_only=True)
        self.assertIn("Summary", english.sheetnames)
        self.assertIn("Energy Calibration", english.sheetnames)
        self.assertIn("Calibration Fit Charts", english.sheetnames)
        self.assertIn("Standard & Efficiency", english.sheetnames)
        english_headers = [cell.value for cell in next(english["Summary"].iter_rows(min_row=3, max_row=3))]
        self.assertIn("Spectrum", english_headers)
        self.assertNotIn("谱线编号", english_headers)
        from app.main import ExportSaveRequest, save_export
        with tempfile.TemporaryDirectory() as directory:
            payload = save_export("pdf", ExportSaveRequest(
                analysis=result, language="zh", directory=directory,
            ))
            self.assertIs(payload["fallback"], False)
            self.assertTrue(Path(payload["path"]).is_file())

    def test_desktop_export_directory(self):
        repository_root = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(repository_root))
        from desktop_launcher import DesktopApi

        result = analyze_batch(
            synthetic("standard", 1.0), [synthetic("sample", 0.5)], [500.0], AnalysisSettings(),
            {"calibration": {"slope": 0.2, "intercept": 0.1},
             "sample": {"slope": 0.2, "intercept": 0.1}},
        )
        with tempfile.TemporaryDirectory() as directory:
            api = DesktopApi()
            api.export_directory = Path(directory)
            for format_name, signature in (("png", b"\x89PNG"), ("pdf", b"%PDF"), ("xlsx", b"PK")):
                saved = api.save_export(format_name, "zh", result)
                destination = Path(saved["path"])
                self.assertEqual(destination.parent, Path(directory))
                self.assertEqual(destination.suffix, f".{format_name}")
                self.assertTrue(destination.read_bytes().startswith(signature))

    def test_browser_export_uses_unique_unlocked_filename(self):
        from app.main import _default_export_directory, _unique_export_destination

        with tempfile.TemporaryDirectory() as directory:
            first = _unique_export_destination(Path(directory), "pdf")
            first.write_bytes(b"locked-name-placeholder")
            second = _unique_export_destination(Path(directory), "pdf")
            self.assertNotEqual(first, second)
            self.assertEqual(second.parent, Path(directory))
            self.assertEqual(second.suffix, ".pdf")
            self.assertTrue(second.name.startswith("镭钍钾定量分析结果_"))
        default_directory = _default_export_directory()
        self.assertTrue(default_directory.is_dir())
        self.assertIn(default_directory.name, {"Desktop", "桌面", "exports"})

    def test_multi_sample_activity_chart_export(self):
        result = analyze_batch(
            synthetic("standard", 1.0), [synthetic("sample-1", 0.45), synthetic("sample-2", 0.7)],
            [334.0, 245.0], AnalysisSettings(),
            {"calibration": {"slope": 0.2, "intercept": 0.1},
             "sample-1": {"slope": 0.2, "intercept": 0.1}, "sample-2": {"slope": 0.2, "intercept": 0.1}},
        )
        workbook = load_workbook(BytesIO(export_xlsx(result)), read_only=False)
        self.assertIn("比活度", workbook.sheetnames)
        self.assertIn("特征峰参考", workbook.sheetnames)
        self.assertEqual(len(workbook["比活度"]._charts), 1)
        self.assertTrue(export_png(result).startswith(b"\x89PNG"))
        self.assertTrue(export_pdf(result).startswith(b"%PDF"))

    def test_four_language_ui_and_exports(self):
        calibration_points = [[100.0, 20.1], [1000.0, 200.1], [5000.0, 1000.1]]
        result = analyze_batch(
            synthetic("sample", 1.0), [synthetic("sample", 0.5)], [500.0], AnalysisSettings(),
            {"calibration": {"points": calibration_points}, "sample": {"points": calibration_points}},
        )
        expected = {
            "zh": ("结果总览", "能量刻度拟合图", "谱线编号"),
            "zht": ("結果總覽", "能量刻度擬合圖", "譜線編號"),
            "en": ("Summary", "Calibration Fit Charts", "Spectrum"),
            "fr": ("Synthèse", "Courbes d’étalonnage", "Spectre"),
        }
        for language, (summary_name, charts_name, first_header) in expected.items():
            with self.subTest(language=language):
                png = export_png(result, language)
                pdf = export_pdf(result, language)
                workbook = load_workbook(BytesIO(export_xlsx(result, language)), read_only=False)
                self.assertTrue(png.startswith(b"\x89PNG"))
                self.assertTrue(pdf.startswith(b"%PDF"))
                self.assertIn(summary_name, workbook.sheetnames)
                self.assertIn(charts_name, workbook.sheetnames)
                self.assertEqual(workbook[summary_name]["A3"].value, first_header)
                self.assertEqual(len(workbook[charts_name]._images), 1)
                self.assertEqual(len(workbook[charts_name]._charts), 1)
        for exporter in (export_xlsx, export_png, export_pdf):
            with self.subTest(exporter=exporter.__name__):
                with self.assertRaisesRegex(ValueError, "Unsupported export language"):
                    exporter(result, "de")

        static_root = Path(__file__).resolve().parents[1] / "app" / "static"
        html = (static_root / "index.html").read_text(encoding="utf-8")
        script = (static_root / "app.js").read_text(encoding="utf-8")
        for language in ("zh", "zht", "en", "fr"):
            self.assertIn(f'value="{language}"', html)
            self.assertIn(f"data-language=\"{language}\"", html)
        self.assertIn("const zhtTranslations", script)
        self.assertIn("const frTranslations", script)
        self.assertNotIn("showDirectoryPicker", script)
        self.assertIn("/api/export-directory", script)
        self.assertIn("/api/export/save/", script)
        self.assertNotIn("window.prompt", script)
        self.assertIn("exportLocationModal.showModal()", script)
        self.assertIn('id="exportLocationInput"', html)
        self.assertIn("efficiencyCanvas", html)
        self.assertIn("probabilityCalibration", script)
        self.assertNotIn("Math.log10(Math.max(0,v)+1)", script)
        self.assertIn("spectrumYAxis:'计数'", script)

    def test_parameter_import_from_excel_and_pdf(self):
        from openpyxl import Workbook
        from reportlab.pdfgen.canvas import Canvas

        workbook = Workbook()
        sheet = workbook.active
        rows = [
            ("校准源质量 (g)", 337.76), ("活度参考日期", "2015-01-25"),
            ("Ra-226 活度 (Bq)", 903), ("Th-232 活度 (Bq)", 483), ("K-40 活度 (Bq)", 668),
            ("ROI 半宽 (keV)", 2.4), ("本底间隔 (keV)", 1.5), ("本底窗宽 (keV)", 3.6),
            ("刻度斜率", 0.297), ("刻度截距", 0.042), ("Ra/Th 衰变链平衡", "已确认"),
            ("K-40 干扰修正", "true"),
        ]
        for row in rows:
            sheet.append(row)
        excel_stream = BytesIO()
        workbook.save(excel_stream)
        excel = parse_analysis_parameters("parameters.xlsx", excel_stream.getvalue())
        self.assertEqual(excel["recognized_count"], 12)
        self.assertAlmostEqual(excel["values"]["calibration_mass_g"], 337.76)
        self.assertEqual(excel["values"]["reference_date"], "2015-01-25")
        self.assertEqual(excel["values"]["ra_activity_bq"], 903)
        self.assertTrue(excel["values"]["assume_chain_equilibrium"])
        self.assertTrue(excel["values"]["correct_k_interference"])

        pdf_stream = BytesIO()
        canvas = Canvas(pdf_stream)
        lines = [
            "Calibration source mass: 337.76 g", "Activity reference date: 2015-01-25",
            "Ra-226 activity: 903 Bq", "Th-232 activity: 483 Bq", "K-40 activity: 668 Bq",
            "ROI half-width: 2.4 keV", "Background gap: 1.5 keV", "Background window width: 3.6 keV",
            "Calibration slope: 0.297", "Calibration intercept: 0.042",
        ]
        for index, line in enumerate(lines):
            canvas.drawString(72, 780 - index * 28, line)
        canvas.save()
        pdf = parse_analysis_parameters("parameters.pdf", pdf_stream.getvalue())
        self.assertEqual(pdf["recognized_count"], 10)
        self.assertAlmostEqual(pdf["values"]["roi_half_width_keV"], 2.4)
        self.assertAlmostEqual(pdf["values"]["calibration_slope"], 0.297)
        self.assertEqual(pdf["values"]["reference_date"], "2015-01-25")
        with self.assertRaisesRegex(ValueError, "仅支持"):
            parse_analysis_parameters("parameters.txt", b"Ra-226: 903")


if __name__ == "__main__":
    unittest.main()
