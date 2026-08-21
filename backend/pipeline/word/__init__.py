#!/usr/bin/env python3
"""把測試報告 JSON 填進參考 Word 範本的 ADO 區塊。"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from docx import Document

from backend.pipeline.word.blocks import (
    append_block,
    clear_ado_blocks,
    extract_block_prototype,
    fill_block,
    sort_report_ids,
)
from backend.pipeline.word.oxml import apply_global_yahei_font
from backend.pipeline.word.toc import ensure_heading_number_space, refresh_toc
from backend.utils.paths import DOCX_DIR, TEMPLATE_PATH
from backend.utils.pipeline_io import log, log_stage, log_stage_done, normalize_ids, read_pipeline_json, run_pipeline_main, write_pipeline_json
from backend.utils.report_schema import find_report

__all__ = ["run_word", "collect_reports", "fill_document", "output_docx_name", "resolve_output_docx"]

_REPORT_DOCX_RE = re.compile(r"^report_\d{8}_\d{6}\.docx$")


def load_report(work_item_id: int) -> dict[str, Any]:
    report = find_report(work_item_id)
    if report is None:
        raise FileNotFoundError(
            f"找不到包含 ADO #{work_item_id} 的 JSON。請先執行 python3 -m backend.pipeline.report_by_llm"
        )
    return report


def fill_document(doc: Document, reports: list[dict[str, Any]]) -> None:
    ensure_heading_number_space(doc)
    body = doc.element.body
    proto = extract_block_prototype(body)
    clear_ado_blocks(body)
    for report in reports:
        block = append_block(body, proto)
        fill_block(doc, block, report)
    apply_global_yahei_font(doc)
    refresh_toc(doc)


def output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DOCX_DIR / f"report_{stamp}.docx"


def output_docx_name(result: Any) -> str | None:
    """從 word／全流程回傳值取出要下載的檔名。"""
    if not isinstance(result, list):
        return None
    names: list[str] = []
    for item in result:
        name = Path(str(item)).name
        if _REPORT_DOCX_RE.fullmatch(name):
            names.append(name)
    return names[-1] if names else None


def resolve_output_docx(filename: str | None = None) -> Path:
    if not DOCX_DIR.exists():
        raise FileNotFoundError("尚未產出 Word。")
    if filename not in (None, ""):
        name = Path(str(filename)).name
        if not _REPORT_DOCX_RE.fullmatch(name):
            raise ValueError("檔名不正確")
        path = DOCX_DIR / name
        if not path.is_file():
            raise FileNotFoundError("找不到該 Word 檔。")
        return path
    docx_files = sorted(DOCX_DIR.glob("report_*.docx"), key=lambda path: path.stat().st_mtime)
    if not docx_files:
        raise FileNotFoundError("尚未產出 Word。")
    return docx_files[-1]


def collect_reports(work_item_ids: list[int]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    seen_groups: set[tuple[int, ...]] = set()
    for work_item_id in work_item_ids:
        report = sort_report_ids(load_report(work_item_id))
        group = tuple(report.get("ado_ids") or [report.get("ado_id")])
        if group in seen_groups:
            continue
        seen_groups.add(group)
        reports.append(report)
    reports.sort(key=lambda report: (report.get("ado_ids") or [0])[0])
    return reports


def run_word(work_item_ids: list[int]) -> list[str]:
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    log_stage(f"5/5 WORD  產出 Word（{len(work_item_ids)} 筆）")
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"找不到範本：{TEMPLATE_PATH}")

    reports = collect_reports(work_item_ids)
    if not reports:
        raise ValueError("沒有可產出的報告 JSON")
    for report in reports:
        label = ", ".join(str(value) for value in report["ado_ids"])
        log(f"  區塊：ADO {label}")

    path = output_path()
    shutil.copy2(TEMPLATE_PATH, path)
    doc = Document(str(path))
    fill_document(doc, reports)
    doc.save(str(path))
    log(f"已寫入：{path}")
    log_stage_done(f"WORD 完成，共 1 份、{len(reports)} 個 ADO 區塊")
    return [str(path)]


def main() -> None:
    write_pipeline_json(run_word(normalize_ids(read_pipeline_json())))
