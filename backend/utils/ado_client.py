#!/usr/bin/env python3
"""Azure DevOps HTTP API 共用函式。"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


WIT_API = "7.1"
COMMENTS_API = "7.1-preview.4"
COMMENTS_PAGE_SIZE = 200
UPDATES_PAGE_SIZE = 200
WORK_ITEMS_BATCH_SIZE = 200


def auth_header(pat: str) -> str:
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def api_url(config: dict[str, Any], *parts: str, query: dict[str, str]) -> str:
    base = str(config.get("ado_base_url") or "https://dev.azure.com").rstrip("/")
    organization = urllib.parse.quote(str(config["organization"]).strip("/"), safe="")
    project = urllib.parse.quote(str(config["project"]).strip(), safe="")
    path = "/".join(str(part).strip("/") for part in parts)
    return f"{base}/{organization}/{project}/_apis/{path}?{urllib.parse.urlencode(query)}"


def request_json(
    url: str,
    authorization: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Authorization": authorization,
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ADO API 失敗 HTTP {exc.code}：{url}\n{detail}") from exc
    return json.loads(body) if body else {}


def fetch_work_item(
    config: dict[str, Any],
    authorization: str,
    work_item_id: int,
) -> dict[str, Any]:
    url = api_url(
        config,
        "wit/workitems",
        str(work_item_id),
        query={"$expand": "all", "api-version": WIT_API},
    )
    return request_json(url, authorization)


def fetch_comments(
    config: dict[str, Any],
    authorization: str,
    work_item_id: int,
) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    continuation: str | None = None
    while True:
        query = {
            "$top": str(COMMENTS_PAGE_SIZE),
            "$expand": "all",
            "order": "asc",
            "api-version": COMMENTS_API,
        }
        if continuation:
            query["continuationToken"] = continuation
        url = api_url(
            config,
            "wit/workItems",
            str(work_item_id),
            "comments",
            query=query,
        )
        payload = request_json(url, authorization)
        comments.extend(payload.get("comments") or [])
        continuation = payload.get("continuationToken")
        if not continuation:
            return comments


def fetch_updates(
    config: dict[str, Any],
    authorization: str,
    work_item_id: int,
) -> list[dict[str, Any]]:
    """抓取 Work Item 每次更新的差異（指派、狀態等）。"""
    updates: list[dict[str, Any]] = []
    skip = 0
    while True:
        url = api_url(
            config,
            "wit/workItems",
            str(work_item_id),
            "updates",
            query={
                "$skip": str(skip),
                "$top": str(UPDATES_PAGE_SIZE),
                "api-version": WIT_API,
            },
        )
        payload = request_json(url, authorization)
        batch = payload if isinstance(payload, list) else (payload.get("value") or [])
        if not batch:
            return updates
        updates.extend(batch)
        if len(batch) < UPDATES_PAGE_SIZE:
            return updates
        skip += len(batch)


def fetch_git_commit(
    config: dict[str, Any],
    authorization: str,
    repository_id: str,
    commit_id: str,
    *,
    project: str | None = None,
) -> dict[str, Any]:
    git_config = config if not project else {**config, "project": project}
    url = api_url(
        git_config,
        "git/repositories",
        repository_id,
        "commits",
        commit_id,
        query={"api-version": WIT_API},
    )
    return request_json(url, authorization)


def fetch_work_items_batch(
    config: dict[str, Any],
    authorization: str,
    work_item_ids: list[int],
    fields: list[str],
) -> list[dict[str, Any]]:
    if not work_item_ids:
        return []
    url = api_url(config, "wit/workitemsbatch", query={"api-version": WIT_API})
    payload = request_json(
        url,
        authorization,
        {"ids": [int(value) for value in work_item_ids], "fields": fields},
    )
    if isinstance(payload, list):
        return payload
    return payload.get("value") or []
