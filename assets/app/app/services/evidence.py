"""Build reproducible analysis evidence packages and SHA-256 fingerprints."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
from typing import Any, Iterable

import rfc8785

from ..version import ALGORITHM_VERSION, SKILL_VERSION, TOOL_SCHEMA_VERSION


APP_ROOT = Path(__file__).resolve().parents[2]
NUCLEAR_DATA_FILE = APP_ROOT / "data" / "nuclear_data.json"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_identity(name: str, payload: bytes, role: str) -> dict[str, Any]:
    return {"name": name, "role": role, "size_bytes": len(payload), "sha256": sha256_bytes(payload)}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return RFC 8785 canonical bytes after rejecting non-JSON numeric values."""
    return rfc8785.dumps(_json_safe(value))


def nuclear_data_identity() -> dict[str, Any]:
    payload = NUCLEAR_DATA_FILE.read_bytes()
    data = json.loads(payload.decode("utf-8"))
    return {
        "dataset_id": data["dataset_id"],
        "version": data["version"],
        "status": data["status"],
        "sha256": sha256_bytes(payload),
        "relative_path": "assets/app/data/nuclear_data.json",
        "value_provenance": data.get("value_provenance", {}),
    }


def dependency_versions(names: Iterable[str] = ("fastapi", "numpy", "openpyxl", "xlrd", "rfc8785", "jsonschema")) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def attach_evidence(
    analysis: dict[str, Any],
    *,
    input_files: list[dict[str, Any]],
    parameters: dict[str, Any],
    standard_identity: dict[str, Any],
) -> dict[str, Any]:
    """Attach a canonical snapshot fingerprint without including volatile timestamps."""
    output = _json_safe(deepcopy(analysis))
    output.pop("evidence", None)
    analysis_snapshot = deepcopy(output)
    snapshot = {
        "schema_version": TOOL_SCHEMA_VERSION,
        "skill": {"name": "ra-th-k-quantitative-1", "version": SKILL_VERSION},
        "algorithm_version": ALGORITHM_VERSION,
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "dependencies": dependency_versions(),
        },
        "nuclear_data": nuclear_data_identity(),
        "input_files": input_files,
        "standard_identity": standard_identity,
        "assertion_provenance": {
            "certificate_id": "user_supplied_not_independently_verified",
            "traceability_claim": "user_supplied_not_independently_verified",
            "reference_activities_bq": "user_supplied_not_independently_verified",
            "geometry_match": "user_supplied_not_independently_verified",
            "matrix_match": "user_supplied_not_independently_verified",
            "chain_equilibrium": "user_supplied_not_independently_verified",
            "note": "SHA-256 detects changes to this snapshot but does not authenticate the original assertions.",
        },
        "parameters": _json_safe(parameters),
        "analysis": analysis_snapshot,
    }
    canonical = canonical_json_bytes(snapshot)
    fingerprint = sha256_bytes(canonical)
    output["evidence"] = {
        "snapshot_format": "RFC8785-JCS",
        "hash_algorithm": "SHA-256",
        "snapshot_sha256": fingerprint,
        "snapshot": snapshot,
    }
    return output


def verify_evidence(analysis: dict[str, Any]) -> tuple[bool, str | None]:
    evidence = analysis.get("evidence") or {}
    snapshot = evidence.get("snapshot")
    expected = evidence.get("snapshot_sha256")
    if not isinstance(snapshot, dict) or not isinstance(expected, str):
        return False, "missing_evidence_snapshot"
    actual = sha256_bytes(canonical_json_bytes(snapshot))
    current = _json_safe(deepcopy(analysis))
    current.pop("evidence", None)
    content_matches = canonical_json_bytes(current) == canonical_json_bytes(snapshot.get("analysis"))
    nuclear_data_matches = snapshot.get("nuclear_data", {}).get("sha256") == nuclear_data_identity()["sha256"]
    return actual == expected and content_matches and nuclear_data_matches, actual
