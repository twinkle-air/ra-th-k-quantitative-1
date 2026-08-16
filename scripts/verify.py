#!/usr/bin/env python3
"""Verify the Skill structure and run the bundled application's regression tests."""

from __future__ import annotations

from pathlib import Path
import compileall
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = SKILL_ROOT / "assets" / "app"


def main() -> int:
    required = [
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "agents" / "openai.yaml",
        APP_ROOT / "app" / "main.py",
        APP_ROOT / "data" / "default_calibration_source.xls",
        APP_ROOT / "tests" / "test_core.py",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("Missing required files:")
        for path in missing:
            print(f"- {path}")
        return 1
    if not compileall.compile_dir(APP_ROOT / "app", quiet=1):
        return 1
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=APP_ROOT,
    )
    if result.returncode:
        return result.returncode
    print("Skill bundle verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
