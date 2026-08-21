#!/usr/bin/env python3
"""ADO 原文 HTML 預覽。"""

from __future__ import annotations

import html
import re
from typing import Any

from backend.utils.work_item_parser import (
    CUSTOM_KEYS,
    HTML_KEYS,
    META_KEYS,
    extract_commits,
    looks_like_html,
    looks_like_markdown,
    rewrite_preview_media,
    stringify,
)


def _cell(value: Any, images: dict[str, str] | None = None, as_html: bool = False) -> str:
    text = stringify(value)
    if not text:
        return '<span class="empty">（空）</span>'
    if as_html or looks_like_html(text) or looks_like_markdown(text):
        return f'<div class="html-body">{rewrite_preview_media(text, images)}</div>'
    return f'<div class="html-body">{html.escape(text).replace(chr(10), "<br>")}</div>'


def _field_rows(keys: list[str], fields: dict[str, Any], images: dict[str, str]) -> str:
    rows: list[str] = []
    for key in keys:
        if key not in fields:
            continue
        text = stringify(fields.get(key))
        as_html = key in HTML_KEYS or looks_like_html(text) or looks_like_markdown(text)
        rows.append(
            f"<tr><th>{html.escape(key.split('.')[-1])}</th>"
            f"<td>{_cell(fields.get(key), images, as_html=as_html)}</td></tr>"
        )
    return "".join(rows)


def _format_commit_date(raw: str) -> str:
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", (raw or "").strip())
    if match:
        year, month, day = match.groups()
        return f"{year}/{int(month)}/{int(day)}"
    return stringify(raw)


def _render_commits_html(commits: Any) -> str:
    rows = []
    show_ado = False
    for entry in commits or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("ado_id"):
            show_ado = True
        sha = html.escape(stringify(entry.get("sha_short") or stringify(entry.get("sha"))[:8]))
        message = html.escape(stringify(entry.get("message")))
        author = html.escape(stringify(entry.get("author")))
        date = html.escape(_format_commit_date(stringify(entry.get("date"))))
        ado = f"<td>#{html.escape(str(entry.get('ado_id')))}</td>" if entry.get("ado_id") else ""
        url = stringify(entry.get("url"))
        sha_cell = f'<a href="{html.escape(url)}">{sha}</a>' if url.startswith(("http://", "https://")) else sha
        rows.append(f"<tr>{ado}<td>{sha_cell}</td><td>{message}</td><td>{author}</td><td>{date}</td></tr>")
    if not rows:
        return ""
    ado_head = "<th>ADO</th>" if show_ado else ""
    return (
        "<h2>Commit</h2>"
        f"<table class='index'><tr>{ado_head}<th>SHA</th><th>訊息</th><th>作者</th><th>日期</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def render_ado_html(item: dict[str, Any], work_item_id: int) -> str:
    fields = item.get("fields") or {}
    images = item.get("images") or {}
    used = set(CUSTOM_KEYS) | set(META_KEYS) | HTML_KEYS
    extra_keys = sorted(key for key in fields if key not in used)
    title = stringify(item.get("title") or fields.get("System.Title") or f"Work Item {work_item_id}")
    work_item_type = stringify(item.get("work_item_type") or fields.get("System.WorkItemType"))
    state = stringify(item.get("state") or fields.get("System.State"))
    fetched_at = stringify(item.get("fetched_at"))

    history_rows = []
    for entry in item.get("history") or []:
        if not isinstance(entry, dict):
            continue
        when = html.escape(stringify(entry.get("date")).replace("T", " ").replace("Z", ""))
        by = html.escape(stringify(entry.get("by")) or "未知")
        lines = []
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            label = html.escape(stringify(change.get("field")))
            old = stringify(change.get("from"))
            new = stringify(change.get("to"))
            if old and new:
                arrow = f"{html.escape(old)} → {html.escape(new)}"
            elif old:
                arrow = f"移除 {html.escape(old)}"
            else:
                arrow = html.escape(new)
            lines.append(f"<div>{label}：{arrow}</div>")
        change_html = "".join(lines) or '<span class="empty">（無）</span>'
        history_rows.append(f"<tr><td>{when}</td><td>{by}</td><td>{change_html}</td></tr>")

    comments = []
    for comment in item.get("comments") or []:
        if not isinstance(comment, dict):
            continue
        author = html.escape(stringify(comment.get("created_by")) or "未知")
        created = html.escape(stringify(comment.get("created_date")))
        comments.append(
            f'<article class="comment"><header>{author} · {created}</header>'
            f'{_cell(comment.get("text"), images, as_html=True)}</article>'
        )

    relations = []
    for rel in item.get("relations") or []:
        if not isinstance(rel, dict):
            continue
        name = html.escape(stringify((rel.get("attributes") or {}).get("name") or rel.get("rel")))
        url = stringify(rel.get("url"))
        relations.append(f'<li>{name}：<a href="{html.escape(url)}">{html.escape(url)}</a></li>')

    body = f"""
    <main class="page">
    <h1>#{html.escape(str(work_item_id))} {html.escape(title)}</h1>
    <p class="sub">{html.escape(work_item_type)} · {html.escape(state)} · 抓取時間 {html.escape(fetched_at)}</p>
    <h2>自訂欄位</h2>
    <table class="meta">{_field_rows(CUSTOM_KEYS, fields, images) or '<tr><td class="empty">（無）</td></tr>'}</table>
    <h2>系統欄位</h2>
    <table class="meta">{_field_rows([*META_KEYS, *extra_keys], fields, images)}</table>
    <h2>變動歷史</h2>
    {"<table class='index history'><tr><th>時間</th><th>操作者</th><th>變更</th></tr>" + "".join(history_rows) + "</table>" if history_rows else '<p class="empty">沒有變動紀錄</p>'}
    <h2>描述</h2>
    {_cell(fields.get("System.Description"), images, as_html=True)}
    <h2>留言</h2>
    {"".join(comments) or '<p class="empty">沒有留言</p>'}
    <h2>關聯</h2>
    {"<ul class='relations'>" + "".join(relations) + "</ul>" if relations else '<p class="empty">沒有關聯</p>'}
    {_render_commits_html(item.get("commits") or extract_commits(item))}
    </main>
    """
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ADO #{html.escape(str(work_item_id))}</title>
  <style>
    :root {{
      --page-max: 880px;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #e5e7eb;
      --soft: #f3f4f6;
      --card: #ffffff;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      min-height: 100%;
      font-family: "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
      background: #eef1f5;
      color: var(--ink);
      line-height: 1.55;
    }}
    .page {{
      max-width: var(--page-max);
      margin: 0 auto;
      padding: 1.75rem 1.5rem 2.5rem;
      background: var(--card);
      min-height: 100vh;
      box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.04), 0 12px 40px rgba(15, 23, 42, 0.06);
    }}
    @media (min-width: 920px) {{
      body {{ padding: 1.5rem 1rem 2rem; background: #e8ecf1; }}
      .page {{
        min-height: auto;
        border-radius: 12px;
        padding: 2rem 2.25rem 2.75rem;
      }}
    }}
    h1 {{
      margin: 0 0 0.35rem;
      font-size: 1.45rem;
      font-weight: 650;
      line-height: 1.35;
      letter-spacing: -0.01em;
    }}
    h2 {{
      margin: 1.75rem 0 0.65rem;
      padding-top: 0.35rem;
      border-top: 1px solid var(--line);
      font-size: 1.05rem;
      font-weight: 650;
    }}
    h2:first-of-type {{ border-top: 0; padding-top: 0; }}
    .sub {{
      margin: 0 0 1.25rem;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .empty {{ color: var(--muted); }}
    table.meta, table.index {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
      margin: 0.25rem 0 0.5rem;
    }}
    table.meta th, table.meta td,
    table.index th, table.index td {{
      border: 1px solid var(--line);
      padding: 0.55rem 0.7rem;
      vertical-align: top;
      text-align: left;
    }}
    table.meta th, table.index th {{
      background: var(--soft);
      font-weight: 600;
      width: 9.5rem;
      color: #374151;
    }}
    table.index th {{ width: auto; white-space: nowrap; }}
    table.index td {{ word-break: break-word; }}
    a {{ color: var(--accent); text-underline-offset: 2px; }}
    a:hover {{ color: #1d4ed8; }}
    ul.relations {{
      margin: 0.35rem 0 0;
      padding-left: 1.2rem;
    }}
    ul.relations li {{ margin: 0.25rem 0; word-break: break-all; }}
    .comment {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0.75rem 0.9rem;
      margin: 0.55rem 0;
      background: #fafbfc;
    }}
    .comment header {{
      font-size: 0.85rem;
      color: var(--muted);
      margin-bottom: 0.45rem;
    }}
    .html-body {{ overflow-wrap: anywhere; }}
    .html-body img {{ max-width: 100%; height: auto; border-radius: 4px; }}
    .html-body pre {{
      background: var(--soft);
      padding: 12px;
      overflow: auto;
      border-radius: 6px;
    }}
    .html-body code {{
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 0.92em;
    }}
    .html-body blockquote {{
      border-left: 3px solid #d1d5db;
      margin: 0.6em 0;
      padding-left: 12px;
      color: #4b5563;
    }}
    .html-body h1, .html-body h2, .html-body h3 {{
      font-size: 1.05em;
      margin: 0.8em 0 0.4em;
    }}
  </style>
</head>
<body>{body}</body>
</html>
"""


def render_ado_html_or_error(item: dict[str, Any], work_item_id: int) -> str:
    try:
        return render_ado_html(item, work_item_id)
    except BaseException as exc:  # noqa: BLE001 — catch RecursionError / re.error 等
        work_item_id_str = html.escape(str(work_item_id))
        title = html.escape(stringify(item.get("title") or f"Work Item {work_item_id}"))
        error_msg = html.escape(str(exc)[:300])
        return (
            f"<!DOCTYPE html><html lang='zh-Hant'><head><meta charset='utf-8'>"
            f"<style>body{{font-family:sans-serif;margin:16px;color:#222}}"
            f".err{{color:#dc2626;background:#fef2f2;border:1px solid #fecaca;"
            f"border-radius:6px;padding:12px;margin-top:1rem}}</style></head>"
            f"<body><h1>#{work_item_id_str} {title}</h1>"
            f"<div class='err'>⚠ HTML 渲染失敗，無法顯示完整原文。<br>"
            f"<small>{error_msg}</small></div></body></html>"
        )
