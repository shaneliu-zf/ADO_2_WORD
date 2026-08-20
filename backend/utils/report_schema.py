#!/usr/bin/env python3
"""測試報告 JSON 的共用資料契約。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict, cast

from backend.utils.paths import JSON_DIR


class TestItem(TypedDict):
    no: int
    item_name: str
    test_data: list[str]
    expected_result: str
    test_result: str


class TestStep(TypedDict):
    no: int
    description: str
    images: list[str]


class ChangeEntry(TypedDict):
    date: str
    by: str
    field: str
    old: str
    new: str


class Report(TypedDict):
    ado_id: int
    ado_ids: list[int]
    redmine_id: str
    ado_subject: str
    test_environment: str
    site: str
    version: str
    test_date: str
    tester: str
    reviewer: str
    test_items: list[TestItem]
    test_steps: list[TestStep]
    change_history: list[ChangeEntry]


META_FIELDS: tuple[tuple[str, str], ...] = (
    ("ADO主旨", "ado_subject"),
    ("測試環境", "test_environment"),
    ("Site", "site"),
    ("版本號", "version"),
    ("測試日期", "test_date"),
    ("測試人員", "tester"),
    ("審核人員", "reviewer"),
)

REQUIRED_REPORT_KEYS = {
    "ado_id",
    "ado_ids",
    "ado_subject",
    "test_items",
    "test_steps",
}


def validate_report(payload: Any, source: Path | str = "報告 JSON") -> Report:
    if not isinstance(payload, dict):
        raise ValueError(f"{source} 必須是 JSON 物件")
    missing = sorted(REQUIRED_REPORT_KEYS - payload.keys())
    if missing:
        raise ValueError(f"{source} 缺少欄位：{', '.join(missing)}")
    # ado_ids 空陣列時嘗試從 ado_id 補回，相容前端只帶 ado_id 的情況
    if not isinstance(payload["ado_ids"], list) or not payload["ado_ids"]:
        if payload.get("ado_id"):
            payload["ado_ids"] = [int(payload["ado_id"])]
        else:
            raise ValueError(f"{source} 的 ado_ids 必須是非空陣列")
    if not isinstance(payload["test_items"], list):
        raise ValueError(f"{source} 的 test_items 必須是陣列")
    if not isinstance(payload["test_steps"], list):
        raise ValueError(f"{source} 的 test_steps 必須是陣列")
    return cast(Report, payload)


def find_report(work_item_id: int) -> Report | None:
    """找到包含此 ADO ID 的 Bob 報告（合併組可能存在最小 ID 的檔名）。"""
    if not JSON_DIR.exists():
        return None
    path = JSON_DIR / f"work_item_{work_item_id}.json"
    candidates = []
    if path.exists():
        candidates.append(path)
    candidates.extend(
        candidate
        for candidate in sorted(JSON_DIR.glob("work_item_*.json"))
        if candidate != path
    )
    for candidate in candidates:
        try:
            payload = validate_report(
                json.loads(candidate.read_text(encoding="utf-8")),
                candidate,
            )
        except (ValueError, OSError):
            continue
        ado_ids = [
            int(value)
            for value in (payload.get("ado_ids") or [payload.get("ado_id")])
            if value is not None
        ]
        if work_item_id in ado_ids:
            return payload
    return None


def list_report_ids() -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    if not JSON_DIR.exists():
        return ids
    for candidate in sorted(JSON_DIR.glob("work_item_*.json")):
        try:
            payload = validate_report(
                json.loads(candidate.read_text(encoding="utf-8")),
                candidate,
            )
        except (ValueError, OSError):
            continue
        for value in payload.get("ado_ids") or [payload.get("ado_id")]:
            if value is None:
                continue
            work_item_id = int(value)
            if work_item_id not in seen:
                seen.add(work_item_id)
                ids.append(work_item_id)
    return ids
