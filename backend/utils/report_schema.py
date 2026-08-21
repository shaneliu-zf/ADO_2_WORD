#!/usr/bin/env python3
"""測試報告 JSON 的共用資料契約。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict, cast

from backend.utils.json_io import read_json
from backend.utils.paths import JSON_DIR, report_json_path


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


class CommitEntry(TypedDict, total=False):
    sha: str
    sha_short: str
    message: str
    author: str
    date: str
    url: str
    ado_id: int


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
    commits: list[CommitEntry]


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
OPTIONAL_STRING_KEYS = (
    "redmine_id",
    "test_environment",
    "site",
    "version",
    "test_date",
    "tester",
    "reviewer",
)


def _as_int(value: Any, field: str, source: Path | str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source} 的 {field} 必須是整數") from exc


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_as_str(item) for item in value]
    text = _as_str(value)
    return [text] if text else []


def _validate_test_item(item: Any, index: int, source: Path | str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"{source} 的 test_items[{index}] 必須是物件")
    row = dict(item)
    row["no"] = _as_int(item.get("no") or index + 1, f"test_items[{index}].no", source)
    row["item_name"] = _as_str(item.get("item_name"))
    row["test_data"] = _as_str_list(item.get("test_data"))
    row["expected_result"] = _as_str(item.get("expected_result"))
    row["test_result"] = _as_str(item.get("test_result"))
    return row


def _validate_test_step(step: Any, index: int, source: Path | str) -> dict[str, Any]:
    if not isinstance(step, dict):
        raise ValueError(f"{source} 的 test_steps[{index}] 必須是物件")
    row = dict(step)
    row["no"] = _as_int(step.get("no") or index + 1, f"test_steps[{index}].no", source)
    row["description"] = _as_str(step.get("description"))
    row["images"] = _as_str_list(step.get("images"))
    return row


def _validate_commit(entry: Any, index: int, source: Path | str) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"{source} 的 commits[{index}] 必須是物件")
    row = dict(entry)
    if "ado_id" in row and row["ado_id"] is not None and row["ado_id"] != "":
        row["ado_id"] = _as_int(row["ado_id"], f"commits[{index}].ado_id", source)
    for key in ("sha", "sha_short", "message", "author", "date", "url"):
        if key in row:
            row[key] = _as_str(row.get(key))
    return row


def validate_report(payload: Any, source: Path | str = "報告 JSON") -> Report:
    if not isinstance(payload, dict):
        raise ValueError(f"{source} 必須是 JSON 物件")
    missing = sorted(REQUIRED_REPORT_KEYS - payload.keys())
    if missing:
        raise ValueError(f"{source} 缺少欄位：{', '.join(missing)}")
    payload["ado_id"] = _as_int(payload.get("ado_id"), "ado_id", source)
    # ado_ids 空陣列時嘗試從 ado_id 補回，相容前端只帶 ado_id 的情況
    raw_ids = payload.get("ado_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        payload["ado_ids"] = [payload["ado_id"]]
    else:
        payload["ado_ids"] = [_as_int(value, f"ado_ids[{index}]", source) for index, value in enumerate(raw_ids)]
    payload["ado_subject"] = _as_str(payload.get("ado_subject"))
    if not isinstance(payload["test_items"], list):
        raise ValueError(f"{source} 的 test_items 必須是陣列")
    if not isinstance(payload["test_steps"], list):
        raise ValueError(f"{source} 的 test_steps 必須是陣列")
    payload["test_items"] = [
        _validate_test_item(item, index, source) for index, item in enumerate(payload["test_items"])
    ]
    payload["test_steps"] = [
        _validate_test_step(step, index, source) for index, step in enumerate(payload["test_steps"])
    ]
    for key in OPTIONAL_STRING_KEYS:
        if key in payload:
            payload[key] = _as_str(payload.get(key))
    payload.pop("change_history", None)
    if "commits" in payload:
        if not isinstance(payload["commits"], list):
            raise ValueError(f"{source} 的 commits 必須是陣列")
        payload["commits"] = [
            _validate_commit(entry, index, source) for index, entry in enumerate(payload["commits"])
        ]
    return cast(Report, payload)


def locate_report(work_item_id: int) -> tuple[Path, Report] | None:
    """找到包含此 ADO ID 的報告檔（合併組可能存在最小 ID 的檔名）。"""
    if not JSON_DIR.exists():
        return None
    path = report_json_path(work_item_id)
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
                read_json(candidate),
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
            return candidate, payload
    return None


def find_report(work_item_id: int) -> Report | None:
    found = locate_report(work_item_id)
    return None if found is None else found[1]
