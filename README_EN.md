# Ra–Th–K Quantitative 1

> Current version: **v1.5.1 (2026-09-23)** · An incremental update to the same Skill, not a new project

[简体中文 README](README.md) · English

<p align="center">
  <img src="assets/project-icon.png" alt="Ra–Th–K Quantitative 1 icon" width="220">
</p>

Ra–Th–K Quantitative 1 is an Agent Skill for quantitative radium, thorium, and potassium analysis of soil spectra acquired with a high-purity germanium (HPGe) gamma-ray detector. It combines spectrum parsing, live-time extraction, energy calibration, characteristic-peak integration, relative efficiency measurement with a calibration source, specific-activity/content calculation, quality checks, and four-language report export in a local visual workbench that can run offline. It can be invoked by Agents such as Codex, Claude Code, WorkBuddy, Qoder, ZCode, and DeepSeek Harness, or used directly in a browser without an Agent.

> This project is an auxiliary calculation and traceable-reporting tool, not a certified laboratory measurement system. The user remains responsible for sample preparation, calibration-source traceability, measurement-geometry consistency, decay-chain equilibrium, detection limits, and uncertainty evaluation.

![Current local Ra–Th–K Quantitative 1 interface, captured on 2026-09-24](assets/ui-verification.png)

## Repository sync on 2026-09-24 (still v1.5.1)

- Added a [value-by-value nuclear-data audit status](references/NUCLEAR_DATA_AUDIT.md) and a reproducible K-40 sensitivity script. The production nuclear-data table was **not** replaced; its individual values have not all been independently verified.
- Documented the [public independent-data search](evaluation/PUBLIC_DATA.md). No qualifying open, end-to-end blind-sample dataset has been secured, so no blind-sample accuracy is claimed.
- Tightened the independent evaluation entry point: raw sample and standard spectra must be bound to the analysis snapshot, with separate energy-calibration evidence and explicit calibration parameters. User declarations of independence still require manual checking.
- Recorded [exact package versions for the current Windows/CPython 3.12 environment](requirements-lock-py312.txt). This is **not** a cross-platform hash-locked environment. Real traces for the planned two-host, three-condition ablation and a fixed release commit remain pending.
- Replaced the interface image with a screenshot of the current locally running web page.

## What's New in v1.5.1

- Web, desktop, CLI, and MCP exports share snapshot validation and blocking quality gates. Tampered results, missing evidence, and blocked analyses cannot produce formal reports.
- Separated `estimated_activity_bq_kg` from `reportable_activity_bq_kg`. Conditional and non-detected results no longer appear as formally reportable activity or concentration values; templates may explicitly request estimated values.
- An efficiency standard without acquisition time is marked as not decay-corrected from reference date to measurement time, yielding a conditional result.
- Evidence snapshots distinguish user-declared certificates, traceability, and geometry from independently verified facts. Nuclear-data entries include versioned check pointers without claiming that all values have been audited.
- Added independent scientific evaluation scaffolding, cross-host trace collection entry points, blank-sample and export-gate regression tests. Real blind-sample accuracy and results on two hosts remain unmeasured.

## What's New in v1.5.0

- Added six deterministic Agent tools with shared JSON Schemas: `inspect_spectrum`, `validate_inputs`, `fit_energy_calibration`, `analyze_ra_th_k`, `validate_analysis`, and `export_report`, exposed through CLI and stdio MCP.
- Made failures in live time, mass, and energy calibration blocking; traceability, geometry/matrix matching, equilibrium, multiplet consistency, and non-detection are machine-readable conditional states.
- Added canonicalized analysis snapshots and SHA-256 evidence fingerprints, with tamper checks for results and nuclear data.
- Clarified that the reported uncertainty covers counting statistics, not a complete combined measurement uncertainty.
- Replaced the fixed K-40 efficiency extrapolation exponent with the slope fitted from the active standard-source peaks. Historical empirical correction is restricted to the exact matching bundled source.

## What's New in v1.4.0

- Added compatible installation for Qoder, ZCode, and DeepSeek Harness while retaining Codex, Claude Code, WorkBuddy, and CodeBuddy support
- Added `qoder`, `zcode`, and `deepseek-harness` installer targets, plus the `deepseek` and `harness` aliases
- Added support for Qoder user/project Skill directories, the ZCode user directory and project import flow, and the DeepSeek Harness `.dsh/skills` directory
- Fixed duplicate writes under `--tool all` when multiple tools share an installation directory, and expanded refresh, enablement, and invocation instructions
- Kept the analysis algorithms, visual interface, four-language export, report templates, and default desktop export location unchanged from v1.3.0

## What's New in v1.3.0

- Replaced the Part 4 placeholder with a **Reports and Extensions** module and redesigned template import, status messages, sample downloads, and template-based export
- Added PDF, DOC, and DOCX report-template import. DOCX and RTF-based DOC templates use `{{report.*}}`, `{{standard.*}}`, and `{{sample.*}}` placeholders and can duplicate sample-table rows; PDF templates use AcroForm fields with the same names
- Added example DOCX and fillable PDF templates. Template inspection reports recognized and unrecognized fields. Legacy binary DOC files receive an explicit instruction to resave as DOCX, avoiding unsafe automatic Office/WPS invocation
- Added Simplified Chinese, Traditional Chinese, English, and French template reports while preserving the current export location and default desktop directory; existing PNG, PDF, and Excel exports remain available

## What's New in v1.2.0

- Added full-energy peak efficiency (probability calibration) for custom calibration sources; the interface and PNG, PDF, and Excel exports now show the source spectrum, per-peak data, and efficiency curve
- Standardized spectrum plots on linear axes: channel (`CH`) on the horizontal axis and counts on the vertical axis; the probability-calibration curve retains log-log axes for efficiency fitting
- Added Word import for custom calibration sources and parameter files, including automatic live-time extraction from fields such as `TLIVE`
- Changed the default export destination to the user's desktop and added unique filenames so an open report is not overwritten; the destination can be changed in the interface
- Improved export APIs and directory selection for the Codex built-in browser, including writable-directory fallback and error reporting

## What's New in v1.1.0

This release updated the original GitHub repository and original Skill name:

- Expanded the interface and PNG, PDF, and Excel export from Chinese/English to Simplified Chinese, Traditional Chinese, English, and French
- Added a raw spectrum plot and an `E = a × CH + b` energy-calibration fit for every test sample
- Synchronized `R / percentage deviation / RMS` across the interface and exported reports; Excel includes both stable chart images and editable scatter charts
- Added PDF, XLS, and XLSX **calibration and analysis parameters** import, automatically recognizing calibration-source mass, reference date, Ra/Th/K activities, ROI, background windows, and optional calibration coefficients
- Improved automatic recognition of `TLIVE`, `LIVE TIME`, `活时间`, and metadata from which real/dead time can be derived
- Added the project icon and updated the detailed tutorial and feedback email addresses

## Main Features

- Import `.xls`, `.xlsx`, `.txt`, `.csv`, `.dat`, `.doc`, and `.docx` spectra. Both sample spectra and custom efficiency-calibration sources may use Word tables or paragraph data.
- Extract calibration-source mass, reference date, Ra/Th/K activities, ROI and background parameters, and optional calibration coefficients from `.pdf`, `.doc`, `.docx`, `.xls`, and `.xlsx` parameter files.
- Recognize `TLIVE`, `LIVE TIME`, `活时间`, and related metadata, with manual entry when reliable metadata is unavailable.
- Use the built-in project efficiency-calibration source or upload a custom traceable standard measured in geometry matching the test samples.
- Calculate `ε(E) = net peak count rate / [activity at measurement time × gamma-emission probability]` for each selected calibration line, explicitly distinguishing nuclear-decay probability `Pγ` from detection probability `ε`, and fit a `ln ε`–`ln E` probability-calibration curve.
- Fit `E = a × CH + b` automatically and report correlation coefficient `R`, percentage deviation, and RMS residual.
- Apply tiered background treatment to major Ra-226, Th-232, and K-40 peaks: IAEA bilateral sideband estimation under normal statistics, adaptive expanded sidebands and SNIP-assisted interference handling at low counts, plus Currie decision thresholds and detection status.
- Report specific activity in Bq/kg and conventional concentration conversions for Ra/Th in ppm and K in percent.
- Compare multiple samples with specific-activity bar charts and include each sample's raw spectrum and calibration fit.
- Provide Simplified Chinese, Traditional Chinese, English, and French interfaces and PNG, PDF, and Excel reports.
- Include both stable rendered fit images and editable native scatter charts in Excel reports.
- Combine the calibration-source spectrum and efficiency curve in the **Calibration source spectrum and probability calibration** view, with synchronized per-peak data and charts in PNG, PDF, and Excel exports.
- Preserve peak position, gross counts, background, net counts, net count rate, fit metrics, and warnings for review.

## Quick Start

### 1. Download

```bash
git clone https://github.com/twinkle-air/ra-th-k-quantitative-1.git
cd ra-th-k-quantitative-1
```

### 2. Install into Agent Tools

Install into the user-level directories of Codex, Claude Code, WorkBuddy, CodeBuddy, Qoder, ZCode, and DeepSeek Harness in one command:

```bash
python scripts/install.py --tool all --scope user
```

Or install for only one tool:

```bash
python scripts/install.py --tool codex --scope user
python scripts/install.py --tool claude --scope user
python scripts/install.py --tool workbuddy --scope user
python scripts/install.py --tool codebuddy --scope user
python scripts/install.py --tool qoder --scope user
python scripts/install.py --tool zcode --scope user
python scripts/install.py --tool deepseek-harness --scope user
```

Example of project-level installation:

```bash
python scripts/install.py --tool all --scope project --project-root /path/to/your/project
```

By default, the installer refuses to overwrite an existing Skill. Add `--force` when an update is intentional; the previous version is first moved to a timestamped backup directory.

To update an existing installation from a newly pulled repository:

```bash
git pull
python scripts/install.py --tool all --scope user --force
```

`--force` replaces only the same-named Skill directory and creates a timestamped backup first. It does not create a second Skill.

### 3. Start the Visual Workbench

Python 3.10 or later is required. On the first run, create an isolated virtual environment and install dependencies automatically:

```bash
python scripts/start_app.py --install
```

For later runs:

```bash
python scripts/start_app.py
```

Open <http://127.0.0.1:8000/> in a browser. The service listens only on the local loopback interface; this project does not proactively upload spectra to the cloud.

The application can be used as a standalone local web app without installing it into any Agent. The default port is `8000`; select another port with, for example, `python scripts/start_app.py --port 8010`.

## Using the Skill with Different Agents

This repository follows the open [Agent Skills specification](https://agentskills.io/specification), with the root `SKILL.md` as its entry point.

| Tool | User-level location | Project-level location | Invocation |
|---|---|---|---|
| Codex | `~/.agents/skills/ra-th-k-quantitative-1` | `.agents/skills/ra-th-k-quantitative-1` | `$ra-th-k-quantitative-1`, or describe the analysis task directly |
| Claude Code | `~/.claude/skills/ra-th-k-quantitative-1` | `.claude/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1`, or describe the analysis task directly |
| WorkBuddy | `~/.workbuddy/skills/ra-th-k-quantitative-1` | `.workbuddy/skills/ra-th-k-quantitative-1` | Ask the Agent to use this Skill |
| CodeBuddy | `~/.codebuddy/skills/ra-th-k-quantitative-1` | `.codebuddy/skills/ra-th-k-quantitative-1` | Ask the Agent to use this Skill |
| Qoder | `~/.qoder/skills/ra-th-k-quantitative-1` | `.qoder/skills/ra-th-k-quantitative-1` | `/ra-th-k-quantitative-1`, or describe the task directly |
| ZCode | `~/.zcode/skills/ra-th-k-quantitative-1` | Install to `.agents/skills/ra-th-k-quantitative-1`, then import it in the current project's settings | `$ra-th-k-quantitative-1` |
| DeepSeek Harness | `~/.dsh/skills/ra-th-k-quantitative-1` | `.dsh/skills/ra-th-k-quantitative-1` | Ask Harness to use this Skill |

Automatic discovery behavior may change between product versions. If the Skill does not appear after installation, restart the tool or begin a new session and name the Skill explicitly. In Qoder CLI, run `/skills reload`. In ZCode, refresh and enable the Skill under **Settings → Skills**; for a project-level installation, use its import function to select the entry under `.agents/skills`. A DeepSeek Harness deployment must enable the local Skill provider/composition. See the [portability guide](references/PORTABILITY.md) for detailed paths.

## Practical Workflow

1. **Verify measurement conditions.** The calibration source and samples should use the same detector and, as far as possible, matching containers, fill height, relative position, matrix, and self-absorption conditions.
2. **Select an efficiency-calibration source.** Use the built-in source only when it matches the original project measurement conditions. Otherwise upload a certified, traceable source spectrum with matching geometry.
3. **Import sample spectra.** Multiple files may be selected. The application attempts to read live time; if reliable metadata is unavailable, enter it manually in seconds.
4. **Enter sample quantity.** Provide the net mass of each sample in grams. The application never infers mass from a filename.
5. **Review parameters.** Import a PDF/Excel parameter file or manually confirm the source reference date, activity, ROI half-width, background gap/window, Ra/Th equilibrium assumptions, and K-40 interference-correction settings.
6. **Run quantitative analysis.** Energy calibration and peak-region calculations are performed separately for each spectral line.
7. **Review the results.** Inspect specific activities, concentrations, detailed intermediate results, sample spectra, and fits. Check `R / deviation / RMS`, the number of valid peaks, and every warning.
8. **Choose an export language.** Generate Simplified Chinese, Traditional Chinese, English, or French PNG, PDF, and Excel files. Confirm that exported fit plots contain both the fitted line and matched calibration points.

See [references/INPUTS_AND_QC.md](references/INPUTS_AND_QC.md) for detailed input and QC requirements, [references/METHOD.md](references/METHOD.md) for algorithm boundaries, and [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) for troubleshooting.

## Principal Gamma Lines and Calculation Notes

Default candidate lines include:

- **Th-232 series:** Pb-212 at 238.632 keV, Tl-208 at 583.187 keV, and Ac-228 at 911.204 keV
- **Ra-226 series:** Pb-214 at 295.224/351.932 keV and Bi-214 at 609.312 keV
- **K-40:** 1460.822 keV

Ra-226 and Th-232 are commonly estimated indirectly from daughter gamma lines. Reports therefore list the actual emitter separately from the analyte. Daughter results must not be treated unconditionally as parent activity when sealing/ingrowth time, equilibrium, or sample handling is inadequate.

Definitions of energy-calibration metrics, concentration-conversion factors, and applicability conditions are documented in [references/METHOD.md](references/METHOD.md). Formal laboratory work should also follow lawfully obtained copies of GB/T 11713-2015 and GB/T 11743-2013 and the user's institutional quality system. This repository does not redistribute the full text of those standards.

## Development and Verification

Run structural checks, Python compilation, and regression tests:

```bash
python scripts/verify.py
```

Application code is located under `assets/app` and can be started independently:

```bash
cd assets/app
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Repository structure:

```text
ra-th-k-quantitative-1/
├── SKILL.md                 # Agent Skill entry point and behavioral constraints
├── agents/openai.yaml       # Codex/OpenAI interface metadata
├── assets/app/              # FastAPI analysis application, default source, and tests
├── references/              # Method, input/QC, portability, and troubleshooting docs
├── scripts/                 # Installation, startup, and verification tools
├── README.md
└── LICENSE
```

## Scientific and Data Responsibilities

- Outputs are auxiliary analysis results and do not automatically constitute an accredited test report.
- Values below detection capability must not be treated as reliable quantitative results without detection-limit evidence.
- For a custom calibration source, the user is responsible for certificate-activity decay correction, nuclide information, and geometry consistency.
- Any change to algorithms or the default source requires renewed validation with traceable standards or QC samples.
- The repository does not contain user-supplied sample spectra, competition reports, national-standard PDFs, or other unauthorized third-party materials.

## License

The code is released under the [MIT License](LICENSE). National standards, calibration certificates, user data, and other third-party materials do not acquire redistribution rights under this license.

## Author and Feedback

**twinkle-air**  
Email: [twinkleair369@gmail.com](mailto:twinkleair369@gmail.com) or [twinkle-air@qq.com](mailto:twinkle-air@qq.com)
