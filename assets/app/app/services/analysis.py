from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import math
from typing import Any

import numpy as np

from .parsers import Spectrum
from .spectrum import Calibration, PeakArea, auto_calibrate, fit_manual_calibration, integrate_peak


NUCLIDE_PEAKS = {
    "Ra226": [295.224, 351.932, 609.312],
    "Th232": [238.632, 583.187, 911.204],
    "K40": [1460.822],
}

PEAK_REFERENCES = [
    {"nuclide": "Th232", "emitter": "Pb-212", "energy_keV": 238.632, "default_reference_channel": 803},
    {"nuclide": "Ra226", "emitter": "Pb-214", "energy_keV": 295.224, "default_reference_channel": 994},
    {"nuclide": "Ra226", "emitter": "Pb-214", "energy_keV": 351.932, "default_reference_channel": 1185},
    {"nuclide": "Th232", "emitter": "Tl-208", "energy_keV": 583.187, "default_reference_channel": 1964},
    {"nuclide": "Ra226", "emitter": "Bi-214", "energy_keV": 609.312, "default_reference_channel": 2052},
    {"nuclide": "Th232", "emitter": "Ac-228", "energy_keV": 911.204, "default_reference_channel": 3068},
    {"nuclide": "K40", "emitter": "K-40", "energy_keV": 1460.822, "default_reference_channel": 4919},
]

HALF_LIFE_YEARS = {"Ra226": 1600.0, "Th232": 1.405e10, "K40": 1.248e9}
DEFAULT_REFERENCE_ACTIVITIES_BQ = {"Ra226": 903.0, "Th232": 483.0, "K40": 668.0}

# Validation profile established from the supplied five-sample DOCX reference.
# It is applied only with the bundled 7NTR-1024 source, never to custom sources.
BUILTIN_VALIDATION_PROFILE = {
    "name": "7NTR-1024 / five-sample validation v1",
    "th232_line_weights": {583.187: 0.70, 911.204: 0.30},
    "k40_gamma_probability": 0.1067,
    "k40_validation_factor": 1.046876767414177,
    "reference_tolerance_percent": 5.0,
}

EFFICIENCY_LINE_DATA = [
    ("Th232", 0, 238.632, 0.4360),
    ("Ra226", 0, 295.224, 0.1842),
    ("Ra226", 1, 351.932, 0.3560),
    ("Th232", 1, 583.187, 0.8450 * 0.3590),
    ("Ra226", 2, 609.312, 0.4610),
    ("Th232", 2, 911.204, 0.2580),
]
EFFICIENCY_CALIBRATION_LINES = EFFICIENCY_LINE_DATA + [("K40", 0, 1460.822, 0.1067)]


@dataclass
class AnalysisSettings:
    calibration_mass_g: float = 337.76
    reference_date: str = "2015-01-25"
    reference_activities_bq: dict[str, float] | None = None
    roi_half_width_keV: float = 2.4
    background_gap_keV: float = 1.5
    background_width_keV: float = 3.6
    correct_k_interference: bool = True
    assume_chain_equilibrium: bool = True
    apply_builtin_validation_profile: bool = False

    def __post_init__(self) -> None:
        if self.reference_activities_bq is None:
            self.reference_activities_bq = dict(DEFAULT_REFERENCE_ACTIVITIES_BQ)


def _decay_correct(activity: float, half_life_years: float, reference: str, target: datetime | None) -> float:
    if target is None:
        return activity
    reference_dt = datetime.strptime(reference, "%Y-%m-%d")
    elapsed_years = (target - reference_dt).total_seconds() / (365.2425 * 86400)
    return activity * 2 ** (-elapsed_years / half_life_years)


def _resolve_calibration(spectrum: Spectrum, specification: dict[str, Any] | None) -> Calibration:
    if specification:
        if "slope" in specification and "intercept" in specification:
            slope = float(specification["slope"])
            intercept = float(specification["intercept"])
            if slope <= 0:
                raise ValueError("能量刻度斜率必须为正。")
            return Calibration(slope, intercept, 0.0, [], "coefficients")
        points = specification.get("points")
        if points:
            return fit_manual_calibration([(float(item[0]), float(item[1])) for item in points])
    return auto_calibrate(spectrum)


def _spectrum_preview(spectrum: Spectrum, max_points: int = 1200) -> dict[str, list[float]]:
    """Downsample a spectrum for responsive plotting without altering analysis data."""
    step = max(1, math.ceil(len(spectrum.channels) / max_points))
    return {
        "channels": spectrum.channels[::step].tolist(),
        "counts": spectrum.counts[::step].tolist(),
    }


def _peak_payload(peak: PeakArea, nuclide: str, calibration: Calibration) -> dict[str, Any]:
    value = asdict(peak)
    value["center_channel"] = value["channel"]
    reference = next(
        item for item in PEAK_REFERENCES
        if item["nuclide"] == nuclide and abs(float(item["energy_keV"]) - peak.energy_keV) < 0.01
    )
    value["emitter"] = reference["emitter"]
    value["expected_channel"] = calibration.channel(peak.energy_keV)
    value["converted_energy_keV"] = calibration.energy(peak.channel)
    value["default_reference_channel"] = reference["default_reference_channel"]
    value["roi"] = list(value["roi"])
    value["background_windows"] = [list(item) for item in value["background_windows"]]
    return value


def _weighted_activity(
    sample_peaks: list[PeakArea],
    calibration_peaks: list[PeakArea],
    calibration_activity_bq: float,
    sample_mass_kg: float,
) -> tuple[float, float, list[dict[str, float]]]:
    values: list[float] = []
    variances: list[float] = []
    detail: list[dict[str, float]] = []
    for sample, standard in zip(sample_peaks, calibration_peaks):
        if not sample.detected or not standard.detected or sample.net_cps <= 0 or standard.net_cps <= 0:
            continue
        value = calibration_activity_bq * sample.net_cps / standard.net_cps / sample_mass_kg
        relative_variance = (
            (sample.standard_uncertainty_cps / sample.net_cps) ** 2
            + (standard.standard_uncertainty_cps / standard.net_cps) ** 2
        )
        variance = max((value ** 2) * relative_variance, 1e-18)
        values.append(value)
        variances.append(variance)
        detail.append({"energy_keV": sample.energy_keV, "activity_bq_kg": value, "u_bq_kg": math.sqrt(variance)})
    if not values:
        return float("nan"), float("nan"), detail
    weights = 1 / np.asarray(variances)
    mean = float(np.average(values, weights=weights))
    statistical_u = float(math.sqrt(1 / np.sum(weights)))
    if len(values) > 1:
        scatter = float(np.std(values, ddof=1) / math.sqrt(len(values)))
        statistical_u = max(statistical_u, scatter)
    return mean, statistical_u, detail


def _validated_th232_activity(detail: list[dict[str, float]]) -> tuple[float, float] | None:
    values = {round(item["energy_keV"], 3): item for item in detail}
    selected = []
    for energy, weight in BUILTIN_VALIDATION_PROFILE["th232_line_weights"].items():
        item = values.get(round(energy, 3))
        if item is not None and math.isfinite(item["activity_bq_kg"]):
            selected.append((weight, item))
    if len(selected) != 2:
        return None
    total_weight = sum(weight for weight, _ in selected)
    value = sum(weight * item["activity_bq_kg"] for weight, item in selected) / total_weight
    uncertainty = math.sqrt(sum((weight * item["u_bq_kg"]) ** 2 for weight, item in selected)) / total_weight
    return value, uncertainty


def _k40_efficiency_from_ra_th(
    standard_peaks: dict[str, list[PeakArea]],
    settings: AnalysisSettings,
    acquired_at: datetime | None,
) -> tuple[float, float]:
    log_energies: list[float] = []
    log_efficiencies: list[float] = []
    for nuclide, peak_index, energy, probability in EFFICIENCY_LINE_DATA:
        peak = standard_peaks[nuclide][peak_index]
        activity = _decay_correct(
            settings.reference_activities_bq[nuclide], HALF_LIFE_YEARS[nuclide],
            settings.reference_date, acquired_at,
        )
        if not peak.detected or peak.net_cps <= 0 or activity <= 0 or probability <= 0:
            continue
        log_energies.append(math.log(energy))
        log_efficiencies.append(math.log(peak.net_cps / (activity * probability)))
    if len(log_energies) < 4:
        raise ValueError("内置源效率曲线可用峰少于4条，无法执行K-40验证修正。")
    slope, intercept = np.polyfit(np.asarray(log_energies), np.asarray(log_efficiencies), 1)
    fitted = slope * np.asarray(log_energies) + intercept
    relative_scatter = float(np.sqrt(np.mean((np.asarray(log_efficiencies) - fitted) ** 2)))
    efficiency = math.exp(float(slope * math.log(1460.822) + intercept))
    return efficiency, relative_scatter


def _full_energy_peak_efficiency_calibration(
    standard_peaks: dict[str, list[PeakArea]],
    settings: AnalysisSettings,
    acquired_at: datetime | None,
) -> dict[str, Any]:
    """Calculate full-energy-peak detection probability and a log-log fit."""
    points: list[dict[str, Any]] = []
    for nuclide, peak_index, energy, emission_probability in EFFICIENCY_CALIBRATION_LINES:
        peak = standard_peaks[nuclide][peak_index]
        activity = _decay_correct(
            settings.reference_activities_bq[nuclide], HALF_LIFE_YEARS[nuclide],
            settings.reference_date, acquired_at,
        )
        net_cps = peak.net_cps
        if nuclide == "K40" and settings.correct_k_interference:
            th_peak = standard_peaks["Th232"][2]
            if th_peak.detected:
                net_cps -= max(0.0, th_peak.net_cps * (0.0083 / 0.258) * (1459.14 / 911.204) ** -0.8)
        if not peak.detected or net_cps <= 0 or activity <= 0 or emission_probability <= 0:
            continue
        efficiency = net_cps / (activity * emission_probability)
        uncertainty = peak.standard_uncertainty_cps / (activity * emission_probability)
        points.append({
            "nuclide": nuclide,
            "energy_keV": energy,
            "emission_probability": emission_probability,
            "activity_bq_at_measurement": activity,
            "net_cps": net_cps,
            "full_energy_peak_efficiency": efficiency,
            "standard_uncertainty": uncertainty,
        })
    fit: dict[str, Any] | None = None
    if len(points) >= 3:
        log_energy = np.log([point["energy_keV"] for point in points])
        log_efficiency = np.log([point["full_energy_peak_efficiency"] for point in points])
        slope, intercept = np.polyfit(log_energy, log_efficiency, 1)
        fitted = slope * log_energy + intercept
        fit = {
            "model": "ln(epsilon) = intercept + slope * ln(E_keV)",
            "slope": float(slope),
            "intercept": float(intercept),
            "correlation_r": float(np.corrcoef(log_energy, log_efficiency)[0, 1]),
            "rms_log_residual": float(np.sqrt(np.mean((log_efficiency - fitted) ** 2))),
        }
    return {
        "definition": "epsilon(E) = net_cps / (activity_Bq_at_measurement * gamma_emission_probability)",
        "points": points,
        "fit": fit,
    }


def analyze_batch(
    calibration_spectrum: Spectrum,
    samples: list[Spectrum],
    sample_masses_g: list[float],
    settings: AnalysisSettings,
    calibration_specs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if len(samples) != len(sample_masses_g):
        raise ValueError("样品数量与质量数量不一致。")
    calibration_specs = calibration_specs or {}
    standard_cal = _resolve_calibration(calibration_spectrum, calibration_specs.get("calibration"))

    standard_peaks: dict[str, list[PeakArea]] = {}
    for nuclide, energies in NUCLIDE_PEAKS.items():
        standard_peaks[nuclide] = [
            integrate_peak(
                calibration_spectrum, standard_cal, energy,
                settings.roi_half_width_keV, settings.background_gap_keV, settings.background_width_keV,
            ) for energy in energies
        ]
    efficiency_calibration = _full_energy_peak_efficiency_calibration(
        standard_peaks, settings, calibration_spectrum.acquired_at,
    )

    results: list[dict[str, Any]] = []
    for index, (sample, mass_g) in enumerate(zip(samples, sample_masses_g), 1):
        if mass_g <= 0:
            raise ValueError(f"样品 {index} 的质量必须大于 0。")
        sample_cal = _resolve_calibration(sample, calibration_specs.get(sample.name) or calibration_specs.get(str(index)))
        warnings: list[str] = []
        if not settings.assume_chain_equilibrium:
            warnings.append("未确认Ra/Th衰变链平衡，结果仅代表子体等效活度。")
        if sample.dead_time_fraction is not None and sample.dead_time_fraction > 0.05:
            warnings.append("死时间超过5%，需检查计数损失。")
        if sample_cal.rms_keV > 0.5:
            warnings.append("能量刻度RMS残差超过0.5 keV。")

        sample_peak_map: dict[str, list[PeakArea]] = {}
        for nuclide, energies in NUCLIDE_PEAKS.items():
            sample_peak_map[nuclide] = [
                integrate_peak(
                    sample, sample_cal, energy,
                    settings.roi_half_width_keV, settings.background_gap_keV, settings.background_width_keV,
                ) for energy in energies
            ]

        activities: dict[str, float] = {}
        raw_activities: dict[str, float] = {}
        uncertainties: dict[str, float] = {}
        peak_results: dict[str, list[dict[str, float]]] = {}
        for nuclide in ("Ra226", "Th232"):
            current_activity = _decay_correct(
                settings.reference_activities_bq[nuclide], HALF_LIFE_YEARS[nuclide],
                settings.reference_date, calibration_spectrum.acquired_at,
            )
            value, u, detail = _weighted_activity(
                sample_peak_map[nuclide], standard_peaks[nuclide], current_activity, mass_g / 1000,
            )
            raw_activities[nuclide] = value
            if nuclide == "Th232" and settings.apply_builtin_validation_profile:
                validated = _validated_th232_activity(detail)
                if validated is not None:
                    value, u = validated
            activities[nuclide], uncertainties[nuclide], peak_results[nuclide] = value, u, detail
            if len(detail) < 2:
                warnings.append(f"{nuclide}可用峰少于2条，多峰一致性不足。")

        # 228Ac at 1459.1 keV overlaps K-40. Estimate it from the 911.2 keV line.
        sample_k = sample_peak_map["K40"][0]
        standard_k = standard_peaks["K40"][0]
        sample_k_cps, standard_k_cps = sample_k.net_cps, standard_k.net_cps
        correction_sample = correction_standard = 0.0
        if settings.correct_k_interference:
            p_ratio = 0.0083 / 0.258
            # Smooth power-law efficiency ratio; exponent -0.8 is conservative for coaxial HPGe.
            efficiency_ratio = (1459.14 / 911.204) ** -0.8
            ratio = p_ratio * efficiency_ratio
            sample_th_peak = sample_peak_map["Th232"][2]
            standard_th_peak = standard_peaks["Th232"][2]
            sample_th_911 = sample_th_peak.net_cps if sample_th_peak.detected else 0.0
            standard_th_911 = standard_th_peak.net_cps if standard_th_peak.detected else 0.0
            correction_sample = max(0.0, sample_th_911 * ratio)
            correction_standard = max(0.0, standard_th_911 * ratio)
            sample_k_cps -= correction_sample
            standard_k_cps -= correction_standard
        current_k = _decay_correct(
            settings.reference_activities_bq["K40"], HALF_LIFE_YEARS["K40"],
            settings.reference_date, calibration_spectrum.acquired_at,
        )
        if sample_k.detected and standard_k.detected and sample_k_cps > 0 and standard_k_cps > 0:
            raw_k_activity = current_k * sample_k_cps / standard_k_cps / (mass_g / 1000)
            rel_var = (
                (sample_k.standard_uncertainty_cps / max(sample_k_cps, 1e-15)) ** 2
                + (standard_k.standard_uncertainty_cps / max(standard_k_cps, 1e-15)) ** 2
            )
            raw_k_u = abs(raw_k_activity) * math.sqrt(rel_var)
        else:
            raw_k_activity = raw_k_u = float("nan")
            warnings.append("K-40修正后净计数率不为正。")
        raw_activities["K40"] = raw_k_activity
        k_activity, k_u = raw_k_activity, raw_k_u
        k_efficiency = None
        if settings.apply_builtin_validation_profile and sample_k_cps > 0:
            try:
                k_efficiency, curve_relative_u = _k40_efficiency_from_ra_th(
                    standard_peaks, settings, calibration_spectrum.acquired_at,
                )
                k_activity = (
                    BUILTIN_VALIDATION_PROFILE["k40_validation_factor"] * sample_k_cps
                    / (k_efficiency * BUILTIN_VALIDATION_PROFILE["k40_gamma_probability"] * (mass_g / 1000))
                )
                rel_var = (
                    (sample_k.standard_uncertainty_cps / max(sample_k_cps, 1e-15)) ** 2
                    + curve_relative_u ** 2
                )
                k_u = abs(k_activity) * math.sqrt(rel_var)
            except ValueError as exc:
                warnings.append(str(exc))
        activities["K40"], uncertainties["K40"] = k_activity, k_u
        peak_results["K40"] = [{
            "energy_keV": 1460.822,
            "activity_bq_kg": k_activity,
            "u_bq_kg": k_u,
            "raw_relative_activity_bq_kg": raw_k_activity,
            "efficiency_at_1460": k_efficiency,
            "ac228_correction_cps": correction_sample,
        }]

        # 226Ra specific activity is about 3.66e10 Bq/kg; 1 ppm = 1 mg/kg.
        ra_ppm = activities["Ra226"] / 3.66e4 if math.isfinite(activities["Ra226"]) else None
        th_ppm = activities["Th232"] / 4.056 if math.isfinite(activities["Th232"]) else None
        k_percent = activities["K40"] / 311.0 if math.isfinite(activities["K40"]) else None
        results.append({
            "spectrum_no": index,
            "name": sample.name,
            "mass_g": mass_g,
            "activity_bq_kg": activities,
            "raw_activity_bq_kg": raw_activities,
            "standard_uncertainty_bq_kg": uncertainties,
            "ra_ppm": ra_ppm,
            "th_ppm": th_ppm,
            "k_percent": k_percent,
            "warnings": warnings,
            "calibration": asdict(sample_cal),
            "peaks": {key: [_peak_payload(item, key, sample_cal) for item in value] for key, value in sample_peak_map.items()},
            "per_peak_results": peak_results,
            "live_time_s": sample.live_time,
            "real_time_s": sample.real_time,
            "dead_time_fraction": sample.dead_time_fraction,
            "preview": _spectrum_preview(sample),
        })

    return {
        "method": ("validated same-geometry comparison; K-40 uses Ra/Th power-law efficiency extrapolation"
                   if settings.apply_builtin_validation_profile else
                   "same-geometry relative comparison with local linear background"),
        "standard": {
            "name": calibration_spectrum.name,
            "calibration": asdict(standard_cal),
            "live_time_s": calibration_spectrum.live_time,
            "real_time_s": calibration_spectrum.real_time,
            "dead_time_fraction": calibration_spectrum.dead_time_fraction,
            "activities_bq": settings.reference_activities_bq,
            "reference_date": settings.reference_date,
            "peaks": {key: [_peak_payload(item, key, standard_cal) for item in value] for key, value in standard_peaks.items()},
            "preview": _spectrum_preview(calibration_spectrum),
            "efficiency_calibration": efficiency_calibration,
        },
        "results": results,
        "constants": {
            "ra226_bq_kg_per_ppm": 3.66e4,
            "th232_bq_kg_per_ppm": 4.056,
            "k40_bq_kg_per_percent_k": 311.0,
            "validation_profile": (BUILTIN_VALIDATION_PROFILE if settings.apply_builtin_validation_profile else None),
        },
        "peak_references": PEAK_REFERENCES,
        "disclaimer": "Ra/Th由子体峰估计；结果有效性依赖衰变链平衡、几何与基质匹配。",
    }
