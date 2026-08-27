# Method and scientific boundaries

## Calculation chain

1. Parse the spectrum and recover channel counts, live time, and available metadata.
2. Fit the energy calibration with reference peak pairs using `E = a * CH + b`.
3. Locate the selected Ra, Th, and K characteristic peaks in energy space.
4. Estimate the local continuum with a tiered method: IAEA two-sideband interpolation at ordinary statistics; adaptive expanded sidebands with SNIP-assisted neighbouring-peak rejection for sparse counts. Preserve the signed net area and its uncertainty.
5. Apply a one-sided Currie decision threshold (`Lc`, alpha = 0.05) before treating a peak as detected. A negative or sub-threshold estimate is a non-detection, not a zero activity measurement.
6. Use a calibration source measured with matching geometry to obtain the response for each radionuclide.
7. Calculate sample specific activity from the sample response, calibration response, sample mass, and calibration certificate values.
8. Convert activity concentration to conventional elemental content only when the stated secular-equilibrium assumptions are acceptable.

## Energy-calibration metrics

For reference energies `y`, fitted energies `y_hat`, and `n` matching points:

- `R`: Pearson correlation coefficient between channel and reference energy.
- `RMS = sqrt(mean((y - y_hat)^2))`, reported in keV.
- `Deviation (%) = 100 * sqrt(mean(((y_hat - y) / y)^2))`.

These metrics describe calibration fit quality. They are not a substitute for peak-identification review or detector performance checks.

## Probability calibration / full-energy-peak efficiency

For each usable calibration-source gamma line, the application calculates the full-energy-peak detection probability (efficiency):

`epsilon(E) = net peak count rate / [A(t) * P_gamma]`

Here `A(t)` is the certificate activity decay-corrected to the spectrum acquisition time, and `P_gamma` is the emission probability per decay for that gamma line. `P_gamma` is nuclear-decay data; `epsilon(E)` is the detector-and-geometry response. They are therefore reported in separate columns and must not be confused.

For three or more valid points in the current Ra/Th/K range, the display fits the IAEA-style log-log response model `ln(epsilon) = intercept + slope * ln(E/keV)` by least squares and reports the correlation coefficient and RMS log residual. The fitted curve is diagnostic interpolation for the matched detector/source geometry, not a universal detector property. It must be regenerated after a relevant detector, geometry, container, filling-height, or matrix change.

## Principal reference peaks

The bundled workflow uses these principal gamma lines as candidate analysis references:

| Analysis target | Actual emitter | Energy (keV) |
|---|---|---:|
| Th-232 series | Pb-212 | 238.632 |
| Th-232 series | Tl-208 | 583.187 |
| Th-232 series | Ac-228 | 911.204 |
| Ra-226 series | Pb-214 | 295.224 |
| Ra-226 series | Pb-214 | 351.932 |
| Ra-226 series | Bi-214 | 609.312 |
| K-40 | K-40 | 1460.822 |

The analysis target and the actual gamma emitter are deliberately distinguished. Ra-226 and Th-232 are commonly inferred from daughter emissions only when the sample preparation and equilibrium conditions justify it.

## Optional conventional content conversion

The application reports activity concentration in Bq/kg and also provides conventional content estimates using:

- `Ra (ppm) = Ra-226 activity (Bq/kg) / 36600`
- `Th (ppm) = Th-232 activity (Bq/kg) / 4.056`
- `K (%) = K-40 activity (Bq/kg) / 311`

These factors assume natural isotopic abundance and the conventional activity-to-mass relationships used by this workflow. Preserve the Bq/kg result as the primary measurement result.

## Conditions for valid use

- The efficiency calibration source and sample must have compatible container geometry, filling height, density/self-attenuation behavior, and detector position.
- The live time must be present or entered correctly.
- Peaks must be resolved well enough for the selected local-background method.
- The detector setup must have a valid energy and efficiency calibration for the measurement period.
- Ra-226/Th-232 estimates from daughter nuclides require justified radioactive equilibrium.
- Any negative net peak area is a quality-control signal, not a physical negative activity.
- This workflow does not replace laboratory QA/QC, uncertainty evaluation, blank/reference checks, or accredited method validation.

For formal laboratory work, consult legally obtained copies of GB/T 11713-2015 and GB/T 11743-2013 and the applicable laboratory quality system. The standards PDFs are not redistributed in this repository.

## Background and detection references

- IAEA, *Uncertainty of Gamma Ray Spectrometry Measurements*: net peak area `N = G - B` and the two-sideband background-uncertainty expression.
- C.G. Ryan et al., “SNIP, a statistics-sensitive background treatment…”, *NIM B* 34 (1988) 396–402, DOI `10.1016/0168-583X(88)90063-8`.
- L.A. Currie, “Limits for qualitative detection and quantitative determination”, *Analytical Chemistry* 40 (1968) 586–593, DOI `10.1021/ac60259a007`.
- IAEA, *Quality Control Atlas for Scintillation Camera Systems*, TECDOC-1092, efficiency-calibration least-squares treatment in `ln(efficiency)` versus `ln(energy)` over the stated gamma-energy range.
- IAEA, *Quantitative Nuclear Medicine Imaging: Concepts, Requirements and Methods*, TECDOC-1741, distinction between gamma emission intensity/probability and full-energy-peak efficiency.
- NIST, *Procedure 23: Calibration of Germanium Gamma-Ray Detectors*, activity, emission-probability and full-energy-peak-efficiency calibration framework.
