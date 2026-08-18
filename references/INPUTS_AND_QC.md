# Inputs and quality control

## Supported spectrum files

- Excel: `.xls`, `.xlsx`
- Text: `.txt`
- Multiple sample files can be imported in one analysis.

The parser tolerates common layouts with a channel column and a count column, or a single ordered count column. Text files may contain metadata before the count data.

Example metadata and data pattern:

```text
DATE=2026-08-16
TIME=12:00:00
TLIVE=21600
TREAL=21618
0  12
1  9
2  11
```

## Automatic live-time recovery

The application searches for common live-time labels such as `TLIVE`, `LIVE TIME`, `live_time`, and `活时间`. If explicit live time is absent but start/end or real-time information is sufficient, the parser may derive it. Always inspect the populated value before analysis.

If the value cannot be recovered, enter live time manually in seconds. Do not silently substitute real time when dead-time correction matters.

## Required analysis inputs

- One efficiency calibration source spectrum or the bundled default calibration source.
- One or more sample spectra.
- Sample mass in kilograms for each sample.
- Live time in seconds for every calibration and sample spectrum.
- Calibration source activity/certificate values appropriate to the source reference date.

The bundled default source is a workflow example derived from the project calibration file. It is valid only for measurements with compatible geometry and detector conditions.

## Review checklist

Before accepting a result, check:

1. The expected peak energies are visible and correctly assigned.
2. Energy calibration has sufficient matched points and acceptable `R`, RMS, and percentage deviation.
3. Live time and sample mass match the measurement record.
4. Gross counts, local background, and net counts are plausible at each selected peak.
5. Calibration and sample geometry are compatible.
6. Ra/Th daughter equilibrium assumptions are documented.
7. Replicate/reference results and uncertainty requirements meet the laboratory procedure.

## Export contents

Simplified Chinese, Traditional Chinese, English, and French exports are available as PNG, PDF, and Excel. Reports include, as applicable:

- sample activity concentration and conventional Ra/Th/K content;
- multi-sample comparison chart;
- peak-analysis details;
- energy calibration equation, `R`, percentage deviation, and RMS;
- sample spectrum plot;
- energy-calibration fitted curve and matching points.

Excel exports include both an embedded rendering of the calibration chart and an editable native Excel chart for compatibility across spreadsheet applications.
