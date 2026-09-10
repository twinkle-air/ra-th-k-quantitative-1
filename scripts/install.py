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
    "qoder": Path.home() / ".qoder" / "skills",
    "zcode": Path.home() / ".zcode" / "skills",
    "deepseek-harness": Path.home() / ".dsh" / "skills",
}
PROJECT_ROOTS = {
    "codex": Path(".agents") / "skills",
    "claude": Path(".claude") / "skills",
    "workbuddy": Path(".workbuddy") / "skills",
    "codebuddy": Path(".codebuddy") / "skills",
    "qoder": Path(".qoder") / "skills",
    # ZCode supports project-scoped imports from external Agent roots.
    "zcode": Path(".agents") / "skills",
    "deepseek-harness": Path(".dsh") / "skills",
}

TOOL_ALIASES = {
    "deepseek": "deepseek-harness",
    "harness": "deepseek-harness",
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
            "exports",
            "__pycache__",
            "*.egg-info",
            "*.pyc",
            "*.pyo",
        ),
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Ra–Th–K Quantitative 1 into an Agent Skills directory.")
    parser.add_argument("--tool", choices=[*USER_ROOTS, *TOOL_ALIASES, "all"], default="all")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--force", action="store_true", help="Back up and replace an existing installation.")
    args = parser.parse_args()
    selected_tool = TOOL_ALIASES.get(args.tool, args.tool)
    tools = list(USER_ROOTS) if selected_tool == "all" else [selected_tool]
    installed: list[Path] = []
    seen_destinations: set[Path] = set()
    for tool in tools:
        base = USER_ROOTS[tool] if args.scope == "user" else args.project_root.resolve() / PROJECT_ROOTS[tool]
        destination = (base / SKILL_NAME).resolve()
        if destination in seen_destinations:
            continue
        seen_destinations.add(destination)
        installed.append(copy_skill(destination, args.force))
    for path in installed:
        print(f"Installed: {path}")
    print("Restart or reload the Agent if the Skill does not appear immediately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
