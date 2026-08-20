"""Vue 前端需要的 JSON API（掛在既有 Flask 上）。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import html
import json
import queue
import re
import shutil
import threading
import uuid
from typing import Any

from flask import Blueprint, Response, jsonify, request, send_from_directory, stream_with_context

from backend.pipeline import STEPS, run_from, run_step
from backend.pipeline.report_by_llm import resolve_site
from backend.utils.config_io import read_config_file, save_config
from backend.utils.paths import ADO_DIR, DOCX_DIR, JSON_DIR, STYLE_PATH
from backend.utils.pipeline_io import add_log_sink, remove_log_sink
from backend.utils.report_schema import find_report, validate_report
from backend.utils.work_item_parser import (
    extract_commits,
    extract_redmine,
    last_state_actor,
    looks_like_html,
    looks_like_markdown,
    read_work_item,
    rewrite_preview_media,
    stringify,
)

bp = Blueprint("frontend_api", __name__)

LISTED_PATH = ADO_DIR / "listed.json"
GROUPS_PATH = ADO_DIR / "groups.json"
UI_SESSION_PATH = ADO_DIR / "ui_session.json"
PIPELINE_STEP_COUNT = 4
SCRIPT_INDEX = {
    "fetch": 1,
    "group": 2,
    "report_by_llm": 3,
    "word": 4,
}
SCRIPT_ALIASES = {
    "list_ids": "list_ids",
    "fetch": "fetch",
    "group": "group",
    "report": "report_by_llm",
    "report_by_llm": "report_by_llm",
    "word": "word",
    "main": "main",
}
REFRESH_SCRIPTS = {"list_ids", "fetch", "group", "main", "report_by_llm"}
CUSTOM_KEYS = [
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
META_KEYS = [
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
HTML_KEYS = {
    "System.Description",
    "Microsoft.VSTS.TCM.ReproSteps",
    "Microsoft.VSTS.TCM.Steps",
}
ADO_JSON_RE = re.compile(r"^work_item_(\d+)\.json$")
_pipeline_lock = threading.Lock()
_session_file_lock = threading.Lock()
_pipeline_running = False
_abort_event = threading.Event()


def _json_error(exc: Exception, status: int = 400):
    message = str(exc)
    return jsonify(error=message, message=message), status


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _load_listed() -> list[dict[str, Any]]:
    if not LISTED_PATH.exists():
        return []
    try:
        payload = json.loads(LISTED_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    rows = payload if isinstance(payload, list) else payload.get("items") or []
    result: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict) and row.get("id") is not None:
            result.append(row)
        elif isinstance(row, int):
            result.append({"id": row, "title": "", "work_item_type": "", "state": ""})
    return result


def _save_listed(rows: list[dict[str, Any]]) -> None:
    ADO_DIR.mkdir(parents=True, exist_ok=True)
    LISTED_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _remove_listed_ids(ids: set[int]) -> None:
    remaining = [row for row in _load_listed() if int(row.get("id") or 0) not in ids]
    if remaining or LISTED_PATH.exists():
        _save_listed(remaining)


def _group_payload(ids: list[int]) -> dict[str, Any]:
    unique: list[int] = []
    for value in ids:
        work_item_id = int(value)
        if work_item_id not in unique:
            unique.append(work_item_id)
    primary = min(unique)
    redmine = ""
    report = find_report(primary)
    if report:
        redmine = stringify(report.get("redmine_id"))
    if not redmine:
        try:
            redmine = extract_redmine(read_work_item(primary))
        except FileNotFoundError:
            pass
    return {"ids": unique, "primary_id": primary, "redmine_id": redmine}


def _save_groups(groups: list[list[int]]) -> None:
    ADO_DIR.mkdir(parents=True, exist_ok=True)
    payload = [_group_payload(group) for group in groups if group]
    GROUPS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_group_id_lists() -> list[list[int]]:
    if not GROUPS_PATH.exists():
        return []
    try:
        saved = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(saved, list):
        return []
    groups: list[list[int]] = []
    for row in saved:
        values = row.get("ids") if isinstance(row, dict) else row
        if not isinstance(values, list):
            continue
        ids: list[int] = []
        for value in values:
            try:
                work_item_id = int(value)
            except (TypeError, ValueError):
                continue
            if work_item_id not in ids:
                ids.append(work_item_id)
        if ids:
            groups.append(ids)
    return groups


def _remove_ids_from_groups(drop: set[int]) -> None:
    if not drop or not GROUPS_PATH.exists():
        return
    next_groups = [[work_item_id for work_item_id in ids if work_item_id not in drop] for ids in _load_group_id_lists()]
    next_groups = [ids for ids in next_groups if ids]
    _save_groups(next_groups)


def _sync_groups_to_listed() -> None:
    keep = {int(row["id"]) for row in _load_listed() if row.get("id") is not None}
    drop = {work_item_id for ids in _load_group_id_lists() for work_item_id in ids if work_item_id not in keep}
    if drop:
        _remove_ids_from_groups(drop)


def _grouped_ids() -> set[int]:
    ids: set[int] = set()
    if not GROUPS_PATH.exists():
        return ids
    try:
        saved = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ids
    if not isinstance(saved, list):
        return ids
    for row in saved:
        values = row.get("ids") if isinstance(row, dict) else row
        if not isinstance(values, list):
            continue
        for value in values:
            try:
                ids.add(int(value))
            except (TypeError, ValueError):
                continue
    return ids


def _known_item_ids() -> list[int]:
    ids: set[int] = set()
    for row in _load_listed():
        ids.add(int(row["id"]))
    if ADO_DIR.exists():
        for path in ADO_DIR.glob("work_item_*.json"):
            match = ADO_JSON_RE.fullmatch(path.name)
            if match:
                ids.add(int(match.group(1)))
    if JSON_DIR.exists():
        for path in JSON_DIR.glob("work_item_*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(payload, dict):
                ids.update(_ado_ids_from_report(payload))
    return sorted(ids)


def _iso_mtime(path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _parse_id_list(raw: Any) -> list[int]:
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else str(raw).replace(";", ",").split(",")
    ids: list[int] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        try:
            work_item_id = int(text)
        except (TypeError, ValueError):
            continue
        if work_item_id not in ids:
            ids.append(work_item_id)
    return ids


def _requested_ids() -> list[int] | None:
    query_ids = request.args.get("ids")
    if query_ids not in (None, ""):
        return _parse_id_list(query_ids)
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        if isinstance(body.get("ids"), list):
            return _parse_id_list(body.get("ids"))
        return []
    return None


def _default_ui_session() -> dict[str, Any]:
    return {
        "working_ids": [],
        "listed_ids": [],
        "current_step": 1,
        "reached_step": 0,
        "pipeline_steps": PIPELINE_STEP_COUNT,
    }


def _session_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ids": list(data.get("working_ids") or []),
        "listedIds": list(data.get("listed_ids") or []),
        "currentStep": int(data.get("current_step") or 1),
        "reachedStep": int(data.get("reached_step") or 0),
    }


def _load_ui_session() -> dict[str, Any]:
    data = _default_ui_session()
    if not UI_SESSION_PATH.exists():
        return data
    try:
        payload = json.loads(UI_SESSION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return data
    if not isinstance(payload, dict):
        return data
    data["working_ids"] = _parse_id_list(payload.get("working_ids"))
    data["listed_ids"] = _parse_id_list(payload.get("listed_ids"))
    data["current_step"] = int(payload.get("current_step") or 1)
    data["reached_step"] = int(payload.get("reached_step") or 0)
    if int(payload.get("pipeline_steps") or 0) != PIPELINE_STEP_COUNT:
        old_current = data["current_step"]
        old_reached = data["reached_step"]
        data["current_step"] = max(1, min(PIPELINE_STEP_COUNT, old_current - 1 if old_current >= 2 else 1))
        data["reached_step"] = max(0, min(PIPELINE_STEP_COUNT, old_reached - 1 if old_reached >= 1 else 0))
        data["pipeline_steps"] = PIPELINE_STEP_COUNT
        return _save_ui_session(data)
    data["current_step"] = max(1, min(PIPELINE_STEP_COUNT, data["current_step"]))
    data["reached_step"] = max(0, min(PIPELINE_STEP_COUNT, data["reached_step"]))
    data["pipeline_steps"] = PIPELINE_STEP_COUNT
    return data


def _save_ui_session(data: dict[str, Any]) -> dict[str, Any]:
    ADO_DIR.mkdir(parents=True, exist_ok=True)
    with _session_file_lock:
        UI_SESSION_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def _working_ids() -> list[int]:
    return list(_load_ui_session().get("working_ids") or [])


def _ids_from_result(result: Any) -> list[int]:
    found: list[int] = []

    def walk(value: Any) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, int):
            found.append(value)
        elif isinstance(value, dict) and value.get("id") is not None:
            found.append(int(value["id"]))
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(result)
    return _parse_id_list(found)


def _update_session_after_run(
    script: str,
    result: Any,
    request_ids: list[int],
    keep_ids: list[int] | None = None,
) -> dict[str, Any]:
    data = _load_ui_session()
    extracted = _ids_from_result(result)
    if script == "list_ids":
        data["working_ids"] = extracted
        data["listed_ids"] = extracted
    elif keep_ids:
        data["working_ids"] = keep_ids
    elif extracted:
        data["working_ids"] = extracted
    elif request_ids:
        data["working_ids"] = request_ids

    if script == "main":
        data["reached_step"] = PIPELINE_STEP_COUNT
        data["current_step"] = PIPELINE_STEP_COUNT
        if not data["working_ids"] and request_ids:
            data["working_ids"] = request_ids
    else:
        index = SCRIPT_INDEX.get(script, 0)
        if index:
            data["reached_step"] = max(int(data.get("reached_step") or 0), index)
            current = int(data.get("current_step") or 1)
            if current == index and index < PIPELINE_STEP_COUNT:
                data["current_step"] = index + 1
            elif index >= PIPELINE_STEP_COUNT:
                data["current_step"] = PIPELINE_STEP_COUNT
    return _save_ui_session(data)


def _empty_item(work_item_id: int) -> dict[str, Any]:
    return {
        "id": work_item_id,
        "title": "",
        "workItemType": "",
        "state": "",
        "site": "",
        "category": "",
        "issuePriority": "",
        "redmineId": "",
        "assignedTo": "",
        "createdBy": "",
        "saBy": "",
        "engineerBy": "",
        "testerBy": "",
        "createdDate": "",
        "fetched": False,
        "grouped": False,
        "hasReport": False,
        "hasJson": False,
        "hasHtml": False,
        "lastUpdated": "",
    }


def _build_item(
    work_item_id: int,
    listed_row: dict[str, Any] | None = None,
    grouped_ids: set[int] | None = None,
) -> dict[str, Any]:
    item = _empty_item(work_item_id)
    item["grouped"] = work_item_id in (grouped_ids or ())
    if listed_row:
        item["title"] = stringify(listed_row.get("title"))
        item["workItemType"] = stringify(listed_row.get("work_item_type") or listed_row.get("workItemType"))
        item["state"] = stringify(listed_row.get("state"))

    ado_path = ADO_DIR / f"work_item_{work_item_id}.json"
    if ado_path.exists():
        try:
            payload = json.loads(ado_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            payload = None
        if isinstance(payload, dict):
            fields = payload.get("fields") or {}
            item["title"] = stringify(payload.get("title") or fields.get("System.Title")) or item["title"]
            item["workItemType"] = (
                stringify(payload.get("work_item_type") or fields.get("System.WorkItemType"))
                or item["workItemType"]
            )
            item["state"] = stringify(payload.get("state") or fields.get("System.State")) or item["state"]
            item["site"] = resolve_site(fields) or item["site"]
            item["category"] = stringify(fields.get("Custom.Category"))
            item["issuePriority"] = stringify(fields.get("Custom.IssuePriority"))
            item["assignedTo"] = stringify(fields.get("System.AssignedTo"))
            item["createdBy"] = stringify(fields.get("System.CreatedBy"))
            item["saBy"] = last_state_actor(payload, "Analyze")
            item["engineerBy"] = last_state_actor(payload, "Develop")
            item["testerBy"] = last_state_actor(payload, "Testing")
            created = stringify(fields.get("System.CreatedDate"))
            match = re.search(r"(\d{4}-\d{2}-\d{2})", created)
            item["createdDate"] = match.group(1) if match else created[:10]
            item["redmineId"] = extract_redmine(payload)
            item["fetched"] = True
            item["hasHtml"] = True
            item["lastUpdated"] = stringify(payload.get("fetched_at")) or _iso_mtime(ado_path)

    if not item["redmineId"] and item["title"]:
        item["redmineId"] = extract_redmine(
            {"fields": {"System.Title": item["title"]}, "comments": []}
        )

    report_path, report = _report_path_for(work_item_id)
    if report:
        item["title"] = item["title"] or stringify(report.get("ado_subject"))
        item["site"] = item["site"] or stringify(report.get("site"))
        item["hasReport"] = True
        item["hasJson"] = True
        if not item["redmineId"]:
            item["redmineId"] = stringify(report.get("redmine_id"))
        if report_path is not None and report_path.exists() and not item["lastUpdated"]:
            item["lastUpdated"] = _iso_mtime(report_path)
    return item


def _ado_ids_from_report(payload: dict[str, Any]) -> list[int]:
    values = payload.get("ado_ids") or [payload.get("ado_id")]
    ids: list[int] = []
    for value in values:
        if value is None:
            continue
        work_item_id = int(value)
        if work_item_id not in ids:
            ids.append(work_item_id)
    return ids


def _report_path_for(work_item_id: int):
    report = find_report(work_item_id)
    if report is None:
        return None, None
    primary = int(report.get("ado_id") or work_item_id)
    return JSON_DIR / f"work_item_{primary}.json", report


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


def _render_ado_html(item: dict[str, Any], work_item_id: int) -> str:
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
    {"<ul>" + "".join(relations) + "</ul>" if relations else '<p class="empty">沒有關聯</p>'}
    {_render_commits_html(item.get("commits") or extract_commits(item))}
    """
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="/style.css">
  <style>
    html, body {{
      font-family: "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
      margin: 16px;
      background: #fff;
      color: #222;
    }}
    .html-body pre {{ background:#f4f6f8; padding:12px; overflow:auto; }}
    .html-body code {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.92em; }}
    .html-body blockquote {{ border-left: 3px solid #ddd; margin: 0.6em 0; padding-left: 12px; color: #555; }}
    .html-body h1, .html-body h2, .html-body h3 {{ font-size: 1.15em; margin: 0.8em 0 0.4em; }}
  </style>
</head>
<body>{body}</body>
</html>
"""


@bp.get("/api/config")
def get_config():
    try:
        return jsonify(read_config_file())
    except Exception as exc:
        return _json_error(exc)


@bp.put("/api/config")
def put_config():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _json_error(ValueError("請傳入 JSON 物件"), 400)
    try:
        return jsonify(save_config(body))
    except Exception as exc:
        return _json_error(exc)


@bp.get("/api/session")
def get_session():
    return jsonify(_session_payload(_load_ui_session()))


@bp.put("/api/session")
def update_session():
    body = request.get_json(silent=True) or {}
    data = _load_ui_session()
    if body.get("restoreListed"):
        data["working_ids"] = list(data.get("listed_ids") or [])
    if "ids" in body:
        data["working_ids"] = _parse_id_list(body.get("ids"))
        if body.get("listed"):
            data["listed_ids"] = list(data["working_ids"])
    if "currentStep" in body:
        data["current_step"] = max(1, min(PIPELINE_STEP_COUNT, int(body.get("currentStep") or 1)))
    if "reachedStep" in body:
        data["reached_step"] = max(0, min(PIPELINE_STEP_COUNT, int(body.get("reachedStep") or 0)))
    return jsonify(_session_payload(_save_ui_session(data)))


@bp.get("/api/items")
@bp.post("/api/items/query")
def list_items():
    requested = _requested_ids()
    if requested is None:
        requested = _working_ids()
    if not requested:
        return jsonify([])
    _sync_groups_to_listed()
    listed = {int(row["id"]): row for row in _load_listed() if row.get("id") is not None}
    grouped_ids = _grouped_ids()
    return jsonify(
        [_build_item(work_item_id, listed.get(work_item_id), grouped_ids) for work_item_id in requested]
    )


@bp.get("/api/groups")
@bp.post("/api/groups/query")
def list_groups():
    requested = _requested_ids()
    if requested is None:
        requested = _working_ids()
    if not requested:
        return jsonify([])

    _sync_groups_to_listed()
    seen: set[int] = set()
    groups: list[dict[str, Any]] = []

    def add(ids: list[int]) -> None:
        leftover = [work_item_id for work_item_id in ids if work_item_id not in seen]
        if not leftover:
            return
        payload = _group_payload(leftover if leftover != ids else ids)
        groups.append(payload)
        seen.update(payload["ids"])

    if GROUPS_PATH.exists():
        try:
            saved = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            saved = []
        if isinstance(saved, list):
            for row in saved:
                if isinstance(row, dict) and row.get("ids"):
                    add([int(value) for value in row["ids"]])

    if requested is not None:
        keep = set(requested)
        groups = [
            {**group, "ids": [work_item_id for work_item_id in group["ids"] if work_item_id in keep]}
            for group in groups
        ]
        groups = [group for group in groups if group["ids"]]

    groups.sort(key=lambda group: int(group["primary_id"]))
    return jsonify(groups)


@bp.get("/api/items/<int:item_id>")
def get_item(item_id: int):
    report = find_report(item_id)
    if report is None:
        return _json_error(FileNotFoundError("尚未有 Bob 報告，請先跑「Bob 報告」。"), 404)
    return jsonify(report)


@bp.get("/api/items/<int:item_id>/html")
def get_item_html(item_id: int):
    try:
        item = read_work_item(item_id)
    except FileNotFoundError as exc:
        return _json_error(exc, 404)
    try:
        rendered = _render_ado_html(item, item_id)
    except BaseException as exc:  # noqa: BLE001 — catch RecursionError / re.error 等
        work_item_id_str = html.escape(str(item_id))
        title = html.escape(stringify(item.get("title") or f"Work Item {item_id}"))
        error_msg = html.escape(str(exc)[:300])
        rendered = (
            f"<!DOCTYPE html><html lang='zh-Hant'><head><meta charset='utf-8'>"
            f"<style>body{{font-family:sans-serif;margin:16px;color:#222}}"
            f".err{{color:#dc2626;background:#fef2f2;border:1px solid #fecaca;"
            f"border-radius:6px;padding:12px;margin-top:1rem}}</style></head>"
            f"<body><h1>#{work_item_id_str} {title}</h1>"
            f"<div class='err'>⚠ HTML 渲染失敗，無法顯示完整原文。<br>"
            f"<small>{error_msg}</small></div></body></html>"
        )
    return Response(rendered, mimetype="text/html")


@bp.get("/api/items/<int:item_id>/updates")
def get_item_updates(item_id: int):
    try:
        item = read_work_item(item_id)
    except FileNotFoundError as exc:
        return _json_error(exc, 404)
    updates: list[dict[str, Any]] = []
    for entry in item.get("history") or []:
        if not isinstance(entry, dict):
            continue
        fields: dict[str, dict[str, Any]] = {}
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            key = stringify(change.get("field")) or "field"
            fields[key] = {"old": change.get("from"), "new": change.get("to")}
        updates.append(
            {
                "revision": entry.get("rev"),
                "revised_by": stringify(entry.get("by")),
                "revised_date": stringify(entry.get("date")),
                "fields": fields,
            }
        )
    return jsonify(updates)


@bp.put("/api/items/<int:item_id>")
def update_item(item_id: int):
    body = request.get_json(silent=True)
    try:
        report = validate_report(body, source=f"work_item_{item_id}")
    except ValueError as exc:
        return _json_error(exc)
    path, existing = _report_path_for(item_id)
    if path is None:
        JSON_DIR.mkdir(parents=True, exist_ok=True)
        path = JSON_DIR / f"work_item_{item_id}.json"
    # 保留現有 change_history（前端 ReportEditor 不編輯此欄位）
    if existing and "change_history" not in report and "change_history" in existing:
        report["change_history"] = existing["change_history"]  # type: ignore[typeddict-unknown-key]
    try:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return _json_error(exc, 500)
    return jsonify({"ok": True})


UPLOAD_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
UPLOAD_IMAGE_MAX = 10 * 1024 * 1024


@bp.post("/api/items/<int:item_id>/images")
def upload_item_image(item_id: int):
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return _json_error(ValueError("請選擇圖片檔"), 400)
    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in UPLOAD_IMAGE_EXTS:
        return _json_error(ValueError("只接受 png / jpg / gif / webp / bmp"), 400)
    data = uploaded.read()
    if not data:
        return _json_error(ValueError("檔案是空的"), 400)
    if len(data) > UPLOAD_IMAGE_MAX:
        return _json_error(ValueError("圖片不能超過 10MB"), 400)
    media_dir = ADO_DIR / f"work_item_{item_id}_files"
    media_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w.-]+", "_", Path(uploaded.filename).stem, flags=re.UNICODE)[:40] or "image"
    name = f"upload_{uuid.uuid4().hex[:8]}_{stem}{suffix}"
    dest = media_dir / name
    dest.write_bytes(data)
    return jsonify({"src": f"{media_dir.name}/{name}"})


@bp.delete("/api/items")
def delete_items():
    body = request.get_json(silent=True) or {}
    ids = [int(value) for value in (body.get("ids") or [])]
    drop = set(ids)
    deleted: list[int] = []
    for item_id in ids:
        removed = False
        ado_file = ADO_DIR / f"work_item_{item_id}.json"
        if ado_file.exists():
            ado_file.unlink()
            removed = True
        ado_files_dir = ADO_DIR / f"work_item_{item_id}_files"
        if ado_files_dir.exists():
            shutil.rmtree(ado_files_dir)
            removed = True
        report_path, _report = _report_path_for(item_id)
        if report_path is not None and report_path.exists():
            report_path.unlink()
            removed = True
        if removed:
            deleted.append(item_id)
    _remove_listed_ids(drop)
    _remove_ids_from_groups(drop)
    data = _load_ui_session()
    data["working_ids"] = [work_item_id for work_item_id in data.get("working_ids") or [] if work_item_id not in drop]
    data["listed_ids"] = [work_item_id for work_item_id in data.get("listed_ids") or [] if work_item_id not in drop]
    _save_ui_session(data)
    return jsonify({"deleted": deleted or ids})


@bp.post("/api/pipeline/run")
def pipeline_run():
    body = request.get_json(silent=True) or {}
    raw_script = str(body.get("script") or "").strip()
    script = SCRIPT_ALIASES.get(raw_script)
    if script is None:
        allowed = ", ".join(sorted({*STEPS, "main"}))
        return _json_error(ValueError(f"未知步驟：{raw_script}。可用：{allowed}"))
    ids = _parse_id_list(body.get("ids"))
    if not ids:
        ids = _working_ids()
    keep_ids = _parse_id_list(body.get("workingIds")) or ids
    run_ids: list[int] | None = None if script == "list_ids" else (ids or None)

    events: queue.Queue[tuple[str, Any]] = queue.Queue()

    def sink(message: str) -> None:
        if _abort_event.is_set():
            raise RuntimeError("已中止執行")
        events.put(("log", message))

    def worker() -> None:
        global _pipeline_running
        with _pipeline_lock:
            _abort_event.clear()
            _pipeline_running = True
        add_log_sink(sink)
        try:
            if script == "main":
                if not run_ids:
                    raise ValueError("請先在左邊勾選要處理的 ADO。")
                result = run_from("fetch", run_ids)
            else:
                result = run_step(script, run_ids)
            if _abort_event.is_set():
                events.put(("error", "已中止執行"))
                return
            if script == "list_ids" and isinstance(result, list):
                _save_listed(
                    [
                        row
                        if isinstance(row, dict)
                        else {"id": row, "title": "", "work_item_type": "", "state": ""}
                        for row in result
                    ]
                )
            if script == "group" and isinstance(result, list):
                _save_groups(result)
            if script == "main":
                known = _known_item_ids()
                if known:
                    from backend.pipeline.group import group_work_item_ids

                    _save_groups(group_work_item_ids(known))
            events.put(("done", result))
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            events.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001 — 串流給前端看
            events.put(("error", str(exc)))
        finally:
            remove_log_sink(sink)
            with _pipeline_lock:
                _pipeline_running = False
            events.put(("end", None))

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            kind, payload = events.get()
            if kind == "end":
                break
            if kind == "log":
                yield _sse({"type": "log", "line": payload})
            elif kind == "error":
                yield _sse({"type": "error", "message": payload})
            elif kind == "done":
                session_data = _update_session_after_run(script, payload, ids, keep_ids)
                yield _sse(
                    {
                        "type": "done",
                        "refresh": script in REFRESH_SCRIPTS,
                        **_session_payload(session_data),
                    }
                )

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@bp.post("/api/pipeline/abort")
def pipeline_abort():
    with _pipeline_lock:
        if not _pipeline_running:
            return jsonify({"ok": False, "message": "沒有正在執行的腳本"})
        _abort_event.set()
    return jsonify({"ok": True, "message": "已送出中止信號"})


@bp.get("/api/pipeline/download")
def download_word():
    if not DOCX_DIR.exists():
        return _json_error(FileNotFoundError("尚未產出 Word。"), 404)
    docx_files = sorted(DOCX_DIR.glob("report_*.docx"), key=lambda path: path.stat().st_mtime)
    if not docx_files:
        return _json_error(FileNotFoundError("尚未產出 Word。"), 404)
    latest = docx_files[-1]
    return send_from_directory(latest.parent, latest.name, as_attachment=True)


@bp.get("/static/ado/<path:filename>")
def static_ado(filename: str):
    if not ADO_DIR.exists():
        return ("尚未抓取 ADO", 404)
    return send_from_directory(ADO_DIR, filename)


@bp.get("/static/style.css")
def static_style():
    return send_from_directory(STYLE_PATH.parent, STYLE_PATH.name)
