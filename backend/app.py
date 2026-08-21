#!/usr/bin/env python3
"""Flask 入口：網頁 API。"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, Response, jsonify, request, send_from_directory

from backend.ado_preview import render_ado_html_or_error
from backend.items import (
    ado_ids_from_report,
    delete_items,
    list_items_for,
    rebuild_report_commits,
    report_group_ids,
    report_path_for,
    save_item_image,
    set_listed_from_ids,
)
from backend.pipeline_job import abort, allowed_scripts, is_running, resolve_script, start_sse
from backend.utils.config_io import read_config_file, save_config
from backend.utils.json_io import write_json
from backend.utils.paths import ADO_DIR, CONFIG_PATH, JSON_DIR, STYLE_PATH, report_json_path
from backend.utils.report_schema import find_report, locate_report, validate_report
from backend.utils.work_item_parser import read_work_item, stringify
from backend.workspace import (
    PIPELINE_STEP_COUNT,
    clear_groups,
    list_groups_for,
    load_listed,
    load_ui_session,
    parse_id_list,
    save_listed,
    save_ui_session,
    session_payload,
    working_ids,
)

app = Flask(__name__, static_folder=None)


def _json_error(exc: Exception, status: int = 400):
    message = str(exc)
    return jsonify(error=message, message=message), status


def _requested_ids() -> list[int] | None:
    query_ids = request.args.get("ids")
    if query_ids not in (None, ""):
        return parse_id_list(query_ids)
    return None


@app.get("/api/config")
def get_config():
    try:
        return jsonify(read_config_file())
    except Exception as exc:
        return _json_error(exc)


@app.get("/api/config/status")
def get_config_status():
    return jsonify({"exists": CONFIG_PATH.exists()})


@app.put("/api/config")
def put_config():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _json_error(ValueError("請傳入 JSON 物件"), 400)
    try:
        return jsonify(save_config(body))
    except Exception as exc:
        return _json_error(exc)


@app.get("/api/session")
def get_session():
    return jsonify(session_payload(load_ui_session()))


@app.get("/api/ado/ids")
def list_ado_ids():
    try:
        from backend.pipeline.list_ids import query_work_item_ids
        from backend.utils.ado_client import auth_header
        from backend.utils.config_io import load_config

        config = load_config()
        ids = query_work_item_ids(config, auth_header(config["pat"]))
        return jsonify({"ids": ids})
    except Exception as exc:  # noqa: BLE001 — Azure DevOps 請求失敗
        return _json_error(exc, 502)


@app.post("/api/items/summaries")
def load_item_summaries():
    body = request.get_json(silent=True) or {}
    ids = parse_id_list(body.get("ids"))
    if not ids:
        return _json_error(ValueError("請傳入至少一個 ID。"))
    try:
        from backend.pipeline.list_ids import load_work_item_summaries
        from backend.utils.ado_client import auth_header
        from backend.utils.config_io import load_config

        config = load_config()
        rows = load_work_item_summaries(config, auth_header(config["pat"]), ids)
        save_listed(rows)
        data = load_ui_session()
        data["working_ids"] = ids
        data["listed_ids"] = ids
        data["selected_ids"] = ids
        save_ui_session(data)
        return jsonify({"ok": True, "count": len(rows)})
    except Exception as exc:  # noqa: BLE001 — Azure DevOps 請求失敗
        return _json_error(exc, 502)


@app.put("/api/session")
def update_session():
    body = request.get_json(silent=True) or {}
    data = load_ui_session()
    if body.get("restoreListed"):
        data["working_ids"] = list(data.get("listed_ids") or [])
    if "ids" in body:
        data["working_ids"] = parse_id_list(body.get("ids"))
        if body.get("listed"):
            data["listed_ids"] = list(data["working_ids"])
            set_listed_from_ids(data["working_ids"])
    if "selectedIds" in body:
        allowed = set(data.get("working_ids") or [])
        data["selected_ids"] = [
            work_item_id
            for work_item_id in parse_id_list(body.get("selectedIds"))
            if work_item_id in allowed
        ]
    else:
        allowed = set(data.get("working_ids") or [])
        data["selected_ids"] = [work_item_id for work_item_id in data.get("selected_ids") or [] if work_item_id in allowed]
    if "currentStep" in body:
        data["current_step"] = max(1, min(PIPELINE_STEP_COUNT, int(body.get("currentStep") or 1)))
    if "reachedStep" in body:
        data["reached_step"] = max(0, min(PIPELINE_STEP_COUNT, int(body.get("reachedStep") or 0)))
    return jsonify(session_payload(save_ui_session(data)))


@app.get("/api/items")
def list_items():
    requested = _requested_ids()
    if requested is None:
        requested = working_ids()
    if not requested:
        return jsonify([])
    return jsonify(list_items_for(requested))


@app.get("/api/groups")
def list_groups():
    requested = _requested_ids()
    if requested is None:
        requested = working_ids()
    if not requested:
        return jsonify([])
    return jsonify(list_groups_for(requested))


@app.delete("/api/groups")
def delete_groups():
    body = request.get_json(silent=True) or {}
    ids = set(parse_id_list(body.get("ids")))
    if not ids:
        return jsonify({"ok": True})
    clear_groups(ids)
    return jsonify({"ok": True})


@app.get("/api/items/<int:item_id>")
def get_item(item_id: int):
    report = find_report(item_id)
    if report is None:
        return _json_error(FileNotFoundError("尚未有 Bob 報告，請先跑「Bob 報告」。"), 404)
    return jsonify(report)


@app.post("/api/items/<int:item_id>/refresh")
def refresh_work_item(item_id: int):
    if is_running():
        return _json_error(RuntimeError("流程正在執行，請稍後再更新。"), 409)
    try:
        from backend.pipeline.fetch import fetch_one_work_item
        from backend.utils.ado_client import auth_header
        from backend.utils.config_io import load_config

        config = load_config()
        authorization = auth_header(config["pat"])
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        outcome = fetch_one_work_item(item_id, config, authorization, fetched_at)
        item = outcome["item"]
        rows = load_listed()
        for row in rows:
            if int(row.get("id") or 0) == item_id:
                row["title"] = stringify(item.get("title"))
                row["work_item_type"] = stringify(item.get("work_item_type"))
                row["state"] = stringify(item.get("state"))
                save_listed(rows)
                break
        found = locate_report(item_id)
        if found is not None:
            path, report = found
            keep = ado_ids_from_report(report) or [item_id]
            report["commits"] = rebuild_report_commits(keep, report.get("commits"))
            write_json(path, report)
        return jsonify({"ok": True})
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        return _json_error(exc)
    except Exception as exc:  # noqa: BLE001 — Azure DevOps 請求失敗
        return _json_error(exc, 502)


@app.post("/api/items/<int:item_id>/regenerate-report")
def regenerate_item_report(item_id: int):
    if is_running():
        return _json_error(RuntimeError("流程正在執行，請稍後再產生報告。"), 409)
    group = report_group_ids(item_id)
    try:
        from backend.pipeline.report_by_llm import process_group
        from backend.utils.bob_llm import load_bob_config

        process_group(group, load_bob_config())
        report = find_report(item_id)
        if report is None:
            return _json_error(FileNotFoundError("重新產生後仍找不到報告。"), 500)
        return jsonify(report)
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        return _json_error(exc)
    except Exception as exc:  # noqa: BLE001 — Bob 請求失敗
        return _json_error(exc, 502)


@app.get("/api/items/<int:item_id>/html")
def get_item_html(item_id: int):
    try:
        item = read_work_item(item_id)
    except FileNotFoundError as exc:
        return _json_error(exc, 404)
    return Response(render_ado_html_or_error(item, item_id), mimetype="text/html")


@app.put("/api/items/<int:item_id>")
def update_item(item_id: int):
    body = request.get_json(silent=True)
    try:
        report = validate_report(body, source=f"work_item_{item_id}")
    except ValueError as exc:
        return _json_error(exc)
    path, _ = report_path_for(item_id)
    if path is None:
        JSON_DIR.mkdir(parents=True, exist_ok=True)
        path = report_json_path(item_id)
    try:
        write_json(path, report)
    except OSError as exc:
        return _json_error(exc, 500)
    return jsonify({"ok": True})


@app.post("/api/items/<int:item_id>/images")
def upload_item_image(item_id: int):
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return _json_error(ValueError("請選擇圖片檔"), 400)
    try:
        return jsonify(save_item_image(item_id, uploaded.filename, uploaded.read()))
    except ValueError as exc:
        return _json_error(exc)


@app.post("/api/items/delete")
def remove_items():
    body = request.get_json(silent=True, force=True) or {}
    ids = parse_id_list(body.get("ids"))
    if not ids:
        ids = parse_id_list(request.args.get("ids"))
    if not ids:
        return _json_error(ValueError("請傳入要刪除的 ID"), 400)
    return jsonify({"deleted": delete_items(ids), "ok": True})


@app.post("/api/pipeline/run")
def pipeline_run():
    body = request.get_json(silent=True) or {}
    raw_script = str(body.get("script") or "").strip()
    script = resolve_script(raw_script)
    if script is None:
        return _json_error(ValueError(f"未知步驟：{raw_script}。可用：{allowed_scripts()}"))
    ids = parse_id_list(body.get("ids"))
    if not ids:
        ids = working_ids()
    return start_sse(script, ids)


@app.post("/api/pipeline/abort")
def pipeline_abort():
    ok, message = abort()
    return jsonify({"ok": ok, "message": message})


@app.get("/api/pipeline/download")
def download_word():
    from backend.pipeline.word import resolve_output_docx

    try:
        path = resolve_output_docx(request.args.get("file"))
    except FileNotFoundError as exc:
        return _json_error(exc, 404)
    except ValueError as exc:
        return _json_error(exc, 400)

    size = path.stat().st_size

    def generate():
        try:
            with path.open("rb") as handle:
                while True:
                    chunk = handle.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    return Response(
        generate(),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{path.name}"',
            "Content-Length": str(size),
        },
    )


@app.get("/static/ado/<path:filename>")
def static_ado(filename: str):
    if not ADO_DIR.exists():
        return ("尚未抓取 ADO", 404)
    return send_from_directory(ADO_DIR, filename)


@app.get("/style.css")
def static_style():
    return send_from_directory(STYLE_PATH.parent, STYLE_PATH.name)


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
