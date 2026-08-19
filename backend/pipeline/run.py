#!/usr/bin/env python3
"""用 JSON／Python 物件直接呼叫 pipeline 步驟。"""

from __future__ import annotations

import json
from typing import Any

from backend.pipeline.fetch import run_fetch
from backend.pipeline.group import group_work_item_ids, run_group
from backend.pipeline.list_ids import run_list_ids
from backend.pipeline.report_by_llm import run_report_by_llm
from backend.pipeline.word import run_word
from backend.utils.pipeline_io import log, normalize_groups, normalize_ids


STEPS = ("list_ids", "fetch", "group", "report_by_llm", "word")


def as_json(payload: Any) -> Any:
    if payload is None:
        return None
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON 格式錯誤：第 {exc.lineno} 行第 {exc.colno} 欄"
            ) from exc
    return payload


def unpack(payload: Any) -> Any:
    """接受 [902]、[[902,939]]，或 {"ids": [...]}／{"groups": [...]}。"""
    data = as_json(payload)
    if isinstance(data, dict):
        if data.get("groups") is not None:
            return data["groups"]
        if data.get("ids") is not None:
            return data["ids"]
        raise ValueError('JSON 物件請包含 "ids" 或 "groups"')
    return data


def _require_ids(payload: Any) -> list[int]:
    data = unpack(payload)
    if data is None:
        raise ValueError("請傳入 ids，例如 [902, 939]")
    return normalize_ids(data)


def _require_groups(payload: Any) -> list[list[int]]:
    data = unpack(payload)
    if data is None:
        raise ValueError("請傳入 ID 或分組，例如 [902, 939] 或 [[902, 939]]")
    if isinstance(data, list) and any(isinstance(item, list) for item in data):
        return normalize_groups(data)
    log("輸入是扁平 ID，改以 Related 分組 …")
    return group_work_item_ids(normalize_ids(data))


def run_step(name: str, payload: Any = None, *, no_images: bool = False) -> Any:
    """只跑單一步驟。"""
    step = str(name or "").strip()
    if step not in STEPS:
        raise ValueError(f"未知步驟：{name}。可用：{', '.join(STEPS)}")
    if step == "list_ids":
        return run_list_ids()
    if step == "fetch":
        return run_fetch(_require_ids(payload), no_images=no_images)
    if step == "group":
        return run_group(_require_ids(payload))
    if step == "report_by_llm":
        return run_report_by_llm(_require_groups(payload))
    return run_word(_require_ids(payload))


def run_from(start: str = "list_ids", payload: Any = None, *, no_images: bool = False) -> Any:
    """從指定步驟跑到 word。payload 為該步的輸入 JSON。"""
    step = str(start or "list_ids").strip()
    if step not in STEPS:
        raise ValueError(f"未知步驟：{start}。可用：{', '.join(STEPS)}")
    data: Any = payload
    started = False
    for name in STEPS:
        if not started:
            if name != step:
                continue
            started = True
        data = run_step(name, data, no_images=no_images)
    return data
