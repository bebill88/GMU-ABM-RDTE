"""
Utility helpers used across the ABM project.
Keep this file *boring* and dependency-light.
"""
from __future__ import annotations

import os
import json
import random
import time
import hashlib
from typing import Any, Dict


def set_global_seed(seed: int | None) -> None:
    """
    Seed Python's random module for reproducibility.
    If `seed` is None, we do nothing (useful for ad‑hoc runs).
    """
    if seed is None:
        return
    random.seed(seed)


def now_ms() -> int:
    """Return current time in milliseconds (Unix epoch)."""
    return int(time.time() * 1000)


def sha1_of_dict(d: Dict[str, Any]) -> str:
    """
    Deterministically hash a dictionary (sorted keys) to capture config identity.
    Useful for tagging output folders / metadata.
    """
    s = json.dumps(d, sort_keys=True).encode("utf-8")
    return hashlib.sha1(s).hexdigest()


def ensure_dir(path: str) -> None:
    """Create a directory if it does not exist (no error if it already exists)."""
    os.makedirs(path, exist_ok=True)
