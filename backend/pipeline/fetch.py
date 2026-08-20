#!/usr/bin/env python3
"""從 Azure DevOps 抓取指定 Work Item，存成 JSON 與圖片。"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
import shutil
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.utils.ado_client import auth_header, fetch_comments, fetch_updates, fetch_work_item
from backend.utils.config_io import load_config
from backend.utils.paths import ADO_DIR, STYLE_PATH, VIEWER_HTML_PATH
from backend.utils.pipeline_io import log, log_stage, log_stage_done, normalize_ids, read_pipeline_json, run_pipeline_main, write_pipeline_json
from backend.utils.work_item_parser import RELATED_ID_RE, collect_item_image_urls, stringify

FETCH_WORKERS = 12
IMAGE_WORKERS = 6

# 更新紀錄裡略過雜訊／已在別處保存的大欄位
HISTORY_SKIP_FIELDS = {
    "System.Rev",
    "System.Watermark",
    "System.AuthorizedDate",
    "System.RevisedDate",
    "System.ChangedDate",
    "System.ChangedBy",
    "System.AuthorizedAs",
    "System.PersonId",
    "System.CommentCount",
    "System.History",
    "System.Description",
    "Microsoft.VSTS.TCM.ReproSteps",
    "Microsoft.VSTS.TCM.Steps",
    "Microsoft.VSTS.Common.StateChangeDate",
    "Microsoft.VSTS.Common.ActivatedDate",
    "Microsoft.VSTS.Common.ActivatedBy",
}


def infer_origin(item: dict[str, Any], extra_urls: list[str] | tuple[str, ...] = ()) -> str:
    candidates: list[str] = []
    for rel in item.get("relations") or []:
        if isinstance(rel, dict):
            candidates.append(str(rel.get("url") or ""))
    candidates.extend(extra_urls)
    for url in candidates:
        if url.startswith(("http://", "https://")):
            parsed = urllib.parse.urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def absolutize_media_url(url: str, origin: str) -> str:
    url = html.unescape(url or "").strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith(("http://", "https://", "data:")):
        return url
    if url.startswith("/") and origin:
        return origin.rstrip("/") + url
    return url


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


def download_images(
    item: dict[str, Any],
    authorization: str,
    media_dir: Path,
    skip_download: bool = False,
) -> dict[str, str]:
    raw_urls = collect_item_image_urls(item)
    origin = infer_origin(item, raw_urls)
    resolved: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in raw_urls:
        url = absolutize_media_url(raw, origin)
        if not url or url.startswith("data:") or url in seen:
            continue
        if not url.startswith(("http://", "https://")):
            log(f"  略過無法下載的圖片網址：{raw}")
            continue
        seen.add(url)
        resolved.append((raw, url))
    url_map: dict[str, str] = {}
    if not resolved:
        return url_map

    if not skip_download:
        media_dir.mkdir(parents=True, exist_ok=True)

    pending: list[tuple[str, str, Path, str, str]] = []
    for index, (raw, url) in enumerate(resolved, start=1):
        filename = safe_filename(url, index)
        dest = media_dir / filename
        relative = f"{media_dir.name}/{filename}"
        if dest.exists():
            url_map[url] = relative
            url_map[raw] = relative
            continue
        if skip_download:
            continue
        pending.append((raw, url, dest, relative, filename))

    def download_one(job: tuple[str, str, Path, str, str]) -> tuple[str, str, str, str]:
        raw, url, dest, relative, filename = job
        download_file(url, dest, authorization)
        return raw, url, relative, filename

    if pending:
        workers = min(IMAGE_WORKERS, len(pending))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(download_one, job): job for job in pending}
            for future in as_completed(future_map):
                raw, url, _dest, _relative, filename = future_map[future]
                try:
                    done_raw, done_url, relative, done_name = future.result()
                    url_map[done_url] = relative
                    url_map[done_raw] = relative
                    log(f"  已下載圖片：{done_name}")
                except Exception as exc:
                    log(f"  圖片下載失敗，保留原網址：{url}（{exc}）")
    return url_map


def skip_history_field(key: str) -> bool:
    return key in HISTORY_SKIP_FIELDS or key.startswith("WEF_")


def related_label(rel: dict[str, Any]) -> str:
    name = stringify((rel.get("attributes") or {}).get("name") or rel.get("rel"))
    match = RELATED_ID_RE.search(str(rel.get("url") or ""))
    if match:
        return f"{name} #{match.group(1)}" if name else f"#{match.group(1)}"
    return name or stringify(rel.get("url"))


def simplify_history(updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for update in updates:
        if not isinstance(update, dict):
            continue
        changes: list[dict[str, str]] = []
        for key, delta in (update.get("fields") or {}).items():
            if skip_history_field(key) or not isinstance(delta, dict):
                continue
            old = stringify(delta.get("oldValue"))
            new = stringify(delta.get("newValue"))
            if old == new:
                continue
            changes.append({"field": key, "from": old, "to": new})
        relations = update.get("relations") or {}
        for rel in relations.get("added") or []:
            if isinstance(rel, dict):
                changes.append({"field": "relation", "from": "", "to": related_label(rel)})
        for rel in relations.get("removed") or []:
            if isinstance(rel, dict):
                changes.append({"field": "relation", "from": related_label(rel), "to": ""})
        if not changes:
            continue
        history.append(
            {
                "rev": update.get("rev"),
                "date": update.get("revisedDate") or "",
                "by": stringify(update.get("revisedBy")),
                "changes": changes,
            }
        )
    return history


def simplify(
    work_item: dict[str, Any],
    comments: list[dict[str, Any]],
    updates: list[dict[str, Any]],
) -> dict[str, Any]:
    fields = work_item.get("fields") or {}
    history = simplify_history(updates)
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
                "created_by": stringify(comment.get("createdBy")),
            }
            for comment in comments
        ],
        "comment_count": len(comments),
        "history": history,
        "history_count": len(history),
    }


def save_work_item(item: dict[str, Any], authorization: str, skip_download: bool = False) -> Path:
    work_item_id = item["id"]
    media_dir = ADO_DIR / f"work_item_{work_item_id}_files"
    item["images"] = download_images(item, authorization, media_dir, skip_download=skip_download)
    path = ADO_DIR / f"work_item_{work_item_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def save_index(items: list[dict[str, Any]]) -> Path:
    payload = {
        "items": [
            {
                "id": item["id"],
                "title": stringify(item.get("title")),
                "state": stringify(item.get("state")),
                "work_item_type": stringify(item.get("work_item_type")),
            }
            for item in items
        ]
    }
    path = ADO_DIR / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def copy_viewer() -> None:
    if not VIEWER_HTML_PATH.exists():
        raise FileNotFoundError(f"找不到預覽頁：{VIEWER_HTML_PATH}")
    if not STYLE_PATH.exists():
        raise FileNotFoundError(f"找不到樣式：{STYLE_PATH}")
    shutil.copy2(VIEWER_HTML_PATH, ADO_DIR / "index.html")
    shutil.copy2(STYLE_PATH, ADO_DIR / "style.css")


def fetch_one_work_item(
    work_item_id: int,
    config: dict[str, Any],
    authorization: str,
    fetched_at: str,
    *,
    no_images: bool = False,
) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=3) as pool:
        work_item_f = pool.submit(fetch_work_item, config, authorization, work_item_id)
        comments_f = pool.submit(fetch_comments, config, authorization, work_item_id)
        updates_f = pool.submit(fetch_updates, config, authorization, work_item_id)
        item = simplify(work_item_f.result(), comments_f.result(), updates_f.result())
    item["fetched_at"] = fetched_at
    path = save_work_item(item, authorization, skip_download=no_images)
    return {
        "work_item_id": work_item_id,
        "item": item,
        "path": path,
    }


def run_fetch(work_item_ids: list[int], *, no_images: bool = False) -> list[int]:
    config = load_config()
    log_stage(f"2/5 FETCH  抓取 ADO JSON（{len(work_item_ids)} 筆）")
    authorization = auth_header(config["pat"])
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results_by_id: dict[int, dict[str, Any]] = {}
    ADO_DIR.mkdir(parents=True, exist_ok=True)
    copy_viewer()
    worker_count = min(FETCH_WORKERS, max(1, len(work_item_ids)))
    log(f"使用 {worker_count} 個 worker 平行抓取 …")

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(
                fetch_one_work_item,
                work_item_id,
                config,
                authorization,
                fetched_at,
                no_images=no_images,
            ): work_item_id
            for work_item_id in work_item_ids
        }
        for future in as_completed(future_map):
            outcome = future.result()
            work_item_id = outcome["work_item_id"]
            item = outcome["item"]
            log(f"完成 Work Item {work_item_id}")
            results_by_id[work_item_id] = item
            log(
                f"  標題：{item.get('title')}\n"
                f"  欄位數：{len(item.get('fields') or {})}　留言數：{item['comment_count']}　"
                f"變動：{item.get('history_count') or 0}\n"
                f"  已寫入：{outcome['path']}"
            )

    results = [results_by_id[work_item_id] for work_item_id in work_item_ids if work_item_id in results_by_id]
    index_path = save_index(results)
    log(f"目錄：{index_path}")
    log(f"預覽：{ADO_DIR / 'index.html'}（請用 python3 -m backend.app 開啟）")
    log_stage_done(f"FETCH 完成，成功 {len(results)} 筆")
    return [int(item["id"]) for item in results]


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取 Azure DevOps Work Item 並存成 JSON")
    parser.add_argument("--no-images", action="store_true", help="不下載圖片；若本機已有檔案則沿用")
    args = parser.parse_args()
    write_pipeline_json(run_fetch(normalize_ids(read_pipeline_json()), no_images=args.no_images))


if __name__ == "__main__":
    run_pipeline_main(main)
