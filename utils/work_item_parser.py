#!/usr/bin/env python3
"""讀取並解析 Work Item HTML（欄位、區塊、Redmine、關聯）。"""

from __future__ import annotations

import html
import re

from utils.paths import HTML_DIR


TAG_RE = re.compile(r"<[^>]+>")
TH_RE = re.compile(r"<th>(.*?)</th>\s*<td>(.*?)</td>", re.IGNORECASE | re.DOTALL)
# 標題結尾常見 (63852.64178) 或 (63759)
TITLE_REDMINE_RE = re.compile(r"\(#?(\d{4,}(?:\.\d+)*)\)\s*$")
# 留言常見 BUG #63474 / redmine 63474
COMMENT_REDMINE_RE = re.compile(r"(?i)(?:redmine\s*#?\s*|BUG\s*#\s*)(\d{4,}(?:\.\d+)*)")
RELATED_ID_RE = re.compile(r"(?i)/workItems/(\d+)")


def inner_text(fragment: str) -> str:
    text = html.unescape(TAG_RE.sub(" ", fragment or ""))
    return re.sub(r"\s+", " ", text).strip()


def extract_section(html_text: str, title: str) -> str:
    pattern = rf"<h2>\s*{re.escape(title)}\s*</h2>(.*?)(?=<h2\b|$)"
    match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def field_map(html_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in TH_RE.finditer(html_text):
        key = inner_text(match.group(1))
        if key:
            fields[key] = inner_text(match.group(2))
    return fields


def heading_title(html_text: str) -> str:
    match = re.search(r"<h1>(.*?)</h1>", html_text, re.IGNORECASE | re.DOTALL)
    return inner_text(match.group(1)) if match else ""


def read_work_item_html(work_item_id: int) -> str:
    html_path = HTML_DIR / f"work_item_{work_item_id}.html"
    if not html_path.exists():
        raise FileNotFoundError(f"找不到 HTML：{html_path}。請先執行 python3 fetch.py")
    return html_path.read_text(encoding="utf-8")


def extract_redmine(html_text: str) -> str:
    """優先從標題結尾取 Redmine 編號，沒有再從留言找。"""
    title = field_map(html_text).get("System.Title", "")
    match = TITLE_REDMINE_RE.search(title)
    if match:
        return match.group(1)
    comments = extract_section(html_text, "留言")
    match = COMMENT_REDMINE_RE.search(comments)
    return match.group(1) if match else ""


def extract_related_ids(html_text: str) -> list[int]:
    relations = extract_section(html_text, "關聯")
    return sorted({int(value) for value in RELATED_ID_RE.findall(relations)})
