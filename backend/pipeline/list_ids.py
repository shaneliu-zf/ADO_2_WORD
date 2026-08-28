#!/usr/bin/env python3
"""列出 Azure DevOps 專案中所有 Work Item（含標題、類型、狀態）。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from backend.utils.ado_client import (
    WORK_ITEMS_BATCH_SIZE,
    api_url,
    auth_header,
    fetch_work_items_batch,
    request_json,
)
from backend.utils.config_io import load_config
from backend.utils.pipeline_io import log, log_stage, log_stage_done, run_pipeline_main, write_pipeline_json
from backend.utils.work_item_parser import stringify

WIQL_PAGE_SIZE = 20000
LIST_FIELDS = ["System.Id", "System.Title", "System.WorkItemType", "System.State"]
LIST_BATCH_WORKERS = 8


def query_work_item_ids(config: dict[str, Any], authorization: str) -> list[int]:
    from backend.utils.config_io import is_demo_mode

    if is_demo_mode(config):
        from backend.demo import all_ids

        ids = all_ids()
        log(f"展示模式：共 {len(ids)} 筆虛構 ID")
        return ids
    ids: list[int] = []
    last_id = 0

    while True:
        query = (
            "SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State] "
            "FROM WorkItems "
            "WHERE [System.TeamProject] = @project "
            f"AND [System.Id] > {last_id} "
            "ORDER BY [System.Id] ASC"
        )
        url = api_url(config, "wit/wiql", query={"api-version": "7.1"})
        payload = request_json(url, authorization, {"query": query})
        batch = [int(item["id"]) for item in (payload.get("workItems") or [])]
        if not batch:
            break
        ids.extend(batch)
        last_id = batch[-1]
        log(f"已取得 {len(ids)} 筆 ID …")
        if len(batch) < WIQL_PAGE_SIZE:
            break

    return ids


def summarize_batch(
    config: dict[str, Any],
    authorization: str,
    work_item_ids: list[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in fetch_work_items_batch(config, authorization, work_item_ids, LIST_FIELDS):
        fields = item.get("fields") or {}
        work_item_id = int(item.get("id") or fields.get("System.Id") or 0)
        if not work_item_id:
            continue
        rows.append(
            {
                "id": work_item_id,
                "title": stringify(fields.get("System.Title")),
                "work_item_type": stringify(fields.get("System.WorkItemType")),
                "state": stringify(fields.get("System.State")),
            }
        )
    return rows


def load_work_item_summaries(
    config: dict[str, Any],
    authorization: str,
    work_item_ids: list[int],
) -> list[dict[str, Any]]:
    if not work_item_ids:
        return []
    chunks = [
        work_item_ids[index : index + WORK_ITEMS_BATCH_SIZE]
        for index in range(0, len(work_item_ids), WORK_ITEMS_BATCH_SIZE)
    ]
    by_id: dict[int, dict[str, Any]] = {}
    workers = min(LIST_BATCH_WORKERS, max(1, len(chunks)))
    log(f"讀取標題／類型／狀態（{len(chunks)} 批）…")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(summarize_batch, config, authorization, chunk): chunk
            for chunk in chunks
        }
        for future in as_completed(future_map):
            for row in future.result():
                by_id[int(row["id"])] = row
    missing = [work_item_id for work_item_id in work_item_ids if work_item_id not in by_id]
    if missing:
        log(f"有 {len(missing)} 筆沒讀到欄位，仍保留 ID")
        for work_item_id in missing:
            by_id[work_item_id] = {
                "id": work_item_id,
                "title": "",
                "work_item_type": "",
                "state": "",
            }
    return [by_id[work_item_id] for work_item_id in work_item_ids]


def run_list_ids(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config()
    authorization = auth_header(cfg["pat"])
    log_stage(f"1/5 LIST  列出專案 Work Item（{cfg.get('project')}）")
    ids = query_work_item_ids(cfg, authorization)
    rows = load_work_item_summaries(cfg, authorization, ids)
    log(f"共 {len(rows)} 筆")
    log_stage_done(f"LIST 完成，共 {len(rows)} 筆")
    return rows


def main() -> None:
    write_pipeline_json(run_list_ids())


if __name__ == "__main__":
    run_pipeline_main(main)
