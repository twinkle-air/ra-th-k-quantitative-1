#!/usr/bin/env python3
"""Start the bundled local Ra-Th-K analysis workbench."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import venv


SKILL_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = SKILL_ROOT / "assets" / "app"
RUNTIME_ROOT = SKILL_ROOT / ".runtime"


def venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def imports_work(python: Path) -> bool:
    command = [
        str(python),
        "-c",
        "import fastapi,uvicorn,multipart,numpy,openpyxl,xlrd,PIL,reportlab,pypdf",
    ]
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def choose_python(install: bool) -> Path:
    local_python = venv_python(RUNTIME_ROOT / "venv")
    if local_python.exists() and imports_work(local_python):
        return local_python
    current = Path(sys.executable)
    if imports_work(current) and not install:
        return current
    if not install:
        raise RuntimeError("Dependencies are missing. Run: python scripts/start_app.py --install")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if not local_python.exists():
        venv.EnvBuilder(with_pip=True).create(RUNTIME_ROOT / "venv")
    subprocess.run(
        [str(local_python), "-m", "pip", "install", "-r", str(APP_ROOT / "requirements.txt")],
        check=True,
    )
    return local_python


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the local Ra-Th-K quantitative analysis web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--install", action="store_true", help="Create a local venv and install dependencies.")
    args = parser.parse_args()
    if not (APP_ROOT / "app" / "main.py").exists():
        raise FileNotFoundError(f"Bundled application is missing: {APP_ROOT}")
    python = choose_python(args.install)
    print(f"Starting Ra–Th–K Quantitative 1 at http://{args.host}:{args.port}/")
    return subprocess.call(
        [str(python), "-m", "uvicorn", "app.main:app", "--host", args.host, "--port", str(args.port)],
        cwd=APP_ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
