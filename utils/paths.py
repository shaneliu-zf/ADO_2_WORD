#!/usr/bin/env python3
"""專案路徑常數。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "secrets" / "config.json"
TEMPLATES_DIR = ROOT / "templates"
STYLE_PATH = TEMPLATES_DIR / "style.css"
WORK_ITEM_HTML_TEMPLATE = TEMPLATES_DIR / "work_item.html"
INDEX_HTML_TEMPLATE = TEMPLATES_DIR / "index.html"
LLM_PROMPT_PATH = TEMPLATES_DIR / "llm_prompt.txt"
TEMPLATE_PATH = TEMPLATES_DIR / "參考目標文件.docx"
OUTPUT_DIR = ROOT / "output"
HTML_DIR = OUTPUT_DIR / "html"
JSON_DIR = OUTPUT_DIR / "json"
DOCX_DIR = OUTPUT_DIR  # 最終 Word 直接放在 output/
