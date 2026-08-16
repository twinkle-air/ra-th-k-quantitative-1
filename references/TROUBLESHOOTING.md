# Troubleshooting

## The agent cannot discover the skill

- Confirm that the directory name is exactly `ra-th-k-quantitative-1`.
- Confirm that `SKILL.md` is directly inside that directory.
- Restart the agent tool or open a new session after installation.
- For project scope, confirm the skill is under the project root rather than a parent directory.

## The local page refuses the connection

The web server is not running. From the installed skill directory, run:

```bash
python scripts/start_app.py --install
```

Then open the URL printed by the command, normally `http://127.0.0.1:8000/`.

## Excel or text spectrum cannot be parsed

- Verify that the file is a real `.xls`, `.xlsx`, or text file rather than a renamed binary file.
- Check that a channel/count pair or an ordered count column is present.
- Export formulas as values if the workbook depends on unavailable external links.
- For unusual vendor formats, convert the spectrum to two columns: channel and counts.

## Live time is blank or implausible

Inspect the source file for `TLIVE`, `LIVE TIME`, or `活时间`. Enter the verified live time manually in seconds if automatic recovery is not possible. Do not use elapsed clock time without checking detector dead time.

## Calibration fit is poor

- Check peak/channel pair assignments.
- Remove false peak matches and add correctly identified lines.
- Confirm that the detector gain did not change between measurements.
- Inspect `R`, RMS, and percentage deviation together; a high `R` alone can hide a biased calibration.

## Excel opens but the calibration chart looks blank

Use the latest application version. The export contains an embedded PNG rendering for stable display and a native editable Excel chart. If a spreadsheet program suppresses drawings, enable object display or open the file in Microsoft Excel/LibreOffice and recalculate once.

## Export does not reflect the latest analysis

Run the analysis again after changing any mass, live-time, calibration, language, or peak parameter. Exports are generated from the current completed result set.
