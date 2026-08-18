#!/usr/bin/env python3
"""把 Work Item HTML 交給 IBM Bob，抽出測試報告 JSON。"""

from __future__ import annotations

import html
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from group import group_work_item_ids
from utils.bob_llm import BOB_MODEL, chat_json, load_bob_config
from utils.paths import JSON_DIR, LLM_PROMPT_PATH
from utils.pipeline_io import (
    log,
    log_stage,
    log_stage_done,
    normalize_groups,
    normalize_ids,
    read_pipeline_json,
    write_pipeline_json,
)
from utils.report_schema import Report, TestItem, TestStep
from utils.work_item_parser import (
    TAG_RE,
    extract_redmine,
    extract_section,
    field_map,
    heading_title,
    inner_text,
    read_work_item_html,
)


REVIEWER = ""
TEST_ENVIRONMENT = "QAS"

IMG_RE = re.compile(
    r"<img\b[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
SITE_RE = re.compile(r"(?i)\bSIT[\s\-]?([12])\b")
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
COMMENT_RE = re.compile(
    r'<article\b[^>]*class="comment"[^>]*>\s*<header>(.*?)</header>(.*?)</article>',
    re.IGNORECASE | re.DOTALL,
)
LONG_URL_RE = re.compile(r"https?://\S{50,}")
EMPTY_FIELD = {"", "（空）", "-", "n/a", "na"}
CUSTOM_CONTEXT_KEYS = ["Case", "Step", "Program", "Category", "Tag", "PrimaryCause", "Solution"]
COMMENT_KEEP_RE = re.compile(
    r"(?i)(?:step\s*\d|[復複]測|測試\s*ok|测试\s*ok|tested\s*pass|測試通過|测试通过|測試完成|\bpass\b|\bfail\b)",
)
NUMBERED_STEP_RE = re.compile(r"(?m)^\s*\d+\.\s+\S")


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    if not LLM_PROMPT_PATH.is_file():
        raise FileNotFoundError(f"找不到 LLM prompt：{LLM_PROMPT_PATH}")
    return LLM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def resolve_site(fields: dict[str, str]) -> str:
    candidates = [
        fields.get("System.AreaLevel2", ""),
        fields.get("System.NodeName", ""),
        fields.get("System.AreaPath", ""),
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


def resolve_tester(fields: dict[str, str]) -> str:
    return fields.get("System.CreatedBy") or ""


def resolve_test_date(fields: dict[str, str]) -> str:
    return format_test_date(fields.get("System.CreatedDate", ""))


def extract_meta(work_item_id: int, html_text: str) -> dict[str, Any]:
    fields = field_map(html_text)
    subject = fields.get("System.Title") or heading_title(html_text)
    subject = re.sub(rf"^#{work_item_id}\s*", "", subject).strip()
    return {
        "ado_id": work_item_id,
        "redmine_id": extract_redmine(html_text),
        "ado_subject": subject,
        "test_environment": TEST_ENVIRONMENT,
        "site": resolve_site(fields),
        "version": "",
        "test_date": resolve_test_date(fields),
        "tester": resolve_tester(fields),
        "reviewer": REVIEWER,
        "state": fields.get("System.State", ""),
    }


def simplify_fragment(fragment: str) -> str:
    def repl_img(match: re.Match[str]) -> str:
        src = html.unescape(match.group(2)).strip()
        return f"\n[img:{src}]\n"

    text = IMG_RE.sub(repl_img, fragment or "")
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


def custom_context(fields: dict[str, str]) -> str:
    lines = []
    for key in CUSTOM_CONTEXT_KEYS:
        value = (fields.get(key) or "").strip()
        if value and value.lower() not in EMPTY_FIELD:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def useful_comments(section: str) -> str:
    blocks: list[str] = []
    for match in COMMENT_RE.finditer(section or ""):
        author = inner_text(match.group(1)).split("·")[0].strip()
        raw_body = match.group(2)
        body = simplify_fragment(raw_body)
        if not body or body.lower().startswith("copied from"):
            continue
        if not (COMMENT_KEEP_RE.search(body) or NUMBERED_STEP_RE.search(body)):
            continue
        blocks.append(f"{author}:\n{body}" if author else body)
    return "\n\n".join(blocks)


def build_llm_html(html_text: str, meta: dict[str, Any]) -> str:
    fields = field_map(html_text)
    parts = [f"標題: {meta.get('ado_subject') or ''}"]
    custom = custom_context(fields)
    if custom:
        parts.append(custom)
    description = simplify_fragment(extract_section(html_text, "描述"))
    if description:
        parts.append("【描述】\n" + description)
    comments = useful_comments(extract_section(html_text, "留言"))
    if comments:
        parts.append("【留言】\n" + comments)
    return "\n\n".join(parts).strip() + "\n"


def build_group_llm_input(html_texts: list[str], metas: list[dict[str, Any]]) -> str:
    sections = []
    for html_text, meta in zip(html_texts, metas):
        sections.append(f"===== ADO #{meta['ado_id']} =====\n{build_llm_html(html_text, meta)}")
    return "\n\n".join(sections)


def collect_image_srcs(html_text: str) -> set[str]:
    return {html.unescape(match.group(2)).strip() for match in IMG_RE.finditer(html_text)}


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


def unique_join(values: list[Any]) -> str:
    unique = []
    for value in values:
        text = as_str(value)
        if text and text not in unique:
            unique.append(text)
    return " / ".join(unique)


def build_report(
    html_texts: list[str],
    metas: list[dict[str, Any]],
    llm_data: dict[str, Any],
) -> Report:
    primary = metas[0]
    allowed_images: set[str] = set()
    for html_text in html_texts:
        allowed_images.update(collect_image_srcs(html_text))
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
        "test_date": unique_join([meta["test_date"] for meta in metas]),
        "tester": unique_join([meta["tester"] for meta in metas]),
        "reviewer": primary["reviewer"],
        "test_items": normalize_test_items(llm_data.get("test_items"), state),
        "test_steps": normalize_test_steps(llm_data.get("test_steps"), allowed_images),
    }
    return report


def process_group(work_item_ids: list[int], config: dict[str, Any]) -> Path:
    html_texts = [read_work_item_html(work_item_id) for work_item_id in work_item_ids]
    metas = [
        extract_meta(work_item_id, html_text)
        for work_item_id, html_text in zip(work_item_ids, html_texts)
    ]
    llm_data = call_test_extract(config, build_group_llm_input(html_texts, metas))
    report = build_report(html_texts, metas, llm_data)

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
    processed_groups: list[list[int]] = []
    for group in groups:
        group_label = ", ".join(str(value) for value in group)
        log(f"正在分析 Work Item {group_label} …")
        if len(group) > 1:
            log(f"  合併處理：{group_label}")
        path = process_group(group, cfg)
        processed_groups.append(group)
        log(f"  已寫入：{path}")
    log_stage_done(f"REPORT 完成，共 {len(processed_groups)} 組")
    return processed_groups


def main() -> None:
    payload = read_pipeline_json()
    if isinstance(payload, list) and any(isinstance(item, list) for item in payload):
        groups = normalize_groups(payload)
    else:
        log("stdin 是扁平 ID，改以 Related＋同 Redmine 分組 …")
        groups = group_work_item_ids(normalize_ids(payload))
    write_pipeline_json(run_report_by_llm(groups))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        sys.exit(1)
