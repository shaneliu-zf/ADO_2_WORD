#!/usr/bin/env python3
"""把 Work Item JSON 交給 IBM Bob，抽出測試報告 JSON。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.pipeline.group import group_work_item_ids
from backend.utils.bob_llm import BOB_MODEL, chat_json, load_bob_config
from backend.utils.paths import JSON_DIR, LLM_PROMPT_PATH
from backend.utils.pipeline_io import (
    log,
    log_stage,
    log_stage_done,
    normalize_groups,
    normalize_ids,
    read_pipeline_json,
    run_pipeline_main,
    write_pipeline_json,
)
from backend.utils.report_schema import ChangeEntry, Report, TestItem, TestStep
from backend.utils.work_item_parser import (
    TAG_RE,
    apply_image_map,
    extract_redmine,
    plain_text,
    read_work_item,
    stringify,
)


REVIEWER = ""
TEST_ENVIRONMENT = "QAS"

IMG_RE = re.compile(
    r"<img\b[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
SITE_RE = re.compile(r"(?i)\bSIT[\s\-]?([12])\b")
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
LONG_URL_RE = re.compile(r"https?://\S{50,}")
EMPTY_FIELD = {"", "（空）", "-", "n/a", "na"}
CUSTOM_CONTEXT_KEYS = ["Case", "Step", "Program", "Category", "Tag", "PrimaryCause", "Solution"]
COMMENT_KEEP_RE = re.compile(
    r"(?i)(?:step\s*\d|[復複]測|測試\s*ok|测试\s*ok|tested\s*pass|測試通過|测试通过|測試完成|\bpass\b|\bfail\b)",
)
NUMBERED_STEP_RE = re.compile(r"(?m)^\s*\d+\.\s+\S")
REPORT_WORKERS = 8


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    if not LLM_PROMPT_PATH.is_file():
        raise FileNotFoundError(f"找不到 LLM prompt：{LLM_PROMPT_PATH}")
    return LLM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def resolve_site(fields: dict[str, Any]) -> str:
    candidates = [
        plain_text(fields.get("System.AreaLevel2")),
        plain_text(fields.get("System.NodeName")),
        plain_text(fields.get("System.AreaPath")),
    ]
    for text in candidates:
        match = SITE_RE.search(text)
        if match:
            return "US-1" if match.group(1) == "1" else "US-2"
    return ""


def format_test_date(value: str) -> str:
    match = ISO_DATE_RE.match((value or "").strip())
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{year}/{int(month)}/{int(day)}"


def resolve_tester(item: dict[str, Any]) -> str:
    """變更歷史中，最後一次把狀態改成 Testing 的操作者。"""
    tester = ""
    for entry in item.get("history") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            if change.get("field") != "System.State":
                continue
            if str(change.get("to") or "").strip().casefold() != "testing":
                continue
            tester = plain_text(entry.get("by"))
    return tester


def resolve_test_date(item: dict[str, Any]) -> str:
    """變更歷史中，最後一次離開 Testing 的日期。9999 → 用 ChangedDate。"""
    date_raw = ""
    for entry in item.get("history") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            if change.get("field") != "System.State":
                continue
            if str(change.get("from") or "").strip().casefold() != "testing":
                continue
            date_raw = entry.get("date") or ""
    if date_raw.startswith("9999"):
        fields = item.get("fields") or {}
        date_raw = plain_text(fields.get("System.ChangedDate"))
    return format_test_date(date_raw)


def extract_meta(item: dict[str, Any]) -> dict[str, Any]:
    work_item_id = int(item["id"])
    fields = item.get("fields") or {}
    subject = plain_text(fields.get("System.Title")) or plain_text(item.get("title"))
    subject = re.sub(rf"^#{work_item_id}\s*", "", subject).strip()
    return {
        "ado_id": work_item_id,
        "redmine_id": extract_redmine(item),
        "ado_subject": subject,
        "test_environment": TEST_ENVIRONMENT,
        "site": resolve_site(fields),
        "version": "",
        "test_date": resolve_test_date(item),
        "tester": resolve_tester(item),
        "reviewer": REVIEWER,
        "state": plain_text(fields.get("System.State")) or plain_text(item.get("state")),
    }


def simplify_fragment(fragment: str) -> str:
    def repl_img(match: re.Match[str]) -> str:
        src = html.unescape(match.group(2)).strip()
        return f"\n[img:{src}]\n"

    def repl_md_img(match: re.Match[str]) -> str:
        src = html.unescape(match.group(2).split()[0].strip("<>")).strip()
        return f"\n[img:{src}]\n"

    text = IMG_RE.sub(repl_img, fragment or "")
    text = MD_IMG_RE.sub(repl_md_img, text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|pre|blockquote)>", "\n", text)
    text = re.sub(r"(?i)<(ul|ol)\b[^>]*>", "\n", text)
    text = re.sub(r"(?i)<li\b[^>]*>", "- ", text)
    text = re.sub(r"(?i)<h[1-6]\b[^>]*>", "", text)
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    text = LONG_URL_RE.sub("[url]", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def custom_context(fields: dict[str, Any]) -> str:
    lines = []
    for key in CUSTOM_CONTEXT_KEYS:
        value = plain_text(fields.get(key) or fields.get(f"Custom.{key}"))
        if value and value.lower() not in EMPTY_FIELD:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def useful_comments(item: dict[str, Any]) -> str:
    images = item.get("images") or {}
    blocks: list[str] = []
    for comment in item.get("comments") or []:
        if not isinstance(comment, dict):
            continue
        author = stringify(comment.get("created_by"))
        raw_body = apply_image_map(stringify(comment.get("text")), images)
        body = simplify_fragment(raw_body)
        if not body or body.lower().startswith("copied from"):
            continue
        if not (COMMENT_KEEP_RE.search(body) or NUMBERED_STEP_RE.search(body)):
            continue
        blocks.append(f"{author}:\n{body}" if author else body)
    return "\n\n".join(blocks)


def build_llm_text(item: dict[str, Any], meta: dict[str, Any]) -> str:
    fields = item.get("fields") or {}
    images = item.get("images") or {}
    parts = [f"標題: {meta.get('ado_subject') or ''}"]
    custom = custom_context(fields)
    if custom:
        parts.append(custom)
    description = simplify_fragment(
        apply_image_map(stringify(fields.get("System.Description")), images)
    )
    if description:
        parts.append("【描述】\n" + description)
    comments = useful_comments(item)
    if comments:
        parts.append("【留言】\n" + comments)
    return "\n\n".join(parts).strip() + "\n"


def build_group_llm_input(items: list[dict[str, Any]], metas: list[dict[str, Any]]) -> str:
    sections = []
    for item, meta in zip(items, metas):
        sections.append(f"===== ADO #{meta['ado_id']} =====\n{build_llm_text(item, meta)}")
    return "\n\n".join(sections)


def collect_image_srcs(item: dict[str, Any]) -> set[str]:
    return {str(path) for path in (item.get("images") or {}).values() if path}


def call_test_extract(config: dict[str, Any], user_content: str) -> dict[str, Any]:
    return chat_json(
        [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": user_content},
        ],
        config=config,
    )


def as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in (as_str(v) for v in value) if item]
    text = as_str(value)
    if not text:
        return []
    return [part.strip(" •-") for part in re.split(r"[\n;]+", text) if part.strip(" •-")]


def normalize_test_items(raw_items: Any, state: str) -> list[TestItem]:
    items: list[TestItem] = []
    result = state.strip()
    for index, item in enumerate(raw_items or [], start=1):
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "no": int(item.get("no") or index),
                "item_name": as_str(item.get("item_name") or item.get("測試項目")),
                "test_data": as_str_list(item.get("test_data") or item.get("測試資料")),
                "expected_result": as_str(item.get("expected_result") or item.get("預期結果")),
                "test_result": result,
            }
        )
    return items


def normalize_test_steps(raw_steps: Any, allowed_images: set[str]) -> list[TestStep]:
    steps: list[TestStep] = []
    for index, step in enumerate(raw_steps or [], start=1):
        if not isinstance(step, dict):
            continue
        images = []
        for src in as_str_list(step.get("images")):
            if src in allowed_images:
                images.append(src)
        steps.append(
            {
                "no": int(step.get("no") or index),
                "description": as_str(step.get("description") or step.get("步驟")),
                "images": images,
            }
        )
    return steps


HISTORY_FIELD_LABELS: dict[str, str] = {
    "System.State": "狀態",
    "System.AssignedTo": "指派",
    "System.Reason": "原因",
    "relation": "關聯",
}

HISTORY_KEEP_FIELDS = {
    "System.State",
    "System.AssignedTo",
    "System.Reason",
    "relation",
}


def extract_change_history(items: list[dict[str, Any]]) -> list[ChangeEntry]:
    """從 ADO JSON history 抽取狀態、指派、關聯等重要變動，依時間排序。"""
    entries: list[ChangeEntry] = []
    for item in items:
        ado_id = int(item.get("id") or 0)
        prefix = f"ADO#{ado_id} " if len(items) > 1 else ""
        for entry in item.get("history") or []:
            if not isinstance(entry, dict):
                continue
            date = as_str(entry.get("date"))
            by = as_str(entry.get("by"))
            for change in entry.get("changes") or []:
                if not isinstance(change, dict):
                    continue
                field = as_str(change.get("field"))
                if field not in HISTORY_KEEP_FIELDS:
                    continue
                old_val = as_str(change.get("from"))
                new_val = as_str(change.get("to"))
                if field == "relation":
                    combined = old_val + new_val
                    if "#" not in combined:
                        continue
                label = prefix + HISTORY_FIELD_LABELS.get(field, field)
                entries.append({
                    "date": date,
                    "by": by,
                    "field": label,
                    "old": old_val,
                    "new": new_val,
                })
    entries.sort(key=lambda e: e["date"])
    return entries


def unique_join(values: list[Any]) -> str:
    unique = []
    for value in values:
        text = as_str(value)
        if text and text not in unique:
            unique.append(text)
    return " / ".join(unique)


def build_report(
    items: list[dict[str, Any]],
    metas: list[dict[str, Any]],
    llm_data: dict[str, Any],
) -> Report:
    primary = metas[0]
    allowed_images: set[str] = set()
    for item in items:
        allowed_images.update(collect_image_srcs(item))
    state = unique_join([meta.get("state") for meta in metas])
    report: Report = {
        "ado_id": primary["ado_id"],
        "ado_ids": [meta["ado_id"] for meta in metas],
        "redmine_id": unique_join([meta.get("redmine_id") for meta in metas]),
        "ado_subject": "\n".join(
            f"#{meta['ado_id']} {meta['ado_subject']}" for meta in metas
        ),
        "test_environment": primary["test_environment"],
        "site": unique_join([meta["site"] for meta in metas]),
        "version": primary["version"],
        "test_date": "、".join(as_str(meta["test_date"]) for meta in metas if as_str(meta["test_date"])),
        "tester": unique_join([meta["tester"] for meta in metas]),
        "reviewer": primary["reviewer"],
        "test_items": normalize_test_items(llm_data.get("test_items"), state),
        "test_steps": normalize_test_steps(llm_data.get("test_steps"), allowed_images),
        "change_history": extract_change_history(items),
    }
    return report


def process_group(work_item_ids: list[int], config: dict[str, Any]) -> Path:
    items = [read_work_item(work_item_id) for work_item_id in work_item_ids]
    metas = [extract_meta(item) for item in items]
    llm_data = call_test_extract(config, build_group_llm_input(items, metas))
    report = build_report(items, metas, llm_data)

    primary_id = min(work_item_ids)
    out_path = JSON_DIR / f"work_item_{primary_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for work_item_id in work_item_ids:
        for stale_path in (
            JSON_DIR / f"work_item_{work_item_id}.json",
            JSON_DIR / f"work_item_{work_item_id}_test.json",
        ):
            if stale_path != out_path and stale_path.exists():
                stale_path.unlink()
    return out_path


def run_report_by_llm(groups: list[list[int]], config: dict[str, Any] | None = None) -> list[list[int]]:
    cfg = load_bob_config(config)
    log_stage("4/5 REPORT  Bob 產出報告 JSON")
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Bob model：{BOB_MODEL}")
    log(f"共 {len(groups)} 組，開始處理 …")
    worker_count = min(REPORT_WORKERS, max(1, len(groups)))
    log(f"使用 {worker_count} 個 worker 平行產生 JSON …")
    for group in groups:
        group_label = ", ".join(str(value) for value in group)
        log(f"排入分析 Work Item {group_label} …")
        if len(group) > 1:
            log(f"  合併處理：{group_label}")
    processed_paths: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(process_group, group, cfg): index
            for index, group in enumerate(groups)
        }
        for future in as_completed(future_map):
            index = future_map[future]
            group = groups[index]
            path = future.result()
            processed_paths[index] = path
            group_label = ", ".join(str(value) for value in group)
            log(f"完成分析 Work Item {group_label}")
            log(f"  已寫入：{path}")
    processed_groups = [groups[index] for index in range(len(groups)) if index in processed_paths]
    log_stage_done(f"REPORT 完成，共 {len(processed_groups)} 組")
    return processed_groups


def main() -> None:
    payload = read_pipeline_json()
    if isinstance(payload, list) and any(isinstance(item, list) for item in payload):
        groups = normalize_groups(payload)
    else:
        log("stdin 是扁平 ID，改以 Related 分組 …")
        groups = group_work_item_ids(normalize_ids(payload))
    write_pipeline_json(run_report_by_llm(groups))


if __name__ == "__main__":
    run_pipeline_main(main)
