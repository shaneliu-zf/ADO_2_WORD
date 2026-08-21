#!/usr/bin/env python3
"""listed / groups / ui_session 工作區檔案。"""

from __future__ import annotations

import re
import threading
from typing import Any

from backend.utils.json_io import read_json_or, write_json
from backend.utils.paths import GROUPS_PATH, LISTED_PATH, UI_SESSION_PATH
from backend.utils.report_schema import find_report
from backend.utils.work_item_parser import extract_redmine, read_work_item, stringify

PIPELINE_STEP_COUNT = 4
SCRIPT_INDEX = {
    "fetch": 1,
    "group": 2,
    "report_by_llm": 3,
    "word": 4,
}
_session_file_lock = threading.Lock()


def parse_id_list(raw: Any) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, list):
        chunks = [str(value) for value in raw]
    else:
        chunks = re.split(r"[,;\s]+", str(raw))
    ids: list[int] = []
    for chunk in chunks:
        text = chunk.strip().lstrip("#")
        if not text:
            continue
        match = re.search(r"(\d+)", text)
        if not match:
            continue
        work_item_id = int(match.group(1))
        if work_item_id not in ids:
            ids.append(work_item_id)
    return ids


def load_listed() -> list[dict[str, Any]]:
    payload = read_json_or(LISTED_PATH, [])
    rows = payload if isinstance(payload, list) else payload.get("items") or []
    result: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict) and row.get("id") is not None:
            result.append(row)
        elif isinstance(row, int):
            result.append({"id": row, "title": "", "work_item_type": "", "state": ""})
    return result


def save_listed(rows: list[dict[str, Any]]) -> None:
    write_json(LISTED_PATH, rows)


def remove_listed_ids(ids: set[int]) -> None:
    remaining = [row for row in load_listed() if int(row.get("id") or 0) not in ids]
    if remaining or LISTED_PATH.exists():
        save_listed(remaining)


def group_payload(ids: list[int]) -> dict[str, Any]:
    unique: list[int] = []
    for value in ids:
        work_item_id = int(value)
        if work_item_id not in unique:
            unique.append(work_item_id)
    primary = min(unique)
    redmine = ""
    report = find_report(primary)
    if report:
        redmine = stringify(report.get("redmine_id"))
    if not redmine:
        try:
            redmine = extract_redmine(read_work_item(primary))
        except FileNotFoundError:
            pass
    return {"ids": unique, "primary_id": primary, "redmine_id": redmine}


def save_groups(groups: list[list[int]]) -> None:
    payload = [group_payload(group) for group in groups if group]
    write_json(GROUPS_PATH, payload)


def merge_groups(new_groups: list[list[int]]) -> None:
    """用新分組覆蓋有交集的舊組，其餘舊組保留。"""
    touched = {work_item_id for group in new_groups for work_item_id in group}
    kept = [group for group in load_group_id_lists() if not touched.intersection(group)]
    save_groups([*kept, *[group for group in new_groups if group]])


def load_group_id_lists() -> list[list[int]]:
    saved = read_json_or(GROUPS_PATH, [])
    if not isinstance(saved, list):
        return []
    groups: list[list[int]] = []
    for row in saved:
        values = row.get("ids") if isinstance(row, dict) else row
        if not isinstance(values, list):
            continue
        ids: list[int] = []
        for value in values:
            try:
                work_item_id = int(value)
            except (TypeError, ValueError):
                continue
            if work_item_id not in ids:
                ids.append(work_item_id)
        if ids:
            groups.append(ids)
    return groups


def load_groups_records() -> list[dict[str, Any]]:
    saved = read_json_or(GROUPS_PATH, [])
    if not isinstance(saved, list):
        return []
    records: list[dict[str, Any]] = []
    for row in saved:
        if isinstance(row, dict) and row.get("ids"):
            records.append(row)
    return records


def remove_ids_from_groups(drop: set[int]) -> None:
    if not drop or not GROUPS_PATH.exists():
        return
    next_groups = [[work_item_id for work_item_id in ids if work_item_id not in drop] for ids in load_group_id_lists()]
    next_groups = [ids for ids in next_groups if ids]
    save_groups(next_groups)


def sync_groups_to_listed() -> None:
    keep = {int(row["id"]) for row in load_listed() if row.get("id") is not None}
    drop = {work_item_id for ids in load_group_id_lists() for work_item_id in ids if work_item_id not in keep}
    if drop:
        remove_ids_from_groups(drop)


def clear_groups(ids: set[int] | None = None) -> None:
    if ids is not None:
        if not ids:
            return
        drop: set[int] = set()
        for group in load_group_id_lists():
            if ids.intersection(group):
                drop.update(group)
        remove_ids_from_groups(drop)
        return
    if GROUPS_PATH.exists():
        save_groups([])


def grouped_ids() -> set[int]:
    ids: set[int] = set()
    for group in load_group_id_lists():
        ids.update(group)
    return ids


def default_ui_session() -> dict[str, Any]:
    return {
        "working_ids": [],
        "listed_ids": [],
        "selected_ids": [],
        "current_step": 1,
        "reached_step": 0,
        "pipeline_steps": PIPELINE_STEP_COUNT,
    }


def session_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ids": list(data.get("working_ids") or []),
        "listedIds": list(data.get("listed_ids") or []),
        "selectedIds": list(data.get("selected_ids") or []),
        "currentStep": int(data.get("current_step") or 1),
        "reachedStep": int(data.get("reached_step") or 0),
    }


def load_ui_session() -> dict[str, Any]:
    data = default_ui_session()
    payload = read_json_or(UI_SESSION_PATH, None)
    if not isinstance(payload, dict):
        return data
    data["working_ids"] = parse_id_list(payload.get("working_ids"))
    data["listed_ids"] = parse_id_list(payload.get("listed_ids"))
    data["selected_ids"] = parse_id_list(payload.get("selected_ids"))
    data["current_step"] = max(1, min(PIPELINE_STEP_COUNT, int(payload.get("current_step") or 1)))
    data["reached_step"] = max(0, min(PIPELINE_STEP_COUNT, int(payload.get("reached_step") or 0)))
    data["pipeline_steps"] = PIPELINE_STEP_COUNT
    return data


def save_ui_session(data: dict[str, Any]) -> dict[str, Any]:
    with _session_file_lock:
        write_json(UI_SESSION_PATH, data)
    return data


def working_ids() -> list[int]:
    return list(load_ui_session().get("working_ids") or [])


def ids_from_result(result: Any) -> list[int]:
    found: list[int] = []

    def walk(value: Any) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, int):
            found.append(value)
        elif isinstance(value, dict) and value.get("id") is not None:
            found.append(int(value["id"]))
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(result)
    return parse_id_list(found)


def update_session_after_run(
    script: str,
    result: Any,
) -> dict[str, Any]:
    """更新步驟進度。working_ids 只在載入 ID（list_ids / summaries）時變，跑 pipeline 不縮清單。"""
    data = load_ui_session()
    if script == "list_ids":
        extracted = ids_from_result(result)
        data["working_ids"] = extracted
        data["listed_ids"] = extracted

    if script == "main":
        data["reached_step"] = PIPELINE_STEP_COUNT
        data["current_step"] = PIPELINE_STEP_COUNT
    else:
        index = SCRIPT_INDEX.get(script, 0)
        if index:
            data["reached_step"] = max(int(data.get("reached_step") or 0), index)
            current = int(data.get("current_step") or 1)
            if current == index and index < PIPELINE_STEP_COUNT:
                data["current_step"] = index + 1
            elif index >= PIPELINE_STEP_COUNT:
                data["current_step"] = PIPELINE_STEP_COUNT
    return save_ui_session(data)


def list_groups_for(requested: list[int]) -> list[dict[str, Any]]:
    sync_groups_to_listed()
    seen: set[int] = set()
    groups: list[dict[str, Any]] = []

    def add(ids: list[int]) -> None:
        leftover = [work_item_id for work_item_id in ids if work_item_id not in seen]
        if not leftover:
            return
        payload = group_payload(leftover if leftover != ids else ids)
        groups.append(payload)
        seen.update(payload["ids"])

    for row in load_groups_records():
        add([int(value) for value in row["ids"]])

    keep = set(requested)
    groups = [
        {**group, "ids": [work_item_id for work_item_id in group["ids"] if work_item_id in keep]}
        for group in groups
    ]
    groups = [group for group in groups if group["ids"]]
    groups.sort(key=lambda group: int(group["primary_id"]))
    return groups
