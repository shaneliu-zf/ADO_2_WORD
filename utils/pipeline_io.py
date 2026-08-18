#!/usr/bin/env python3
"""stdin/stdout 的 JSON pipeline 共用函式。"""

from __future__ import annotations

import json
import sys
from typing import Any


def read_pipeline_json() -> Any:
    text = sys.stdin.read().strip()
    if not text:
        raise ValueError(
            'stdin 沒有資料。請傳入 JSON，例如：echo \'[902, 939]\' | python3 fetch.py'
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"stdin JSON 格式錯誤：第 {exc.lineno} 行第 {exc.colno} 欄"
        ) from exc


def normalize_ids(payload: Any) -> list[int]:
    """接受單一 ID、ID 陣列或分組陣列，回傳去重後的扁平 ID。"""
    if isinstance(payload, int):
        values = [payload]
    elif isinstance(payload, list):
        values = []
        for item in payload:
            if isinstance(item, list):
                values.extend(item)
            else:
                values.append(item)
    else:
        raise ValueError("pipeline 輸入必須是 ID 或 ID 陣列")

    ids: list[int] = []
    for value in values:
        if isinstance(value, bool):
            raise ValueError("Work Item ID 必須是整數")
        try:
            work_item_id = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"無效的 Work Item ID：{value!r}") from exc
        if work_item_id not in ids:
            ids.append(work_item_id)
    if not ids:
        raise ValueError("pipeline 輸入沒有 Work Item ID")
    return ids


def normalize_groups(payload: Any) -> list[list[int]]:
    """接受 ID 或 ID／分組陣列；扁平陣列會轉成單筆分組。"""
    if isinstance(payload, int):
        return [normalize_ids(payload)]
    if not isinstance(payload, list) or not payload:
        raise ValueError("pipeline 輸入必須是 ID 陣列或分組陣列")
    if all(not isinstance(item, list) for item in payload):
        return [[work_item_id] for work_item_id in normalize_ids(payload)]

    groups: list[list[int]] = []
    for item in payload:
        group = normalize_ids(item if isinstance(item, list) else [item])
        if group:
            groups.append(group)
    return groups


def write_pipeline_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def log(message: str = "") -> None:
    print(message, file=sys.stderr)


def log_stage(title: str) -> None:
    bar = "=" * 60
    log("")
    log(bar)
    log(f"  {title}")
    log(bar)


def log_stage_done(summary: str = "完成") -> None:
    log("-" * 60)
    log(f"  {summary}")
    log("-" * 60)
