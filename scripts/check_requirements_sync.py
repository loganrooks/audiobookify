#!/usr/bin/env python3
"""Verify requirements.txt matches [project.dependencies] in pyproject.toml.

The Dockerfile installs requirements.txt as a separate layer for build caching,
so the file has to exist alongside pyproject.toml. That duplication silently
drifts. This check makes drift a CI failure instead of a production surprise.

Usage: python scripts/check_requirements_sync.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize(lines: list[str]) -> set[str]:
    """Strip comments and whitespace, returning the set of requirement specs."""
    out = set()
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            # Normalize whitespace and quote style so cosmetic differences
            # (e.g. '3.13' vs "3.13") don't register as drift.
            out.add(line.replace(" ", "").replace('"', "'"))
    return out


def main() -> int:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    declared = normalize(pyproject["project"]["dependencies"])
    pinned = normalize((ROOT / "requirements.txt").read_text().splitlines())

    missing = declared - pinned
    extra = pinned - declared

    if not missing and not extra:
        print(f"requirements.txt is in sync with pyproject.toml ({len(declared)} deps)")
        return 0

    print("requirements.txt is OUT OF SYNC with pyproject.toml [project.dependencies]")
    for dep in sorted(missing):
        print(f"  missing from requirements.txt: {dep}")
    for dep in sorted(extra):
        print(f"  not declared in pyproject.toml: {dep}")
    print("\nUpdate requirements.txt to match, then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
