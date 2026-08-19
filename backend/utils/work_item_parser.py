#!/usr/bin/env python3
"""讀取並解析 fetch 產出的 ADO JSON（欄位、Redmine、關聯）。"""

from __future__ import annotations

import html
import json
import re
from typing import Any

from backend.utils.paths import ADO_DIR


TAG_RE = re.compile(r"<[^>]+>")
# 標題結尾常見 (63852.64178) 或 (63759)
TITLE_REDMINE_RE = re.compile(r"\(#?(\d{4,}(?:\.\d+)*)\)\s*$")
# 留言常見 BUG #63474 / redmine 63474
COMMENT_REDMINE_RE = re.compile(r"(?i)(?:redmine\s*#?\s*|BUG\s*#\s*)(\d{4,}(?:\.\d+)*)")
RELATED_ID_RE = re.compile(r"(?i)/workItems/(\d+)")


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(
            value.get("displayName")
            or value.get("uniqueName")
            or json.dumps(value, ensure_ascii=False)
        )
    if isinstance(value, list):
        return "; ".join(item for item in (stringify(v) for v in value) if item)
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value)


def inner_text(fragment: str) -> str:
    text = html.unescape(TAG_RE.sub(" ", fragment or ""))
    return re.sub(r"\s+", " ", text).strip()


def plain_text(value: Any) -> str:
    return inner_text(stringify(value))


def read_work_item(work_item_id: int) -> dict[str, Any]:
    path = ADO_DIR / f"work_item_{work_item_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"找不到 ADO JSON：{path}。請先執行 python3 -m backend.pipeline.fetch"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} 必須是 JSON 物件")
    return payload


def apply_image_map(text: str, images: dict[str, str] | None) -> str:
    """把描述／留言裡的遠端圖片網址換成本機相對路徑。"""
    if not text:
        return ""
    if not images:
        return text
    out = text
    for url, local in images.items():
        if not url or not local:
            continue
        if url in out:
            out = out.replace(url, local)
        escaped = html.escape(url, quote=True)
        if escaped != url and escaped in out:
            out = out.replace(escaped, html.escape(local, quote=True))
    return out


def extract_redmine(item: dict[str, Any]) -> str:
    """優先從標題結尾取 Redmine 編號，沒有再從留言找。"""
    fields = item.get("fields") or {}
    title = plain_text(fields.get("System.Title")) or plain_text(item.get("title"))
    match = TITLE_REDMINE_RE.search(title)
    if match:
        return match.group(1)
    for comment in item.get("comments") or []:
        if not isinstance(comment, dict):
            continue
        text = plain_text(comment.get("text"))
        match = COMMENT_REDMINE_RE.search(text)
        if match:
            return match.group(1)
    return ""


def extract_related_ids(item: dict[str, Any]) -> list[int]:
    found: set[int] = set()
    self_id = item.get("id")
    for rel in item.get("relations") or []:
        if not isinstance(rel, dict):
            continue
        match = RELATED_ID_RE.search(str(rel.get("url") or ""))
        if match:
            related_id = int(match.group(1))
            if related_id != self_id:
                found.add(related_id)
    return sorted(found)
