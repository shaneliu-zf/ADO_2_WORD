#!/usr/bin/env python3
"""項目列表、報告檔清理與單筆檔案操作。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import uuid
from typing import Any

from backend.pipeline.report_by_llm import resolve_site
from backend.utils.json_io import read_json_or, write_json
from backend.utils.paths import (
    ADO_DIR,
    JSON_DIR,
    ado_files_dir,
    ado_id_from_json_name,
    ado_json_path,
    report_json_path,
)
from backend.utils.report_schema import locate_report
from backend.utils.work_item_parser import extract_redmine, last_state_actor, read_work_item, stringify
from backend.workspace import (
    grouped_ids,
    load_group_id_lists,
    load_listed,
    remove_ids_from_groups,
    remove_listed_ids,
    save_listed,
    load_ui_session,
    save_ui_session,
    sync_groups_to_listed,
)

UPLOAD_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
UPLOAD_IMAGE_MAX = 10 * 1024 * 1024


def empty_item(work_item_id: int) -> dict[str, Any]:
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


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def ado_ids_from_report(payload: dict[str, Any]) -> list[int]:
    values = payload.get("ado_ids") or [payload.get("ado_id")]
    ids: list[int] = []
    for value in values:
        if value is None:
            continue
        work_item_id = int(value)
        if work_item_id not in ids:
            ids.append(work_item_id)
    return ids


def report_path_for(work_item_id: int):
    found = locate_report(work_item_id)
    if found is None:
        return None, None
    return found


def build_item(
    work_item_id: int,
    listed_row: dict[str, Any] | None = None,
    grouped: set[int] | None = None,
) -> dict[str, Any]:
    item = empty_item(work_item_id)
    item["grouped"] = work_item_id in (grouped or ())
    if listed_row:
        item["title"] = stringify(listed_row.get("title"))
        item["workItemType"] = stringify(listed_row.get("work_item_type") or listed_row.get("workItemType"))
        item["state"] = stringify(listed_row.get("state"))

    ado_path = ado_json_path(work_item_id)
    payload = read_json_or(ado_path, None)
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

    report_path, report = report_path_for(work_item_id)
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


def set_listed_from_ids(ids: list[int]) -> None:
    existing = {int(row["id"]): row for row in load_listed() if row.get("id") is not None}
    rows: list[dict[str, Any]] = []
    for work_item_id in ids:
        row = existing.get(work_item_id)
        if row:
            rows.append(row)
            continue
        built = build_item(work_item_id, None, set())
        rows.append(
            {
                "id": work_item_id,
                "title": built.get("title") or "",
                "work_item_type": built.get("workItemType") or "",
                "state": built.get("state") or "",
            }
        )
    save_listed(rows)


def known_item_ids() -> list[int]:
    ids: set[int] = set()
    for row in load_listed():
        ids.add(int(row["id"]))
    if ADO_DIR.exists():
        for path in ADO_DIR.glob("work_item_*.json"):
            found = ado_id_from_json_name(path.name)
            if found is not None:
                ids.add(found)
    if JSON_DIR.exists():
        for path in JSON_DIR.glob("work_item_*.json"):
            payload = read_json_or(path, None)
            if isinstance(payload, dict):
                ids.update(ado_ids_from_report(payload))
    return sorted(ids)


def list_items_for(requested: list[int]) -> list[dict[str, Any]]:
    sync_groups_to_listed()
    listed = {int(row["id"]): row for row in load_listed() if row.get("id") is not None}
    grouped = grouped_ids()
    return [build_item(work_item_id, listed.get(work_item_id), grouped) for work_item_id in requested]


def report_group_ids(item_id: int) -> list[int]:
    for group in load_group_id_lists():
        if item_id in group:
            return list(group)
    found = locate_report(item_id)
    if found is not None:
        ids = ado_ids_from_report(found[1])
        if ids:
            return ids
    return [item_id]


def _commits_keeping_ids(commits: Any, keep: list[int]) -> list[dict[str, Any]]:
    keep_set = set(keep)
    rows: list[dict[str, Any]] = []
    for entry in commits or []:
        if not isinstance(entry, dict):
            continue
        ado = entry.get("ado_id")
        if ado is not None and int(ado) not in keep_set:
            continue
        row = dict(entry)
        if len(keep) == 1:
            row.pop("ado_id", None)
        rows.append(row)
    return rows


def rebuild_report_commits(keep: list[int], fallback: Any) -> list[dict[str, Any]]:
    from backend.pipeline.report_by_llm import collect_commits

    records: list[dict[str, Any]] = []
    for work_item_id in keep:
        try:
            records.append(read_work_item(work_item_id))
        except FileNotFoundError:
            continue
    if records:
        return list(collect_commits(records))
    return _commits_keeping_ids(fallback, keep)


def prune_reports_for_ids(drop: set[int]) -> None:
    if not drop or not JSON_DIR.exists():
        return
    for path in list(JSON_DIR.glob("work_item_*.json")):
        payload = read_json_or(path, None)
        if not isinstance(payload, dict):
            continue
        ado_ids = ado_ids_from_report(payload)
        named_id = ado_id_from_json_name(path.name)
        if not ado_ids:
            if named_id in drop:
                path.unlink(missing_ok=True)
            continue
        if not drop.intersection(ado_ids):
            continue
        keep = [work_item_id for work_item_id in ado_ids if work_item_id not in drop]
        if not keep:
            path.unlink(missing_ok=True)
            continue
        payload["ado_ids"] = keep
        payload["ado_id"] = min(keep)
        payload["commits"] = rebuild_report_commits(keep, payload.get("commits"))
        dest = report_json_path(int(payload["ado_id"]))
        write_json(dest, payload)
        if dest.resolve() != path.resolve():
            path.unlink(missing_ok=True)


def save_item_image(item_id: int, filename: str, data: bytes) -> dict[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in UPLOAD_IMAGE_EXTS:
        raise ValueError("只接受 png / jpg / gif / webp / bmp")
    if not data:
        raise ValueError("檔案是空的")
    if len(data) > UPLOAD_IMAGE_MAX:
        raise ValueError("圖片不能超過 10MB")
    media_dir = ado_files_dir(item_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w.-]+", "_", Path(filename).stem, flags=re.UNICODE)[:40] or "image"
    name = f"upload_{uuid.uuid4().hex[:8]}_{stem}{suffix}"
    dest = media_dir / name
    dest.write_bytes(data)
    return {"src": f"{media_dir.name}/{name}"}


def delete_items(ids: list[int]) -> list[int]:
    drop = set(ids)
    for item_id in ids:
        ado_file = ado_json_path(item_id)
        if ado_file.exists():
            ado_file.unlink()
        media_dir = ado_files_dir(item_id)
        if media_dir.exists():
            shutil.rmtree(media_dir)
    prune_reports_for_ids(drop)
    remove_listed_ids(drop)
    remove_ids_from_groups(drop)
    data = load_ui_session()
    data["working_ids"] = [work_item_id for work_item_id in data.get("working_ids") or [] if work_item_id not in drop]
    data["listed_ids"] = [work_item_id for work_item_id in data.get("listed_ids") or [] if work_item_id not in drop]
    data["selected_ids"] = [work_item_id for work_item_id in data.get("selected_ids") or [] if work_item_id not in drop]
    save_ui_session(data)
    return ids
