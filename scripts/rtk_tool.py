#!/usr/bin/env python3
"""Portable CLI for the deterministic Ra-Th-K Agent tools."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from start_app import APP_ROOT, choose_python


TOOL_NAMES = (
    "inspect_spectrum", "validate_inputs", "fit_energy_calibration",
    "analyze_ra_th_k", "validate_analysis", "export_report",
)


def _bootstrap(install: bool) -> None:
    if os.environ.get("RTK_TOOL_BOOTSTRAPPED") == "1":
        return
    python = choose_python(install)
    if Path(sys.executable).resolve() == python.resolve():
        return
    environment = dict(os.environ)
    environment["RTK_TOOL_BOOTSTRAPPED"] = "1"
    raise SystemExit(subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]], env=environment))


def _read_request(path: str) -> dict:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(text or "{}")
    if not isinstance(value, dict):
        raise ValueError("Tool input must be a JSON object.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic Ra-Th-K Agent tool CLI.")
    parser.add_argument("tool", choices=TOOL_NAMES)
    parser.add_argument("--input", default="-", help="UTF-8 request JSON file, or - for stdin.")
    parser.add_argument("--output", help="Optional UTF-8 result JSON file; stdout is always available.")
    parser.add_argument("--install", action="store_true", help="Create/update the project runtime if needed.")
    parser.add_argument("--describe", action="store_true", help="Print this tool's JSON Schemas without running it.")
    args = parser.parse_args()
    _bootstrap(args.install)
    sys.path.insert(0, str(APP_ROOT))
    from app.services.agent_tools import invoke_tool, tool_definition

    if args.describe:
        result = tool_definition(args.tool)
        exit_code = 0
    else:
        try:
            result = invoke_tool(args.tool, _read_request(args.input))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            result = {
                "schema_version": "1.0.0", "tool": args.tool, "status": "error",
                "error_code": "invalid_request", "message": str(exc), "issues": [], "data": None,
            }
        exit_code = 0 if result.get("status") != "error" else 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
