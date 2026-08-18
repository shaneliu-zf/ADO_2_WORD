#!/usr/bin/env python3
"""一鍵跑完整 ADO → Word pipeline（全專案）。"""

from __future__ import annotations

import argparse
import sys

from fetch import run_fetch
from group import run_group
from list_ids import run_list_ids
from report_by_llm import run_report_by_llm
from utils.pipeline_io import log_stage, write_pipeline_json
from word import run_word


def flatten_groups(groups: list[list[int]]) -> list[int]:
    ids: list[int] = []
    for group in groups:
        for work_item_id in group:
            if work_item_id not in ids:
                ids.append(work_item_id)
    return ids


def run_pipeline(*, no_images: bool = False) -> list[str]:
    ids = run_list_ids()
    log_stage(f"PIPELINE  全專案（{len(ids)} 筆）")
    ids = run_fetch(ids, no_images=no_images)
    groups = run_group(ids)
    groups = run_report_by_llm(groups)
    return run_word(flatten_groups(groups))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WIQL 列全專案 Issue，跑 list → fetch → group → report_by_llm → word",
        epilog="指定 ID 或從中間重跑請用分步 pipe，見 README。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="fetch 時不下載圖片",
    )
    args = parser.parse_args()
    write_pipeline_json(run_pipeline(no_images=args.no_images))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        sys.exit(1)
