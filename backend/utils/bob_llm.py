#!/usr/bin/env python3
"""IBM Bob LLM 呼叫（OpenAI-compatible chat completions）。"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from backend.utils.config_io import load_json_file
from backend.utils.paths import CONFIG_PATH


BOB_BASE_URL = "https://api.us-east.bob.ibm.com/inference/v1"
BOB_MODEL = "premium"
BOB_AUTH_SCHEME = "Apikey"
BOB_USER_AGENT = "bobshell"
PLACEHOLDER_KEYS = {"", "你的 Bob API Key", "YOUR_BOB_API_KEY"}
FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def load_bob_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """從 backend/secrets/config.json（或傳入的 dict）讀取 Bob 設定。"""
    if config is None:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"找不到設定檔：{CONFIG_PATH}\n"
                "請複製 backend/secrets/config.json.example 為 backend/secrets/config.json，再填入 bob_api_key。"
            )
        config = load_json_file(CONFIG_PATH)
    if not isinstance(config, dict):
        raise ValueError(f"{CONFIG_PATH} 必須是 JSON 物件")

    api_key = str(config.get("bob_api_key") or os.environ.get("BOB_API_KEY") or "").strip()
    if not api_key or api_key in PLACEHOLDER_KEYS:
        raise ValueError(
            '請在 backend/secrets/config.json 的 "bob_api_key" 貼上 IBM Bob API key。\n'
            "建議在 Bob 網站申請 Scope 為 Inference 的 key，這樣不必再填 team id。\n"
            "說明：https://bob.ibm.com/docs/ide/account/api-keys"
        )

    return {"bob_api_key": api_key}


def _repair_truncated_json(raw: str) -> str:
    """嘗試補齊被截斷的 JSON：在最後一個完整值後補上缺少的 } 和 ]。"""
    # 找到最後一個合法結尾字元（數字、字串結尾引號、true/false/null、]、}）
    # 策略：直接計算未閉合的 { 和 [ 並補齊
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape = False
    last_good = -1
    for i, ch in enumerate(raw):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            if not in_string:
                last_good = i
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            if ch == '{':
                depth_brace += 1
            else:
                depth_bracket += 1
        elif ch in ('}', ']'):
            if ch == '}':
                depth_brace -= 1
            else:
                depth_bracket -= 1
            last_good = i
        elif ch not in (' ', '\t', '\n', '\r', ',', ':'):
            last_good = i
    if depth_brace <= 0 and depth_bracket <= 0:
        return raw  # 已平衡，不需修補
    # 從 last_good 截斷（捨去後面的殘缺片段），再補閉合括號
    truncated = raw[: last_good + 1].rstrip().rstrip(',')
    truncated += ']' * depth_bracket + '}' * depth_brace
    return truncated


def parse_json_object(text: str) -> dict[str, Any]:
    """從 LLM 回覆中抽出 JSON 物件（可含 ```json fence）。"""
    raw = (text or "").strip()
    fenced = FENCE_RE.search(raw)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError(f"LLM 沒有回傳 JSON：{raw[:400]}") from None
        trimmed = raw[start : end + 1]
        try:
            payload = json.loads(trimmed)
        except json.JSONDecodeError:
            # 第三層：嘗試補齊截斷的括號
            repaired = _repair_truncated_json(raw[start:])
            payload = json.loads(repaired)
    if not isinstance(payload, dict):
        raise ValueError("LLM 回傳的 JSON 必須是物件")
    return payload


def format_http_error(status: int, body: str, url: str) -> str:
    text = (body or "").strip()
    if "cloudflare" in text.lower() or "cf-error" in text.lower() or "you have been blocked" in text.lower():
        return (
            f"Bob API 被 Cloudflare 擋住（HTTP {status}）：{url}\n"
            "這通常是 User-Agent 被 WAF 擋下，不是 API key 無效。"
        )
    snippet = text[:800]
    hint = ""
    if status == 401:
        hint = (
            "\n請確認 backend/secrets/config.json 的 bob_api_key 正確，且申請的是 Inference key。"
            "說明：https://bob.ibm.com/docs/ide/account/api-keys"
        )
    elif status == 403:
        hint = (
            "\n請確認 bob_api_key 為 Inference key 且有權限。"
            "說明：https://bob.ibm.com/docs/ide/account/api-keys"
        )
    return f"Bob API 失敗 HTTP {status}：{url}\n{snippet}{hint}"


def chat_completion(
    messages: list[dict[str, str]],
    *,
    config: dict[str, Any] | None = None,
    model: str | None = None,
    temperature: float = 0,
    max_tokens: int = 4096,
    timeout: int = 120,
) -> str:
    """呼叫 Bob chat/completions，回傳 message content 字串。"""
    cfg = load_bob_config(config)
    url = f"{BOB_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"{BOB_AUTH_SCHEME} {cfg['bob_api_key']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": BOB_USER_AGENT,
    }

    body = {
        "model": model or BOB_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(format_http_error(exc.code, detail, url)) from exc

    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"Bob 沒有回傳內容：{json.dumps(payload, ensure_ascii=False)[:800]}")
    return str(((choices[0].get("message") or {}).get("content")) or "")


def chat_json(
    messages: list[dict[str, str]],
    *,
    config: dict[str, Any] | None = None,
    model: str | None = None,
    temperature: float = 0,
    max_tokens: int = 8192,
    timeout: int = 120,
) -> dict[str, Any]:
    """呼叫 Bob，並把回覆解析成 JSON 物件。"""
    content = chat_completion(
        messages,
        config=config,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return parse_json_object(content)
