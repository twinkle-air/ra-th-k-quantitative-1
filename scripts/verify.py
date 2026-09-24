#!/usr/bin/env python3
"""One-command structural, contract, compile and regression verification."""
from __future__ import annotations
import argparse
import compileall
import json
import os
from pathlib import Path
import subprocess
import sys
from start_app import APP_ROOT, choose_python

SKILL_ROOT = Path(__file__).resolve().parents[1]

def _bootstrap(install: bool) -> None:
    if os.environ.get("RTK_VERIFY_BOOTSTRAPPED") == "1":
        return
    python = choose_python(install)
    if Path(sys.executable).resolve() == python.resolve():
        return
    environment = dict(os.environ)
    environment["RTK_VERIFY_BOOTSTRAPPED"] = "1"
    raise SystemExit(subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]], env=environment))

def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Ra-Th-K Quantitative 1.")
    parser.add_argument("--install", action="store_true", help="Create/update the project-local runtime if needed.")
    args = parser.parse_args()
    try:
        _bootstrap(args.install)
    except RuntimeError as exc:
        print(json.dumps({"status": "dependency_error", "message": str(exc),
                          "next_command": "python scripts/verify.py --install"}, ensure_ascii=False, indent=2))
        return 2
    required = [
        SKILL_ROOT / "SKILL.md", SKILL_ROOT / "agents" / "openai.yaml",
        APP_ROOT / "app" / "main.py", APP_ROOT / "data" / "default_calibration_source.xls",
        APP_ROOT / "data" / "nuclear_data.json", APP_ROOT / "tests" / "test_core.py",
        APP_ROOT / "tests" / "test_agent_tools.py", SKILL_ROOT / "schemas" / "tool-registry.json",
        SKILL_ROOT / "scripts" / "rtk_tool.py", SKILL_ROOT / "scripts" / "mcp_server.py",
        SKILL_ROOT / "evaluation" / "evaluate.py",
    ]
    missing = [str(path.relative_to(SKILL_ROOT)) for path in required if not path.exists()]
    checks: dict[str, object] = {"python": sys.executable, "missing": missing}
    if missing:
        print(json.dumps({"status": "failed", "checks": checks}, ensure_ascii=False, indent=2))
        return 1
    sys.path.insert(0, str(APP_ROOT))
    from jsonschema import Draft202012Validator
    from app.services.agent_tools import tool_registry
    from app.version import SKILL_VERSION
    registry = tool_registry()
    for definition in registry["tools"]:
        Draft202012Validator.check_schema({"$schema": registry["$schema"], "$defs": registry["$defs"],
                                           **definition["inputSchema"]})
    checks["tool_count"] = len(registry["tools"])
    checks["skill_version"] = SKILL_VERSION
    checks["compiled"] = compileall.compile_dir(APP_ROOT / "app", quiet=1)
    checks["scripts_compiled"] = compileall.compile_dir(SKILL_ROOT / "scripts", quiet=1)
    try:
        for name in ("evaluate.py", "nuclear_sensitivity.py"):
            path = SKILL_ROOT / "evaluation" / name
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        checks["evaluation_compiled"] = True
    except SyntaxError:
        checks["evaluation_compiled"] = False
    if not checks["compiled"] or not checks["scripts_compiled"] or not checks["evaluation_compiled"]:
        print(json.dumps({"status": "failed", "checks": checks}, ensure_ascii=False, indent=2))
        return 1
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=APP_ROOT)
    checks["tests_exit_code"] = result.returncode
    status = "passed" if result.returncode == 0 else "failed"
    print(json.dumps({"status": status, "checks": checks}, ensure_ascii=False, indent=2))
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
