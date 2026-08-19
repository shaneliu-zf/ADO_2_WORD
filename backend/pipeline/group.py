#!/usr/bin/env python3
"""檢查 Work Item JSON 的關聯，Related 直接合併成一組。"""

from __future__ import annotations

from backend.utils.pipeline_io import log, log_stage, log_stage_done, normalize_ids, read_pipeline_json, run_pipeline_main, write_pipeline_json
from backend.utils.work_item_parser import extract_related_ids, read_work_item


def related_group(primary_id: int) -> list[int]:
    """從 primary 出發，BFS 收集所有 Related Work Item（不管 Redmine）。"""
    group: list[int] = []
    pending = [primary_id]
    seen: set[int] = set()
    while pending:
        work_item_id = pending.pop(0)
        if work_item_id in seen:
            continue
        seen.add(work_item_id)
        try:
            item = read_work_item(work_item_id)
        except FileNotFoundError:
            continue
        group.append(work_item_id)
        for related_id in extract_related_ids(item):
            if related_id not in seen:
                pending.append(related_id)
    return group


def group_work_item_ids(work_item_ids: list[int]) -> list[list[int]]:
    """對一組 ID 去重後，回傳 Related 分組。"""
    groups: list[list[int]] = []
    processed: set[int] = set()
    for work_item_id in work_item_ids:
        if work_item_id in processed:
            continue
        group = related_group(work_item_id)
        processed.update(group)
        groups.append(group)
    return groups


def run_group(work_item_ids: list[int]) -> list[list[int]]:
    log_stage(f"3/5 GROUP  檢查關聯（{len(work_item_ids)} 筆）")
    groups = group_work_item_ids(work_item_ids)
    for group in groups:
        ids_text = ", ".join(str(value) for value in group)
        if len(group) > 1:
            log(f"合併：ADO {ids_text}")
        else:
            log(f"單筆：ADO {ids_text}")
    log(f"分成 {len(groups)} 組：{groups}")
    log_stage_done(f"GROUP 完成，共 {len(groups)} 組")
    return groups


def main() -> None:
    write_pipeline_json(run_group(normalize_ids(read_pipeline_json())))


if __name__ == "__main__":
    run_pipeline_main(main)
