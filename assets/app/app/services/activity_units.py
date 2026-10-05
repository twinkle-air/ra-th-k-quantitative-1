"""Shared content conversion; ppm means mg of the stated isotope per kg."""
from __future__ import annotations

import json
import math
from pathlib import Path

NUCLEAR_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "nuclear_data.json"
NUCLEAR_DATA = json.loads(NUCLEAR_DATA_FILE.read_text(encoding="utf-8"))


def bq_kg_per_ppm(half_life_years: float, molar_mass_g_mol: float) -> float:
    """Activity of 1 mg/kg (1 ppm); Julian year = 365.25 days."""
    return math.log(2) * 6.02214076e23 / (half_life_years * 365.25 * 86400 * molar_mass_g_mol) * 1e-3


ACTIVITY_CONVERSION = dict(NUCLEAR_DATA["activity_conversion"])
_ra = NUCLEAR_DATA["content_conversion_basis"]["Ra226"]
_derived_ra = bq_kg_per_ppm(NUCLEAR_DATA["half_life_years"]["Ra226"], _ra["molar_mass_g_mol"])
if not math.isclose(ACTIVITY_CONVERSION["ra226_bq_kg_per_ppm"], _derived_ra, rel_tol=1e-12):
    raise ValueError("Ra-226 ppm conversion disagrees with the declared half-life/molar-mass basis")
CONTENT_DIVISORS = {
    "Ra226": _derived_ra,
    "Th232": ACTIVITY_CONVERSION["th232_bq_kg_per_ppm"],
    "K40": ACTIVITY_CONVERSION["k40_bq_kg_per_percent_k"],
}


def activity_to_content(activity: float | None, nuclide: str) -> float | None:
    return activity / CONTENT_DIVISORS[nuclide] if isinstance(activity, (int, float)) and math.isfinite(activity) else None
