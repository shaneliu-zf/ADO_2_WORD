---
name: ado2word
description: >-
  ADO_2_WORD 專案的 AI 工作指南。涵蓋 Pipeline 結構（list_ids→fetch→group→report_by_llm→word）、
  config.json 欄位規範、Redmine 抽取規則、Word 產出細節、以及「使用者已刪除的內容不要加回去」的協作原則。
  當在這個專案工作、或被問到 config、Redmine、Word 目錄、測試項目表寬度、Bob API 設定等話題時使用。
disable-model-invocation: true
---

# ADO_2_WORD 工作指南

完整細節在 [`AGENTS.md`](../../AGENTS.md)，這裡只列最需要注意的規則。

---

## 協作原則

**使用者已刪除的內容，不要加回去。**

- 編輯前先確認當前檔案版本，不要假設「之前有某段所以要補回」。

---

## config.json 欄位

只保留：`organization`、`project`、`pat`、`ado_base_url`、`bob_api_key`。

---

## Redmine 規則

- **優先**從標題結尾抓，格式 `(63852.64178)`。
- 標題沒有，再從**留言**找（`BUG #`、`redmine` 關鍵字）。
- 都沒有：Word 標題寫 `ADO#902`，不寫 `Redmine#XXXX`。
- Related ADO **直接合併**，不看 Redmine（`group.py`）。

---

## Fetch 產出

- 存 `output/ado/work_item_*.json` 與圖片，不要加回逐筆 HTML 樣板。
- 預覽：`python3 -m backend.app`（一份 HTML 去讀各個 JSON）。

---

## Word 產出重點

| 問題 | 解法 |
|------|------|
| 測試項目表太寬 | `fill_items_table` 傳 `target_width`，縮成與主旨表等寬 |
| 標題數字黏文字 | `ensure_heading_number_space` 設 `suff=space` |
| 目錄自動更新彈窗 | 不設 `updateFields`；目錄已由 `refresh_toc` 直接重寫 |
| 沒有 Redmine 的 ADO 標題格式 | `ado_heading_text` 只有有值才加 `/ Redmine#…` |

---

## 只重產 Word（不跑 Bob）

```python
from backend.pipeline import run_from
run_from("word", [902, 939])
```

---

## 查沒有 Redmine 的 ADO

```bash
python3 - << 'PY'
import json
from pathlib import Path
for path in sorted(Path('output/json').glob('work_item_*.json')):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not str(data.get('redmine_id') or '').strip():
        ids = data.get('ado_ids') or [data.get('ado_id')]
        print(', '.join(f'#{x}' for x in ids), '-', (data.get('ado_subject') or '').splitlines()[0])
PY
```
