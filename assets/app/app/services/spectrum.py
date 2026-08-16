from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math

import numpy as np

from .parsers import Spectrum


KNOWN_CALIBRATION_ENERGIES = np.asarray([
    59.5409, 80.9979, 121.7817, 238.632, 244.6974, 295.224,
    344.2785, 351.932, 583.187, 609.312, 661.657, 778.904,
    911.204, 964.057, 1112.076, 1173.228, 1332.492, 1408.013,
    1460.822,
])
QUANTIFICATION_ANCHORS = np.asarray([238.632, 295.224, 351.932, 583.187, 609.312, 911.204, 1460.822])


@dataclass
class Calibration:
    slope: float
    intercept: float
    rms_keV: float
    matched_points: list[tuple[float, float]]
    source: str = "auto"
    correlation_r: float | None = None
    relative_deviation_percent: float | None = None

    def energy(self, channel: np.ndarray | float) -> np.ndarray | float:
        return self.slope * channel + self.intercept

    def channel(self, energy: float) -> float:
        return (energy - self.intercept) / self.slope


@dataclass
class PeakArea:
    energy_keV: float
    channel: float
    gross_counts: float
    background_counts: float
    net_counts: float
    net_cps: float
    standard_uncertainty_cps: float
    roi: tuple[int, int]
    background_windows: tuple[tuple[int, int], tuple[int, int]]


def _moving_average(values: np.ndarray, width: int) -> np.ndarray:
    width = max(3, int(width) | 1)
    kernel = np.ones(width, dtype=float) / width
    return np.convolve(values, kernel, mode="same")


def find_candidate_peaks(spectrum: Spectrum, limit: int = 60) -> np.ndarray:
    counts = spectrum.counts
    smooth = _moving_average(counts, 5)
    broad = _moving_average(counts, max(31, len(counts) // 180 | 1))
    signal = smooth - broad
    local = np.where((signal[1:-1] > signal[:-2]) & (signal[1:-1] >= signal[2:]))[0] + 1
    threshold = max(8.0, float(np.percentile(signal[local], 55)) if len(local) else 8.0)
    local = local[signal[local] > threshold]
    if not len(local):
        raise ValueError("谱中未找到可用于刻度的明显峰。")
    ranked = local[np.argsort(signal[local])[::-1]][:limit]
    return np.sort(spectrum.channels[ranked])


def fit_manual_calibration(points: list[tuple[float, float]]) -> Calibration:
    if len(points) < 2:
        raise ValueError("能量刻度至少需要两个“道址—能量”点。")
    channels = np.asarray([point[0] for point in points], dtype=float)
    energies = np.asarray([point[1] for point in points], dtype=float)
    slope, intercept = np.polyfit(channels, energies, 1)
    residuals = energies - (slope * channels + intercept)
    fitted = slope * channels + intercept
    correlation_r = float(np.corrcoef(channels, energies)[0, 1])
    relative_deviation_percent = float(np.sqrt(np.mean(((fitted - energies) / energies) ** 2)) * 100)
    if slope <= 0:
        raise ValueError("刻度斜率必须为正。")
    return Calibration(
        float(slope), float(intercept), float(np.sqrt(np.mean(residuals ** 2))), points, "manual",
        correlation_r, relative_deviation_percent,
    )


def auto_calibrate(spectrum: Spectrum, tolerance_keV: float = 2.2) -> Calibration:
    # Keep the strongest peaks. Uniformly thinning a channel-sorted list can drop
    # the very Ra/Th/K anchors needed to reject a numerically plausible false fit.
    channels = find_candidate_peaks(spectrum, limit=35)
    best: tuple[int, int, float, float, float, list[tuple[float, float]]] | None = None
    energy_pairs = list(combinations(KNOWN_CALIBRATION_ENERGIES, 2))
    for c1, c2 in combinations(channels, 2):
        if c2 - c1 < 180:
            continue
        for e1, e2 in energy_pairs:
            slope = (e2 - e1) / (c2 - c1)
            if not 0.02 <= slope <= 2.0:
                continue
            intercept = e1 - slope * c1
            predicted = slope * channels + intercept
            matches: list[tuple[float, float]] = []
            errors: list[float] = []
            used: set[int] = set()
            for channel, energy in zip(channels, predicted):
                index = int(np.argmin(np.abs(KNOWN_CALIBRATION_ENERGIES - energy)))
                error = abs(float(KNOWN_CALIBRATION_ENERGIES[index] - energy))
                if error <= tolerance_keV and index not in used:
                    matches.append((float(channel), float(KNOWN_CALIBRATION_ENERGIES[index])))
                    errors.append(error)
                    used.add(index)
            if len(matches) < 3:
                continue
            span = max(item[1] for item in matches) - min(item[1] for item in matches)
            target_count = sum(any(abs(energy - target) < 0.02 for target in QUANTIFICATION_ANCHORS) for _, energy in matches)
            mean_error = float(np.mean(errors))
            # Physics anchors outrank incidental matches to environmental lines.
            score = (target_count, len(matches), span, -mean_error)
            if best is None or score > (best[0], best[1], best[2], -best[3]):
                best = (target_count, len(matches), span, mean_error, intercept, matches)
    if best is None:
        raise ValueError("自动刻度未找到至少 3 个一致峰；请手动填写斜率/截距或刻度点。")
    if best[0] < 3:
        raise ValueError("自动刻度未覆盖至少3条Ra/Th/K目标峰；请改用手动刻度。")
    robust_points = best[5]
    initial = fit_manual_calibration(robust_points)
    residuals = np.asarray([energy - initial.energy(channel) for channel, energy in robust_points])
    median = float(np.median(residuals))
    mad = float(np.median(np.abs(residuals - median)))
    cutoff = max(0.75, 4.0 * 1.4826 * mad)
    filtered = [point for point, residual in zip(robust_points, residuals) if abs(float(residual - median)) <= cutoff]
    result = fit_manual_calibration(filtered if len(filtered) >= 3 else robust_points)
    result.source = "auto"
    if result.rms_keV > tolerance_keV:
        raise ValueError("自动刻度残差过大，请改用手动刻度。")
    return result


def integrate_peak(
    spectrum: Spectrum,
    calibration: Calibration,
    energy_keV: float,
    roi_half_width_keV: float = 2.4,
    background_gap_keV: float = 1.5,
    background_width_keV: float = 3.6,
) -> PeakArea:
    channel_center = calibration.channel(energy_keV)
    half = max(2, int(round(roi_half_width_keV / calibration.slope)))
    gap = max(1, int(round(background_gap_keV / calibration.slope)))
    width = max(3, int(round(background_width_keV / calibration.slope)))
    center_index = int(np.argmin(np.abs(spectrum.channels - channel_center)))
    left, right = center_index - half, center_index + half
    left_bg = (left - gap - width, left - gap - 1)
    right_bg = (right + gap + 1, right + gap + width)
    if left_bg[0] < 0 or right_bg[1] >= len(spectrum.counts):
        raise ValueError(f"{energy_keV:.1f} keV 峰区超出谱范围。")

    x_left = spectrum.channels[left_bg[0] : left_bg[1] + 1]
    y_left = spectrum.counts[left_bg[0] : left_bg[1] + 1]
    x_right = spectrum.channels[right_bg[0] : right_bg[1] + 1]
    y_right = spectrum.counts[right_bg[0] : right_bg[1] + 1]
    x_bg = np.concatenate([x_left, x_right])
    y_bg = np.concatenate([y_left, y_right])
    slope_bg, intercept_bg = np.polyfit(x_bg, y_bg, 1)
    x_roi = spectrum.channels[left : right + 1]
    gross = float(np.sum(spectrum.counts[left : right + 1]))
    background = float(np.sum(slope_bg * x_roi + intercept_bg))
    net = gross - background
    net_profile = spectrum.counts[left : right + 1] - (slope_bg * x_roi + intercept_bg)
    positive_profile = np.clip(net_profile, 0.0, None)
    observed_channel = (
        float(np.average(x_roi, weights=positive_profile))
        if float(np.sum(positive_profile)) > 0 else float(spectrum.channels[center_index])
    )

    n_roi = len(x_roi)
    # Poisson approximation plus uncertainty of the two background means.
    var_background = (n_roi / 2) ** 2 * (
        max(float(np.sum(y_left)), 1.0) / len(y_left) ** 2
        + max(float(np.sum(y_right)), 1.0) / len(y_right) ** 2
    )
    variance = max(gross, 1.0) + var_background
    return PeakArea(
        energy_keV=energy_keV,
        channel=observed_channel,
        gross_counts=gross,
        background_counts=background,
        net_counts=net,
        net_cps=net / spectrum.live_time,
        standard_uncertainty_cps=math.sqrt(variance) / spectrum.live_time,
        roi=(int(spectrum.channels[left]), int(spectrum.channels[right])),
        background_windows=(
            (int(spectrum.channels[left_bg[0]]), int(spectrum.channels[left_bg[1]])),
            (int(spectrum.channels[right_bg[0]]), int(spectrum.channels[right_bg[1]])),
        ),
    )
