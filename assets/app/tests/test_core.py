from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
import sys
import unittest

import numpy as np
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.analysis import (
    AnalysisSettings, EFFICIENCY_LINE_DATA, _k40_efficiency_from_ra_th,
    _validated_th232_activity, analyze_batch,
)
from app.services.exporters import export_pdf, export_png, export_xlsx
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
    def test_text_parser_and_metadata(self):
        lines = ["DATE=2025-01-02", "TIME=03:04:05", "TLIVE=120", "TREAL=125"]
        lines.extend(f"{i}\t{i + 2}" for i in range(64))
        result = parse_spectrum("sample.txt", "\n".join(lines).encode())
        self.assertEqual(len(result.channels), 64)
        self.assertEqual(result.live_time, 120)
        self.assertAlmostEqual(result.dead_time_fraction, 0.04)

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

    def test_calibration_correlation_and_percent_deviation(self):
        calibration = fit_manual_calibration([(100.0, 30.0), (500.0, 150.3), (1000.0, 299.7)])
        channels = np.array([100.0, 500.0, 1000.0])
        energies = np.array([30.0, 150.3, 299.7])
        fitted = calibration.slope * channels + calibration.intercept
        expected_deviation = float(np.sqrt(np.mean(((fitted - energies) / energies) ** 2)) * 100)
        self.assertGreater(calibration.correlation_r, 0.999)
        self.assertAlmostEqual(calibration.relative_deviation_percent, expected_deviation, places=12)

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
        self.assertEqual(workbook["过程明细"]["B2"].value, "Ra-226")
        self.assertEqual(workbook["特征峰参考"]["A2"].value, "Th-232")
        self.assertIn("能量刻度", workbook.sheetnames)
        self.assertIn("能量刻度拟合图", workbook.sheetnames)
        self.assertEqual(len(workbook["能量刻度拟合图"]._charts), 1)
        self.assertEqual(len(workbook["能量刻度拟合图"]._images), 1)
        calibration_headers = [cell.value for cell in next(workbook["能量刻度"].iter_rows(min_row=1, max_row=1))]
        self.assertIn("相关系数 R", calibration_headers)
        self.assertIn("偏差 (%)", calibration_headers)
        self.assertAlmostEqual(workbook["能量刻度"]["D2"].value, 1.0, places=12)
        self.assertAlmostEqual(workbook["能量刻度"]["E2"].value, 0.0, places=12)
        english = load_workbook(BytesIO(export_xlsx(result, "en")), read_only=True)
        self.assertIn("Summary", english.sheetnames)
        self.assertIn("Energy Calibration", english.sheetnames)
        self.assertIn("Calibration Fit Charts", english.sheetnames)
        english_headers = [cell.value for cell in next(english["Summary"].iter_rows(min_row=3, max_row=3))]
        self.assertIn("Spectrum", english_headers)
        self.assertNotIn("谱线编号", english_headers)

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


if __name__ == "__main__":
    unittest.main()
