#!/usr/bin/env python3
"""列出 Azure DevOps 專案中所有 Work Item 編號。"""

from __future__ import annotations

import sys
from typing import Any

from utils.ado_client import api_url, auth_header, request_json
from utils.config_io import load_config
from utils.pipeline_io import log, log_stage, log_stage_done, write_pipeline_json

WIQL_PAGE_SIZE = 20000


def query_work_item_ids(config: dict[str, Any], authorization: str) -> list[int]:
    ids: list[int] = []
    last_id = 0

    while True:
        query = (
            "SELECT [System.Id] FROM WorkItems "
            "WHERE [System.TeamProject] = @project "
            "AND [System.WorkItemType] = 'Issue' "
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
        log(f"已取得 {len(ids)} 筆 …")
        if len(batch) < WIQL_PAGE_SIZE:
            break

    return ids


def run_list_ids(config: dict[str, Any] | None = None) -> list[int]:
    cfg = config or load_config()
    authorization = auth_header(cfg["pat"])
    log_stage(f"1/5 LIST  列出專案 Issue（{cfg.get('project')}）")
    ids = query_work_item_ids(cfg, authorization)
    log(f"共 {len(ids)} 筆")
    log_stage_done(f"LIST 完成，共 {len(ids)} 筆")
    return ids


def main() -> None:
    write_pipeline_json(run_list_ids())


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        sys.exit(1)
