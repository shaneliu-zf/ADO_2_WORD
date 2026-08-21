#!/usr/bin/env python3
"""Pipeline SSE 長任務。"""

from __future__ import annotations

import json
import queue
import threading
from typing import Any

from flask import Response, stream_with_context

from backend.items import known_item_ids
from backend.pipeline.word import output_docx_name
from backend.pipeline import STEPS, run_from, run_step
from backend.utils.pipeline_io import add_log_sink, remove_log_sink
from backend.workspace import merge_groups, save_groups, save_listed, session_payload, update_session_after_run

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

_pipeline_lock = threading.Lock()
_pipeline_running = False
_abort_event = threading.Event()


def is_running() -> bool:
    return _pipeline_running


def abort() -> tuple[bool, str]:
    with _pipeline_lock:
        if not _pipeline_running:
            return False, "沒有正在執行的腳本"
        _abort_event.set()
    return True, "已送出中止信號"


def resolve_script(raw_script: str) -> str | None:
    return SCRIPT_ALIASES.get(str(raw_script or "").strip())


def allowed_scripts() -> str:
    return ", ".join(sorted({*STEPS, "main"}))


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def start_sse(script: str, ids: list[int]) -> Response:
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
                save_listed(
                    [
                        row
                        if isinstance(row, dict)
                        else {"id": row, "title": "", "work_item_type": "", "state": ""}
                        for row in result
                    ]
                )
            if script == "group" and isinstance(result, list):
                merge_groups(result)
            if script == "main":
                known = known_item_ids()
                if known:
                    from backend.pipeline.group import group_work_item_ids

                    save_groups(group_work_item_ids(known))
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
                session_data = update_session_after_run(script, payload)
                event = {
                    "type": "done",
                    "refresh": script in REFRESH_SCRIPTS,
                    **session_payload(session_data),
                }
                docx = output_docx_name(payload) if script in {"word", "main"} else None
                if docx:
                    event["docx"] = docx
                yield _sse(event)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
