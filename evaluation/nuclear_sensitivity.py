#!/usr/bin/env python3
"""Reproducible, *counterfactual* K-40 nuclear-data sensitivity.

This script does not change the production nuclear-data table or claim an
independent measurement validation. It isolates algebraic effects that can be
calculated without a held-out spectrum.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "assets/app/data/nuclear_data.json").read_text(encoding="utf-8"))

# DDEP K-40 evaluation (May 2025), DOI-independent official PDF:
# https://www.bipm.org/documents/d/guest/k-40_report
EVALUATED_K40 = {
    "half_life_years": 1.2522e9,
    "gamma_energy_keV": 1460.822,
    "gamma_probability": 0.1034,
    "natural_abundance_amount_fraction": 0.00011668,
}
# CIAAW potassium standard atomic weight and exact SI Avogadro constant.
NATURAL_K_MOLAR_MASS_G_MOL = 39.0983
AVOGADRO_MOL_INV = 6.02214076e23
DAYS_PER_YEAR = 365.2425  # Computational convention; not a DDEP datum.


def decay_factor(years: float, half_life_years: float) -> float:
    return 2 ** (-years / half_life_years)


def evaluated_k_activity_per_percent() -> float:
    """Bq/kg for 1 mass percent of natural K (10 g K per kg material)."""
    atoms_k40 = (10 / NATURAL_K_MOLAR_MASS_G_MOL) * AVOGADRO_MOL_INV * EVALUATED_K40["natural_abundance_amount_fraction"]
    seconds = EVALUATED_K40["half_life_years"] * DAYS_PER_YEAR * 86400
    return atoms_k40 * math.log(2) / seconds


def sensitivity(elapsed_years: float = 11.0) -> dict[str, object]:
    legacy_half_life = DATA["half_life_years"]["K40"]
    legacy_probability = next(x["emission_probability"] for x in DATA["gamma_lines"] if x["target"] == "K40")
    legacy_conversion = DATA["activity_conversion"]["k40_bq_kg_per_percent_k"]
    evaluated_conversion = evaluated_k_activity_per_percent()
    return {
        "analysis_type": "analytic_parameter_sensitivity_not_blind_sample_validation",
        "production_data_unchanged": True,
        "elapsed_years_example": elapsed_years,
        "legacy": {"half_life_years": legacy_half_life, "gamma_probability": legacy_probability,
                   "bq_kg_per_percent_k": legacy_conversion},
        "evaluated_counterfactual": {**EVALUATED_K40, "bq_kg_per_percent_k": evaluated_conversion},
        "effects_percent": {
            # A standard's activity is propagated from its reference date to acquisition time.
            "standard_activity_decay_new_vs_old": 100 * (decay_factor(elapsed_years, EVALUATED_K40["half_life_years"])
                                                        / decay_factor(elapsed_years, legacy_half_life) - 1),
            # The direct, same-line sample/standard rate ratio cancels gamma probability.
            "direct_same_line_K40_activity_from_gamma_probability": 0.0,
            "absolute_efficiency_based_K40_activity_from_gamma_probability": 100 * (legacy_probability / EVALUATED_K40["gamma_probability"] - 1),
            "K_mass_percent_at_fixed_activity_from_conversion": 100 * (legacy_conversion / evaluated_conversion - 1),
        },
        "limitations": [
            "Gamma probability cancels only in the direct same-line sample/standard activity ratio; it does not cancel in absolute efficiency inference.",
            "The conversion estimate uses DDEP isotopic abundance and half-life, CIAAW natural-K atomic weight, and an explicit days-per-year convention.",
            "No sample spectrum, efficiency fit, peak area or interference correction was reprocessed here.",
            "Neither evaluated nuclear data nor the new conversion have been adopted by the production analysis.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(sensitivity(), ensure_ascii=False, indent=2, allow_nan=False))
