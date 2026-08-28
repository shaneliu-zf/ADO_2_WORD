#!/usr/bin/env python3
"""讀取專案設定檔。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.utils.paths import CONFIG_PATH

CONFIG_KEYS = ("organization", "project", "pat", "ado_base_url", "bob_api_key")
PLACEHOLDER_PATS = {"", "你的 PAT", "YOUR_PAT"}
DEMO_TRUE = {"1", "true", "yes", "on"}


def parse_demo_mode(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in DEMO_TRUE


def is_demo_mode(config: dict[str, Any] | None = None) -> bool:
    """展示模式：用虛構 ADO／範本，不連客戶 Azure DevOps。"""
    if config is not None:
        return parse_demo_mode(config.get("demo_mode"))
    if not CONFIG_PATH.exists():
        return False
    try:
        data = load_json_file(CONFIG_PATH)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    return parse_demo_mode(data.get("demo_mode"))


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
            "請在網頁左上角齒輪填寫組織、專案與 PAT 後儲存。"
        )
    config = load_json_file(CONFIG_PATH)
    if not isinstance(config, dict):
        raise ValueError(
            f"{CONFIG_PATH} 必須是 JSON 物件，例如 {{\"organization\": \"...\", \"pat\": \"...\"}}"
        )

    config["demo_mode"] = parse_demo_mode(config.get("demo_mode"))
    if config["demo_mode"]:
        config["organization"] = str(config.get("organization") or "demo-org").strip() or "demo-org"
        config["project"] = str(config.get("project") or "LumenWMS").strip() or "LumenWMS"
        config["pat"] = str(config.get("pat") or "demo").strip() or "demo"
        if not str(config.get("ado_base_url") or "").strip():
            config["ado_base_url"] = "https://dev.azure.com"
        config["bob_api_key"] = str(config.get("bob_api_key") or "").strip()
        return config

    pat = str(config.get("pat") or "").strip()
    if not pat or pat in {"你的 PAT", "YOUR_PAT"}:
        raise ValueError('請在 backend/secrets/config.json 的 "pat" 欄位貼上 Personal Access Token。')

    config["pat"] = pat
    return config


def empty_config() -> dict[str, Any]:
    return {
        "organization": "",
        "project": "",
        "pat": "",
        "ado_base_url": "https://dev.azure.com",
        "bob_api_key": "",
        "demo_mode": False,
    }


def read_config_file() -> dict[str, Any]:
    """讀取設定檔供 UI 編輯；檔案不存在則回空值，不拋錯。"""
    payload = empty_config()
    if not CONFIG_PATH.exists():
        return payload
    data = load_json_file(CONFIG_PATH)
    if not isinstance(data, dict):
        raise ValueError(f"{CONFIG_PATH} 必須是 JSON 物件")
    for key in CONFIG_KEYS:
        value = data.get(key)
        if value is None:
            continue
        payload[key] = str(value).strip()
    payload["demo_mode"] = parse_demo_mode(data.get("demo_mode"))
    if not payload["ado_base_url"]:
        payload["ado_base_url"] = "https://dev.azure.com"
    return payload


def save_config(updates: dict[str, Any]) -> dict[str, Any]:
    """寫入 backend/secrets/config.json，只更新允許的欄位。"""
    existing: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        data = load_json_file(CONFIG_PATH)
        if isinstance(data, dict):
            existing = data
    payload = empty_config()
    for key in CONFIG_KEYS:
        if key in existing and existing[key] is not None:
            payload[key] = str(existing[key]).strip()
    payload["demo_mode"] = parse_demo_mode(existing.get("demo_mode"))
    for key in CONFIG_KEYS:
        if key not in updates:
            continue
        payload[key] = str(updates.get(key) or "").strip()
    if "demo_mode" in updates:
        payload["demo_mode"] = parse_demo_mode(updates.get("demo_mode"))
    if not payload["ado_base_url"]:
        payload["ado_base_url"] = "https://dev.azure.com"

    if not payload["demo_mode"]:
        missing = [key for key in ("organization", "project", "pat", "bob_api_key") if not payload[key]]
        if missing:
            raise ValueError("請填寫：" + "、".join(missing))
        if payload["pat"] in PLACEHOLDER_PATS:
            raise ValueError('請在 "pat" 欄位貼上 Personal Access Token。')

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    out: dict[str, Any] = dict(existing)
    out.update(payload)
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
