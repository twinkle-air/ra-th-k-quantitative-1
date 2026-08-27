---
name: ra-th-k-quantitative-1
description: Analyze soil Ra-226, Th-232, and K-40 from HPGe gamma spectra with a bundled local web workbench. Use when users need to import .xls, .xlsx, .txt, .csv, .dat, .doc, or .docx spectra, recover live time, perform energy calibration and detection-aware adaptive-background peak integration, compare samples with a matched efficiency standard, review calibration/QC evidence, or export Simplified Chinese, Traditional Chinese, English, and French PNG, PDF, and Excel reports.
---

# Ra–Th–K Quantitative 1

Use the bundled application to turn soil HPGe gamma spectra into traceable Ra-226, Th-232, and K-40 results. Keep the workflow local and preserve the user's original files.

## Resolve the skill directory

Treat the directory containing this `SKILL.md` as `SKILL_DIR`. Resolve every relative path below from `SKILL_DIR`; do not assume a fixed user name or installation path.

## Choose the workflow

- To launch the visual workbench, run `python scripts/start_app.py`. If dependencies are missing, run `python scripts/start_app.py --install` once, then open `http://127.0.0.1:8000/`.
- To verify an installation or modification, run `python scripts/verify.py`.
- To install this Skill into supported agents, run `python scripts/install.py --tool <codex|claude|workbuddy|codebuddy|all> --scope <user|project>`.
- To understand input fields or QC, read [references/INPUTS_AND_QC.md](references/INPUTS_AND_QC.md).
- To interpret the calculations and scientific limits, read [references/METHOD.md](references/METHOD.md).
- To diagnose startup, parsing, chart, or export failures, read [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md).
- To explain installation paths across agents, read [references/PORTABILITY.md](references/PORTABILITY.md).

## Run an analysis

1. Confirm that the standard and sample spectra were measured with the same detector and matched container, fill height, geometry, and relevant matrix conditions.
2. Select the bundled standard only for the supplied project workflow with matched geometry. Otherwise require a traceable custom efficiency-standard spectrum.
3. Import one or more sample spectra. Accept `.xls`, `.xlsx`, `.txt`, `.csv`, `.dat`, `.doc`, and `.docx`. Word tables or paragraphs must contain recognizable channel-count data. Binary `.doc` conversion requires Word/WPS or LibreOffice on the local machine.
4. Read live time from `TLIVE`, localized live-time labels, or derivable real/dead-time metadata. If the file provides none, ask the user for live time; never invent it.
5. Require the net mass of every sample in grams. Never infer mass from a filename.
6. Review reference date, source activities, ROI width, background windows, equilibrium confirmation, and K-40 interference correction before running. These fields may be populated from a text-based PDF, Word, XLS, or XLSX parameter file, but verify every recognized value against the source document.
7. Run the analysis, then inspect all result tabs: content, specific activity, process detail, sample spectrum, `E = a × CH + b` calibration plots, and the combined calibration-source spectrum/probability-calibration view. Verify that `P_gamma` is the line emission probability and `epsilon(E) = net_cps / [A(t) * P_gamma]` is the full-energy-peak detection probability.
8. Review correlation `R`, relative deviation, RMS residual, matched points, usable peaks, dead-time information, and warnings. Do not treat `R` near 1 as proof that peak assignment or quantification is correct.
9. Select Simplified Chinese, Traditional Chinese, English, or French and export PNG, PDF, or Excel. Confirm that exports contain the calibration-source spectrum, probability-calibration data/curve, and energy-calibration plots with both the fitted line and matched points.

## Scientific guardrails

- Treat outputs as assisted calculations, not certified laboratory results.
- Ra-226 and Th-232 are inferred from daughter lines and require justified decay-chain equilibrium.
- Reject or clearly qualify results when source traceability, geometry/matrix matching, sample homogeneity, mass, live time, or equilibrium is unsupported.
- Preserve warnings and intermediate values in every handoff. Do not report below-detection-limit values as reliable quantification when detection-limit evidence is unavailable.
- Preserve signed net peak areas. Do not clip a negative low-count estimate to zero; use the reported Currie decision threshold and detection status to distinguish a non-detection from a quantified peak.
- Do not redistribute standards documents or third-party test data unless the user has distribution rights.

## Modification rule

When changing the bundled application under `assets/app/`, run `python scripts/verify.py` before delivery. Verify the generated PNG, PDF, and Excel artifacts in proportion to the change.
