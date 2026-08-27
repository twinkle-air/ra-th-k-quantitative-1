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
    critical_level_counts: float = 0.0
    detected: bool = True
    background_method: str = "adaptive-snippet"


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


def _snip_baseline(values: np.ndarray, max_half_width: int) -> np.ndarray:
    """Statistics-sensitive nonlinear iterative peak clipping (LLS-SNIP)."""
    original = np.clip(np.asarray(values, dtype=float), 0.0, None)
    transformed = np.log(np.log(np.sqrt(original + 1.0) + 1.0) + 1.0)
    work = transformed.copy()
    max_half_width = min(max(2, int(max_half_width)), max(2, (len(work) - 1) // 2))
    for half_width in range(max_half_width, 0, -1):
        previous = work.copy()
        middle = 0.5 * (previous[:-2 * half_width] + previous[2 * half_width:])
        work[half_width:-half_width] = np.minimum(previous[half_width:-half_width], middle)
    baseline = (np.exp(np.exp(work) - 1.0) - 1.0) ** 2 - 1.0
    return np.clip(baseline, 0.0, None)


def _adaptive_background(
    spectrum: Spectrum, left: int, right: int, gap: int, width: int, half: int,
) -> tuple[float, float, tuple[tuple[int, int], tuple[int, int]], str]:
    """Fit a non-negative local continuum after SNIP-assisted sideband cleaning."""
    n_roi = right - left + 1
    initial_left = (left - gap - width, left - gap - 1)
    initial_right = (right + gap + 1, right + gap + width)
    initial_left_counts = spectrum.counts[initial_left[0]:initial_left[1] + 1]
    initial_right_counts = spectrum.counts[initial_right[0]:initial_right[1] + 1]
    initial_counts = np.concatenate([initial_left_counts, initial_right_counts])
    # At ordinary counting statistics the IAEA two-sideband estimator is
    # efficient and preserves the validated method. Adapt only where sparse
    # Poisson data make a fixed narrow window unstable.
    if float(np.mean(initial_counts)) >= 5.0:
        x_bg = np.concatenate([
            spectrum.channels[initial_left[0]:initial_left[1] + 1],
            spectrum.channels[initial_right[0]:initial_right[1] + 1],
        ])
        slope_bg, intercept_bg = np.polyfit(x_bg, initial_counts, 1)
        x_roi = spectrum.channels[left:right + 1]
        background = float(np.sum(np.clip(slope_bg * x_roi + intercept_bg, 0.0, None)))
        variance_background = (n_roi / 2.0) ** 2 * (
            max(float(np.sum(initial_left_counts)), 1.0) / len(initial_left_counts) ** 2
            + max(float(np.sum(initial_right_counts)), 1.0) / len(initial_right_counts) ** 2
        )
        windows = (
            (int(spectrum.channels[initial_left[0]]), int(spectrum.channels[initial_left[1]])),
            (int(spectrum.channels[initial_right[0]]), int(spectrum.channels[initial_right[1]])),
        )
        return background, variance_background, windows, "IAEA-linear-sidebands"

    expanded = min(max(width * 3, 12), left - gap, len(spectrum.counts) - right - gap - 1)
    if expanded < 3:
        raise ValueError("峰区附近没有足够本底道址。")
    left_bg = (left - gap - expanded, left - gap - 1)
    right_bg = (right + gap + 1, right + gap + expanded)
    local_start, local_stop = left_bg[0], right_bg[1] + 1
    local_counts = spectrum.counts[local_start:local_stop]
    baseline = _snip_baseline(local_counts, max(half + gap, width))

    left_indices = np.arange(left_bg[0], left_bg[1] + 1)
    right_indices = np.arange(right_bg[0], right_bg[1] + 1)
    side_indices = np.concatenate([left_indices, right_indices])
    side_counts = spectrum.counts[side_indices]
    side_baseline = baseline[side_indices - local_start]
    # Reject only statistically clear positive excursions (neighbouring peaks);
    # retain downward Poisson fluctuations to avoid an upward-biased net area.
    # SNIP can sit below sparse Poisson observations. Anchor the rejection
    # threshold to the observed sideband median and reject only unmistakable
    # neighbouring peaks, not ordinary upward fluctuations.
    reference_level = np.maximum(side_baseline, float(np.median(side_counts)))
    keep = side_counts <= reference_level + 6.0 * np.sqrt(reference_level + 1.0)
    if int(np.sum(keep)) < 8:
        keep = np.ones_like(side_counts, dtype=bool)
    x_fit, y_fit = spectrum.channels[side_indices][keep], side_counts[keep]
    slope_bg, intercept_bg = np.polyfit(x_fit, y_fit, 1)
    x_roi = spectrum.channels[left:right + 1]
    predicted = np.clip(slope_bg * x_roi + intercept_bg, 0.0, None)
    background = float(np.sum(predicted))

    kept_left = keep[:len(left_indices)]
    kept_right = keep[len(left_indices):]
    y_left = spectrum.counts[left_indices][kept_left]
    y_right = spectrum.counts[right_indices][kept_right]
    n_left, n_right = max(len(y_left), 1), max(len(y_right), 1)
    variance_background = (n_roi / 2.0) ** 2 * (
        max(float(np.sum(y_left)), 1.0) / n_left ** 2
        + max(float(np.sum(y_right)), 1.0) / n_right ** 2
    )
    windows = (
        (int(spectrum.channels[left_bg[0]]), int(spectrum.channels[left_bg[1]])),
        (int(spectrum.channels[right_bg[0]]), int(spectrum.channels[right_bg[1]])),
    )
    return background, variance_background, windows, "adaptive-SNIP/robust-linear"


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
    if left - gap - width < 0 or right + gap + width >= len(spectrum.counts):
        raise ValueError(f"{energy_keV:.1f} keV 峰区超出谱范围。")
    x_roi = spectrum.channels[left : right + 1]
    gross = float(np.sum(spectrum.counts[left : right + 1]))
    background, var_background, background_windows, background_method = _adaptive_background(
        spectrum, left, right, gap, width, half,
    )
    net = gross - background
    local_background = np.full_like(x_roi, background / len(x_roi), dtype=float)
    net_profile = spectrum.counts[left : right + 1] - local_background
    positive_profile = np.clip(net_profile, 0.0, None)
    observed_channel = (
        float(np.average(x_roi, weights=positive_profile))
        if float(np.sum(positive_profile)) > 0 else float(spectrum.channels[center_index])
    )

    variance = max(gross, 1.0) + var_background
    critical_level = 1.645 * math.sqrt(max(var_background, 1.0))
    return PeakArea(
        energy_keV=energy_keV,
        channel=observed_channel,
        gross_counts=gross,
        background_counts=background,
        net_counts=net,
        net_cps=net / spectrum.live_time,
        standard_uncertainty_cps=math.sqrt(variance) / spectrum.live_time,
        roi=(int(spectrum.channels[left]), int(spectrum.channels[right])),
        background_windows=background_windows,
        critical_level_counts=critical_level,
        detected=net > critical_level,
        background_method=background_method,
    )
