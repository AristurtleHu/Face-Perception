"""Helpers for locating project resources in source and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Return an absolute path rooted at the app bundle or repository root."""
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS"))
    else:
        base_path = Path(__file__).resolve().parents[1]
    return base_path.joinpath(*parts)
