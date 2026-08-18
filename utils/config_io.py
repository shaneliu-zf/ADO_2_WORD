#!/usr/bin/env python3
"""讀取專案設定檔。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.paths import CONFIG_PATH


def load_json_file(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} JSON 格式錯誤：第 {exc.lineno} 行第 {exc.colno} 欄。\n"
            "請確認鍵名都有雙引號、沒有註解，且最後一個欄位後面沒有逗號。"
        ) from exc


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"找不到設定檔：{CONFIG_PATH}\n"
            "請複製 secrets/config.json.example 為 secrets/config.json，再填入組織、專案與 PAT。"
        )
    config = load_json_file(CONFIG_PATH)
    if not isinstance(config, dict):
        raise ValueError(
            f"{CONFIG_PATH} 必須是 JSON 物件，例如 {{\"organization\": \"...\", \"pat\": \"...\"}}"
        )

    pat = str(config.get("pat") or "").strip()
    if not pat or pat in {"你的 PAT", "YOUR_PAT"}:
        raise ValueError('請在 secrets/config.json 的 "pat" 欄位貼上 Personal Access Token。')

    config["pat"] = pat
    return config
