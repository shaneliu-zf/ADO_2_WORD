#!/usr/bin/env python3
"""讀寫 JSON 檔。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_or(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return read_json(path)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
