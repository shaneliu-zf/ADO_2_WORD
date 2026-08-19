#!/usr/bin/env python3
"""專案路徑常數。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "secrets" / "config.json"
TEMPLATES_DIR = ROOT / "templates"
STYLE_PATH = TEMPLATES_DIR / "style.css"
VIEWER_HTML_PATH = TEMPLATES_DIR / "viewer.html"
LLM_PROMPT_PATH = TEMPLATES_DIR / "llm_prompt.txt"
TEMPLATE_PATH = TEMPLATES_DIR / "參考目標文件.docx"
OUTPUT_DIR = ROOT / "output"
ADO_DIR = OUTPUT_DIR / "ado"  # fetch 產出：work_item_*.json、圖片、預覽頁
JSON_DIR = OUTPUT_DIR / "json"
DOCX_DIR = OUTPUT_DIR  # 最終 Word 直接放在 output/
