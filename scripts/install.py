#!/usr/bin/env python3
"""Install this Agent Skill into supported user or project discovery paths."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil


SKILL_NAME = "ra-th-k-quantitative-1"
SKILL_ROOT = Path(__file__).resolve().parents[1]
USER_ROOTS = {
    "codex": Path.home() / ".agents" / "skills",
    "claude": Path.home() / ".claude" / "skills",
    "workbuddy": Path.home() / ".workbuddy" / "skills",
    "codebuddy": Path.home() / ".codebuddy" / "skills",
}
PROJECT_ROOTS = {
    "codex": Path(".agents") / "skills",
    "claude": Path(".claude") / "skills",
    "workbuddy": Path(".workbuddy") / "skills",
    "codebuddy": Path(".codebuddy") / "skills",
}


def copy_skill(destination: Path, force: bool) -> Path:
    destination = destination.resolve()
    if destination == SKILL_ROOT or SKILL_ROOT in destination.parents:
        raise ValueError(f"Refusing to install inside the source Skill: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not force:
            raise FileExistsError(f"Already exists: {destination}. Re-run with --force to replace it safely.")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = destination.with_name(f"{destination.name}.backup-{stamp}")
        destination.replace(backup)
        print(f"Backed up existing Skill to {backup}")
    shutil.copytree(
        SKILL_ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".review",
            ".venv",
            ".runtime",
            "build",
            "dist",
            "__pycache__",
            "*.egg-info",
            "*.pyc",
            "*.pyo",
        ),
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Ra–Th–K Quantitative 1 into an Agent Skills directory.")
    parser.add_argument("--tool", choices=[*USER_ROOTS, "all"], default="all")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--force", action="store_true", help="Back up and replace an existing installation.")
    args = parser.parse_args()
    tools = list(USER_ROOTS) if args.tool == "all" else [args.tool]
    installed: list[Path] = []
    for tool in tools:
        base = USER_ROOTS[tool] if args.scope == "user" else args.project_root.resolve() / PROJECT_ROOTS[tool]
        installed.append(copy_skill(base / SKILL_NAME, args.force))
    for path in installed:
        print(f"Installed: {path}")
    print("Restart or reload the Agent if the Skill does not appear immediately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
