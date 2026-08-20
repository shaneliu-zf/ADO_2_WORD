#!/usr/bin/env python3
"""讀取並解析 fetch 產出的 ADO JSON（欄位、Redmine、關聯）。"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
from typing import Any

from backend.utils.paths import ADO_DIR


TAG_RE = re.compile(r"<[^>]+>")
# 標題結尾常見 (63852.64178) 或 (63759)
TITLE_REDMINE_RE = re.compile(r"\(#?(\d{4,}(?:\.\d+)*)\)\s*$")
# 留言常見 BUG #63474 / redmine 63474
COMMENT_REDMINE_RE = re.compile(r"(?i)(?:redmine\s*#?\s*|BUG\s*#\s*)(\d{4,}(?:\.\d+)*)")
RELATED_ID_RE = re.compile(r"(?i)/workItems/(\d+)")
GIT_COMMIT_SHA_RE = re.compile(r"(?i)^[0-9a-f]{40}$")
GIT_COMMIT_VSTFS_RE = re.compile(r"(?i)^vstfs:///Git/Commit/(.+)$")
GIT_COMMIT_WEB_RE = re.compile(r"(?i)/_git/[^/]+/commit/([0-9a-f]{7,40})\b")
IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE | re.DOTALL)
MD_IMG_RE = re.compile(
    r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:[ \t]+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
ADO_COLON_IMG_RE = re.compile(r":::image\b(.*?):::", re.IGNORECASE | re.DOTALL)
ADO_COLON_SRC_RE = re.compile(r'\bsource\s*=\s*"([^"]+)"', re.IGNORECASE)
HTML_HINT_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9]*(?:\s|>|/)")
MD_HINT_RE = re.compile(
    r"(?m)(?:!\[[^\]]*\]\(|^#{1,6}\s|^\s{0,3}(?:[-*+]|\d+\.)\s|\*\*[^*\n]+\*\*|```|^\|.+\||:::image\b)",
)


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
    for url, local in sorted(images.items(), key=lambda item: len(item[0] or ""), reverse=True):
        if not url or not local:
            continue
        if url in out:
            out = out.replace(url, local)
        escaped = html.escape(url, quote=True)
        if escaped != url and escaped in out:
            out = out.replace(escaped, html.escape(local, quote=True))
    return out


def looks_like_html(text: str) -> bool:
    return bool(HTML_HINT_RE.search(text or ""))


def looks_like_markdown(text: str) -> bool:
    return bool(MD_HINT_RE.search(text or ""))


def extract_image_urls(*chunks: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        url = html.unescape(url or "").strip().strip("<>")
        if url.startswith("#") or url.lower().startswith("javascript:"):
            return
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    for chunk in chunks:
        if not chunk:
            continue
        for match in IMG_SRC_RE.finditer(chunk):
            add(match.group(3))
        for match in MD_IMG_RE.finditer(chunk):
            add(match.group(2))
        for match in ADO_COLON_IMG_RE.finditer(chunk):
            src = ADO_COLON_SRC_RE.search(match.group(1) or "")
            if src:
                add(src.group(1))
    return urls


def collect_item_image_urls(item: dict[str, Any]) -> list[str]:
    chunks: list[str] = []
    for value in (item.get("fields") or {}).values():
        if isinstance(value, str) and value:
            chunks.append(value)
    for comment in item.get("comments") or []:
        if not isinstance(comment, dict):
            continue
        text = stringify(comment.get("text"))
        if text:
            chunks.append(text)
    urls = extract_image_urls(*chunks)
    seen = set(urls)
    for rel in item.get("relations") or []:
        if not isinstance(rel, dict):
            continue
        url = str(rel.get("url") or "").strip()
        rel_type = str(rel.get("rel") or "")
        if rel_type == "AttachedFile" or "/_apis/wit/attachments/" in url:
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def _md_images_to_html(text: str) -> str:
    def repl_md(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1) or "", quote=True)
        src = html.escape(html.unescape(match.group(2)).strip(), quote=True)
        return f'<img src="{src}" alt="{alt}">'

    def repl_colon(match: re.Match[str]) -> str:
        src_match = ADO_COLON_SRC_RE.search(match.group(1) or "")
        if not src_match:
            return match.group(0)
        src = html.escape(html.unescape(src_match.group(1)).strip(), quote=True)
        return f'<img src="{src}" alt="">'

    out = MD_IMG_RE.sub(repl_md, text or "")
    return ADO_COLON_IMG_RE.sub(repl_colon, out)


def render_rich_html(text: str) -> str:
    """把 ADO 原文（HTML、Markdown 或兩者混合）轉成可預覽的 HTML。"""
    fragment = _md_images_to_html(text or "")
    if not looks_like_markdown(text or ""):
        return fragment
    import markdown

    extensions = ["extra", "sane_lists"]
    if not looks_like_html(text or ""):
        extensions.append("nl2br")
    try:
        return markdown.markdown(fragment, extensions=extensions)
    except Exception:
        # markdown 解析失敗（特殊字元、超長輸入等）：fallback 回原始 HTML fragment
        return fragment


def prefix_static_media(html_text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        prefix, quote, src = match.group(1), match.group(2), html.unescape(match.group(3)).strip()
        if src.startswith(("http://", "https://", "data:", "/")):
            new_src = src
        else:
            new_src = "/static/ado/" + src.lstrip("./")
        return f"{prefix}{quote}{html.escape(new_src, quote=True)}{quote}"

    try:
        return IMG_SRC_RE.sub(repl, html_text or "")
    except (re.error, RecursionError):
        return html_text or ""


def rewrite_preview_media(text: str, images: dict[str, str] | None = None) -> str:
    try:
        mapped = apply_image_map(text or "", images)
        return prefix_static_media(render_rich_html(mapped))
    except (re.error, RecursionError, Exception):
        # fallback：回傳純文字 HTML，至少不 crash
        return html.escape(text or "").replace("\n", "<br>")


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


def last_state_actor(item: dict[str, Any], state: str) -> str:
    """變更歷史中，最後一次把狀態改成 `state` 的操作者。"""
    actor = ""
    target = (state or "").strip().casefold()
    if not target:
        return ""
    for entry in item.get("history") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            if change.get("field") != "System.State":
                continue
            if str(change.get("to") or "").strip().casefold() != target:
                continue
            actor = stringify(entry.get("by"))
    return actor


def parse_git_commit_ref(url: str) -> dict[str, str] | None:
    """從 ArtifactLink 網址抽出 Git commit SHA（以及可能的 repo id）。"""
    raw = html.unescape(str(url or "")).strip()
    if not raw:
        return None
    decoded = urllib.parse.unquote(raw)
    match = GIT_COMMIT_VSTFS_RE.match(decoded)
    if match:
        parts = [part for part in match.group(1).split("/") if part]
        sha = parts[-1] if parts else ""
        if GIT_COMMIT_SHA_RE.match(sha) and len(parts) >= 3:
            return {"project_id": parts[0], "repo_id": parts[1], "sha": sha.lower()}
        if GIT_COMMIT_SHA_RE.match(sha):
            return {"project_id": "", "repo_id": "", "sha": sha.lower()}
    web = GIT_COMMIT_WEB_RE.search(decoded)
    if web:
        sha = web.group(1).lower()
        if len(sha) >= 7:
            return {"project_id": "", "repo_id": "", "sha": sha}
    return None


def extract_commits(item: dict[str, Any]) -> list[dict[str, str]]:
    """從 Work Item relations 抽出關聯的 Git commit。"""
    commits: list[dict[str, str]] = []
    seen: set[str] = set()
    for rel in item.get("relations") or []:
        if not isinstance(rel, dict):
            continue
        parsed = parse_git_commit_ref(str(rel.get("url") or ""))
        if parsed is None:
            continue
        sha = parsed["sha"]
        if sha in seen:
            continue
        seen.add(sha)
        attrs = rel.get("attributes") or {}
        message = stringify(attrs.get("comment"))
        commits.append(
            {
                "sha": sha,
                "sha_short": sha[:8],
                "message": message.splitlines()[0].strip() if message else "",
                "author": "",
                "date": stringify(
                    attrs.get("resourceCreatedDate")
                    or attrs.get("authorizedDate")
                    or attrs.get("resourceModifiedDate")
                ),
                "url": str(rel.get("url") or ""),
                "name": stringify(attrs.get("name")),
                "repo_id": parsed.get("repo_id") or "",
                "project_id": parsed.get("project_id") or "",
            }
        )
    return commits


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
