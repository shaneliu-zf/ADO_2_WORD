#!/usr/bin/env python3
"""從 Azure DevOps 抓取指定 Work Item，並單筆存成 HTML。"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.ado_client import auth_header, fetch_comments, fetch_work_item
from utils.config_io import load_config
from utils.paths import HTML_DIR, INDEX_HTML_TEMPLATE, STYLE_PATH, WORK_ITEM_HTML_TEMPLATE
from utils.pipeline_io import log, log_stage, log_stage_done, normalize_ids, read_pipeline_json, write_pipeline_json

IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE | re.DOTALL)
MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
HTML_TAG_RE = re.compile(r"</?(div|p|table|img|span|br|h[1-6]|ul|ol|li|pre|code|blockquote)\b", re.IGNORECASE)
MD_HINT_RE = re.compile(r"\*\*[^*]+\*\*|!\[[^\]]*\]\([^)]+\)|(?<!!)\[[^\]]+\]\([^)]+\)|(^|\n)\s{0,3}#{1,6}\s|(^|\n)\s{0,3}(\d+\.|[-*+])\s", re.MULTILINE)

HTML_FIELD_KEYS = {
    "System.Description",
    "Microsoft.VSTS.TCM.ReproSteps",
    "Microsoft.VSTS.TCM.Steps",
}

META_FIELD_KEYS = [
    "System.Id",
    "System.WorkItemType",
    "System.Title",
    "System.State",
    "System.AssignedTo",
    "System.CreatedBy",
    "System.CreatedDate",
    "System.ChangedBy",
    "System.ChangedDate",
    "System.AreaPath",
    "System.IterationPath",
    "System.Tags",
]

CUSTOM_FIELD_KEYS = [
    "Custom.Case",
    "Custom.Step",
    "Custom.Program",
    "Custom.Category",
    "Custom.Systems",
    "Custom.Tag",
    "Custom.IssuePriority",
    "Custom.PrimaryCause",
    "Custom.Solution",
]


def field_label(key: str) -> str:
    if key.startswith("Custom."):
        return key.split(".", 1)[1]
    return key


def identity_name(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("displayName")
    return value


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("displayName") or value.get("uniqueName") or json.dumps(value, ensure_ascii=False))
    if isinstance(value, list):
        return "; ".join(item for item in (stringify(v) for v in value) if item)
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value)


def looks_like_html(value: str) -> bool:
    return bool(HTML_TAG_RE.search(value))


def looks_like_markdown(value: str) -> bool:
    return bool(MD_HINT_RE.search(value))


def collect_image_urls(*html_chunks: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        url = html.unescape(url).strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    for chunk in html_chunks:
        if not chunk:
            continue
        for match in IMG_SRC_RE.finditer(chunk):
            add(match.group(3))
        for match in MD_IMG_RE.finditer(chunk):
            add(match.group(2).split()[0].strip("<>"))
    return urls


def markdown_to_html(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    placeholders: list[str] = []

    def protect(fragment: str) -> str:
        placeholders.append(fragment)
        return f"@@PH{len(placeholders) - 1}@@"

    def repl_img(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1), quote=True)
        src = html.escape(html.unescape(match.group(2).split()[0].strip("<>")), quote=True)
        return protect(f'<img src="{src}" alt="{alt}">')

    def repl_link(match: re.Match[str]) -> str:
        label = html.escape(match.group(1))
        raw = match.group(2).strip()
        href, _, title = raw.partition(" ")
        href_esc = html.escape(html.unescape(href.strip("<>")), quote=True)
        if title:
            title = title.strip().strip('"').strip("'")
            return protect(f'<a href="{href_esc}" title="{html.escape(title, quote=True)}">{label}</a>')
        return protect(f'<a href="{href_esc}">{label}</a>')

    text = MD_IMG_RE.sub(repl_img, text)
    text = MD_LINK_RE.sub(repl_link, text)

    parts = re.split(r"(@@PH\d+@@)", text)
    escaped: list[str] = []
    entity_re = re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);")
    for part in parts:
        if re.fullmatch(r"@@PH\d+@@", part):
            escaped.append(part)
            continue
        entities: list[str] = []

        def stash_entity(match: re.Match[str]) -> str:
            entities.append(match.group(0))
            return f"@@ENT{len(entities) - 1}@@"

        piece = entity_re.sub(stash_entity, part)
        piece = html.escape(piece, quote=False)
        for idx, entity in enumerate(entities):
            piece = piece.replace(f"@@ENT{idx}@@", entity)
        escaped.append(piece)
    text = "".join(escaped)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)

    lines = text.split("\n")
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue

        ordered = re.match(r"^\s*\d+\.\s+(.*)$", lines[index])
        bullet = re.match(r"^\s*[-*+]\s+(.*)$", lines[index])
        if ordered or bullet:
            items: list[str] = []
            list_re = re.compile(r"^\s*\d+\.\s+(.*)$") if ordered else re.compile(r"^\s*[-*+]\s+(.*)$")
            while index < len(lines):
                if not lines[index].strip():
                    index += 1
                    continue
                item_match = list_re.match(lines[index])
                if item_match:
                    items.append(item_match.group(1))
                    index += 1
                    continue
                if items and not re.match(r"^\s*(\d+\.|[-*+])\s+", lines[index]):
                    items[-1] += "<br>" + lines[index].strip()
                    index += 1
                    continue
                break
            tag = "ol" if ordered else "ul"
            blocks.append(f"<{tag}>" + "".join(f"<li>{item}</li>" for item in items) + f"</{tag}>")
            continue

        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", lines[index])
        if heading:
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{heading.group(2).strip()}</h{level}>")
            index += 1
            continue

        para = [lines[index].strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not re.match(r"^\s*(\d+\.|[-*+]|#{1,6}\s)", lines[index]):
            para.append(lines[index].strip())
            index += 1
        blocks.append("<p>" + "<br>".join(para) + "</p>")

    html_out = "\n".join(blocks)
    for idx, fragment in enumerate(placeholders):
        html_out = html_out.replace(f"@@PH{idx}@@", fragment)
    return html_out


def safe_filename(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    raw_name = (query.get("fileName") or query.get("filename") or [""])[0]
    name = Path(raw_name).name if raw_name else Path(parsed.path).name
    if not name or name in {".", ".."}:
        name = f"image_{index}.png"
    stem = Path(name).stem or f"image_{index}"
    suffix = Path(name).suffix or ".png"
    guid = Path(parsed.path).name[:8]
    return f"{guid}_{stem}{suffix}" if guid else f"{index}_{stem}{suffix}"


def download_file(url: str, dest: Path, authorization: str) -> None:
    req = urllib.request.Request(url, headers={"Authorization": authorization})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def localize_html(content: str, url_map: dict[str, str]) -> str:
    if not content:
        return ""

    def replace(match: re.Match[str]) -> str:
        prefix, quote, src = match.group(1), match.group(2), match.group(3)
        original = html.unescape(src).strip()
        local = url_map.get(original) or url_map.get(src)
        if not local:
            return match.group(0)
        return f"{prefix}{quote}{html.escape(local, quote=True)}{quote}"

    return IMG_SRC_RE.sub(replace, content)


def download_images(
    item: dict[str, Any],
    authorization: str,
    media_dir: Path,
    skip_download: bool = False,
) -> dict[str, str]:
    fields = item.get("fields") or {}
    chunks = [stringify(fields.get(key)) for key in HTML_FIELD_KEYS]
    chunks.extend(stringify(comment.get("text")) for comment in (item.get("comments") or []))
    urls = collect_image_urls(*chunks)
    url_map: dict[str, str] = {}
    if not urls:
        return url_map

    if not skip_download:
        media_dir.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(urls, start=1):
        filename = safe_filename(url, index)
        dest = media_dir / filename
        relative = f"{media_dir.name}/{filename}"
        if dest.exists():
            url_map[url] = relative
            continue
        if skip_download:
            continue
        try:
            download_file(url, dest, authorization)
            url_map[url] = relative
            log(f"  已下載圖片：{filename}")
        except Exception as exc:
            log(f"  圖片下載失敗，保留原網址：{url}（{exc}）")
    return url_map


def render_rich_text(text: str, url_map: dict[str, str]) -> str:
    if not text.strip():
        return "<span class=\"empty\">（空）</span>"
    if looks_like_html(text):
        body = localize_html(text, url_map)
    elif looks_like_markdown(text):
        body = localize_html(markdown_to_html(text), url_map)
    else:
        body = html.escape(text).replace("\n", "<br>\n")
    return f'<div class="html-body">{body}</div>'


def render_field_value(_key: str, value: Any, url_map: dict[str, str]) -> str:
    text = stringify(value)
    if not text:
        return "<span class=\"empty\">（空）</span>"
    return render_rich_text(text, url_map)


def render_template(template_path: Path, **values: str) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def save_work_item_html(item: dict[str, Any], authorization: str, skip_download: bool = False) -> Path:
    work_item_id = item["id"]
    media_dir = HTML_DIR / f"work_item_{work_item_id}_files"
    url_map = download_images(item, authorization, media_dir, skip_download=skip_download)

    fields: dict[str, Any] = item.get("fields") or {}
    title = stringify(item.get("title") or fields.get("System.Title") or f"Work Item {work_item_id}")
    used = set(HTML_FIELD_KEYS)
    meta_keys = [key for key in META_FIELD_KEYS if key in fields]
    used.update(meta_keys)
    used.update(CUSTOM_FIELD_KEYS)
    extra_keys = sorted(key for key in fields if key not in used)

    def rows_for(keys: list[str], always: bool = False) -> list[str]:
        rows = []
        for key in keys:
            if key in HTML_FIELD_KEYS:
                continue
            if not always and key not in fields:
                continue
            rows.append(
                f"<tr><th>{html.escape(field_label(key))}</th>"
                f"<td>{render_field_value(key, fields.get(key), url_map)}</td></tr>"
            )
        return rows

    custom_rows = rows_for(CUSTOM_FIELD_KEYS, always=True)
    meta_rows = rows_for(meta_keys)
    extra_rows = rows_for(extra_keys)

    description = render_field_value("System.Description", fields.get("System.Description"), url_map)

    comment_blocks = []
    for comment in item.get("comments") or []:
        body = render_rich_text(stringify(comment.get("text")), url_map)
        author = html.escape(stringify(comment.get("created_by")) or "未知")
        created = html.escape(stringify(comment.get("created_date")))
        comment_blocks.append(
            f'<article class="comment"><header>{author} · {created}</header>{body}</article>'
        )
    comments_html = "".join(comment_blocks) or "<p class=\"empty\">沒有留言</p>"

    relation_items = []
    for rel in item.get("relations") or []:
        name = html.escape(stringify((rel.get("attributes") or {}).get("name") or rel.get("rel")))
        url = stringify(rel.get("url"))
        relation_items.append(f'<li>{name}：<a href="{html.escape(url, quote=True)}">{html.escape(url)}</a></li>')
    relations_html = f"<ul>{''.join(relation_items)}</ul>" if relation_items else "<p class=\"empty\">沒有關聯</p>"

    if not WORK_ITEM_HTML_TEMPLATE.exists():
        raise FileNotFoundError(f"找不到 HTML 樣板：{WORK_ITEM_HTML_TEMPLATE}")

    page = render_template(
        WORK_ITEM_HTML_TEMPLATE,
        page_title=f"#{html.escape(str(work_item_id))} {html.escape(title)}",
        heading=f"#{html.escape(str(work_item_id))} {html.escape(title)}",
        subtitle=(
            f"{html.escape(stringify(item.get('work_item_type')))} · "
            f"{html.escape(stringify(item.get('state')))} · "
            f"抓取時間 {html.escape(stringify(item.get('fetched_at')))}"
        ),
        custom_rows="".join(custom_rows),
        meta_rows="".join(meta_rows + extra_rows),
        description=description,
        comments=comments_html,
        relations=relations_html,
    )
    path = HTML_DIR / f"work_item_{work_item_id}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


def save_index(items: list[dict[str, Any]]) -> Path:
    rows = []
    for item in items:
        work_item_id = item["id"]
        title = html.escape(stringify(item.get("title")))
        href = html.escape(f"work_item_{work_item_id}.html", quote=True)
        rows.append(
            f"<tr><td><a href=\"{href}\">#{work_item_id}</a></td>"
            f"<td>{html.escape(stringify(item.get('work_item_type')))}</td>"
            f"<td>{html.escape(stringify(item.get('state')))}</td>"
            f"<td><a href=\"{href}\">{title}</a></td></tr>"
        )
    if not INDEX_HTML_TEMPLATE.exists():
        raise FileNotFoundError(f"找不到 HTML 樣板：{INDEX_HTML_TEMPLATE}")
    page = render_template(INDEX_HTML_TEMPLATE, rows="".join(rows))
    path = HTML_DIR / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


def simplify(work_item: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
    fields = work_item.get("fields") or {}
    return {
        "id": work_item.get("id"),
        "work_item_type": fields.get("System.WorkItemType"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "fields": fields,
        "relations": [
            {
                "rel": rel.get("rel"),
                "url": rel.get("url"),
                "attributes": rel.get("attributes") or {},
            }
            for rel in (work_item.get("relations") or [])
        ],
        "comments": [
            {
                "id": comment.get("id"),
                "text": comment.get("text"),
                "created_date": comment.get("createdDate"),
                "created_by": identity_name(comment.get("createdBy")),
            }
            for comment in comments
        ],
        "comment_count": len(comments),
    }


def run_fetch(work_item_ids: list[int], *, no_images: bool = False) -> list[int]:
    config = load_config()
    log_stage(f"2/5 FETCH  抓取 ADO HTML（{len(work_item_ids)} 筆）")
    authorization = auth_header(config["pat"])
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: list[dict[str, Any]] = []
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STYLE_PATH, HTML_DIR / "style.css")

    for work_item_id in work_item_ids:
        log(f"正在抓取 Work Item {work_item_id} …")
        item = simplify(
            fetch_work_item(config, authorization, work_item_id),
            fetch_comments(config, authorization, work_item_id),
        )
        item["fetched_at"] = fetched_at
        if item.get("work_item_type") != "Issue":
            log(f"  略過（類型為 {item.get('work_item_type')}，只保留 Issue）")
            continue
        path = save_work_item_html(item, authorization, skip_download=no_images)
        results.append(item)
        log(
            f"  標題：{item.get('title')}\n"
            f"  欄位數：{len(item.get('fields') or {})}　留言數：{item['comment_count']}\n"
            f"  已寫入：{path}"
        )

    index_path = save_index(results)
    log(f"目錄：{index_path}")
    log_stage_done(f"FETCH 完成，成功 {len(results)} 筆")
    return [int(item["id"]) for item in results]


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取 Azure DevOps Work Item 並存成 HTML")
    parser.add_argument("--no-images", action="store_true", help="不下載圖片；若本機已有檔案則沿用")
    args = parser.parse_args()
    write_pipeline_json(run_fetch(normalize_ids(read_pipeline_json()), no_images=args.no_images))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        sys.exit(1)
