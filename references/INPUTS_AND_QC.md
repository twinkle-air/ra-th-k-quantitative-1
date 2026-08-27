# Inputs and quality control

## Supported spectrum files

- Excel: `.xls`, `.xlsx`
- Text: `.txt`
- Word: `.docx`; `.doc` (RTF is read directly; binary files require local Word/WPS or LibreOffice conversion)
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
- Gamma emission probabilities for the supported Ra/Th/K calibration lines. The current workflow supplies the adopted line probabilities and shows them explicitly in the probability-calibration result; verify them against the source certificate and the laboratory's approved decay-data library.

The bundled default source is a workflow example derived from the project calibration file. It is valid only for measurements with compatible geometry and detector conditions.

## Parameter-file import

The calibration and analysis panel accepts `.pdf`, `.doc`, `.docx`, `.xls`, and `.xlsx` parameter files. It can recognize calibration-source mass, activity reference date, Ra-226/Th-232/K-40 source activities, ROI half-width, background gap/window width, optional calibration slope/intercept, and explicit equilibrium/interference-correction flags. Only fields that are explicitly recognized are changed; all other current values remain intact. PDF import requires an extractable text layer, so scanned documents must be OCR-processed first. Always compare the populated fields with the source document before analysis.

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
- calibration-source spectrum, per-line gamma emission probability, decay-corrected activity, full-energy-peak efficiency, and log-log probability-calibration fit.

Excel exports include both an embedded rendering of the calibration chart and an editable native Excel chart for compatibility across spreadsheet applications.
