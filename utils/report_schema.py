#!/usr/bin/env python3
"""測試報告 JSON 的共用資料契約。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict, cast


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
    if not isinstance(payload["ado_ids"], list) or not payload["ado_ids"]:
        raise ValueError(f"{source} 的 ado_ids 必須是非空陣列")
    if not isinstance(payload["test_items"], list):
        raise ValueError(f"{source} 的 test_items 必須是陣列")
    if not isinstance(payload["test_steps"], list):
        raise ValueError(f"{source} 的 test_steps 必須是陣列")
    return cast(Report, payload)
