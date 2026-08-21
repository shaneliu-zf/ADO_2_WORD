#!/usr/bin/env python3
"""專案路徑常數。"""

from __future__ import annotations

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DOCS_DIR = PROJECT_ROOT / "docs"
CONFIG_PATH = BACKEND_DIR / "secrets" / "config.json"
TEMPLATES_DIR = BACKEND_DIR / "templates"
STYLE_PATH = TEMPLATES_DIR / "style.css"
LLM_PROMPT_PATH = TEMPLATES_DIR / "llm_prompt.txt"
TEMPLATE_PATH = TEMPLATES_DIR / "參考目標文件.docx"
OUTPUT_DIR = BACKEND_DIR / "output"
ADO_DIR = OUTPUT_DIR / "ado"  # fetch 產出：work_item_*.json、圖片
JSON_DIR = OUTPUT_DIR / "json"
DOCX_DIR = OUTPUT_DIR  # 最終 Word 直接放在 output/
LISTED_PATH = ADO_DIR / "listed.json"
GROUPS_PATH = ADO_DIR / "groups.json"
UI_SESSION_PATH = ADO_DIR / "ui_session.json"

_ADO_JSON_NAME_RE = re.compile(r"^work_item_(\d+)\.json$")


def ado_json_path(work_item_id: int) -> Path:
    return ADO_DIR / f"work_item_{int(work_item_id)}.json"


def ado_files_dir(work_item_id: int) -> Path:
    return ADO_DIR / f"work_item_{int(work_item_id)}_files"


def report_json_path(work_item_id: int) -> Path:
    return JSON_DIR / f"work_item_{int(work_item_id)}.json"


def ado_id_from_json_name(name: str) -> int | None:
    match = _ADO_JSON_NAME_RE.fullmatch(name)
    return int(match.group(1)) if match else None
