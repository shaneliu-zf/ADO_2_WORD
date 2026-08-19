#!/usr/bin/env python3
"""本機預覽＋用 JSON 呼叫 pipeline。"""

from flask import Flask, jsonify, request, send_from_directory

from backend.pipeline import STEPS, run_from, run_step
from backend.utils.paths import ADO_DIR, STYLE_PATH, VIEWER_HTML_PATH
from backend.utils.report_schema import find_report, list_report_ids

app = Flask(__name__)


def _json_error(exc: Exception, status: int = 400):
    return jsonify(error=str(exc)), status


def _run_kwargs() -> tuple[object, bool]:
    body = request.get_json(silent=True)
    no_images = False
    if isinstance(body, dict):
        no_images = bool(body.get("no_images"))
    return body, no_images


@app.post("/api/run")
def api_run():
    body, no_images = _run_kwargs()
    start = "list_ids"
    payload = body
    if isinstance(body, list):
        start = "fetch"
    elif isinstance(body, dict) and ("from" in body or "ids" in body or "groups" in body):
        start = str(body.get("from") or ("fetch" if body.get("ids") or body.get("groups") else "list_ids"))
        if body.get("groups") is not None:
            payload = body["groups"]
        elif body.get("ids") is not None:
            payload = body["ids"]
        else:
            payload = None
    try:
        return jsonify(run_from(start, payload, no_images=no_images))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        return _json_error(exc)


@app.post("/api/<step>")
def api_step(step: str):
    if step not in STEPS:
        return _json_error(ValueError(f"未知步驟：{step}。可用：{', '.join(STEPS)}"), 404)
    body, no_images = _run_kwargs()
    try:
        return jsonify(run_step(step, body, no_images=no_images))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        return _json_error(exc)


@app.get("/api/reports")
def api_reports():
    return jsonify({"ids": list_report_ids()})


@app.get("/api/report/<int:work_item_id>")
def api_report(work_item_id: int):
    report = find_report(work_item_id)
    if report is None:
        return _json_error(FileNotFoundError("尚未有 Bob 報告，請先跑「Bob 報告」。"), 404)
    return jsonify(report)


@app.route("/")
def index():
    return send_from_directory(VIEWER_HTML_PATH.parent, VIEWER_HTML_PATH.name)


@app.route("/style.css")
def style():
    return send_from_directory(STYLE_PATH.parent, STYLE_PATH.name)


@app.route("/<path:filename>")
def ado_file(filename: str):
    if not ADO_DIR.exists():
        return ("尚未抓取 ADO", 404)
    return send_from_directory(ADO_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
