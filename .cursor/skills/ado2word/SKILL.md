---
name: ado2word
description: >-
  Run or debug the ADO_2_WORD pipeline (list_ids, fetch, group, report_by_llm, word),
  regenerate Word without Bob, inspect report JSON, or work on the Vue/Flask app.
  Use when starting the app, rerunning a pipeline step, filling Word, grouping related
  work items, editing reports, or looking up output paths.
---

# ADO_2_WORD 操作

專案介紹與開發規範見根目錄 `AGENTS.md`。這裡只寫怎麼跑 pipeline。

路徑一律 `from backend.utils.paths import …`。

## 啟動

- Mac：`start-mac.command`；Windows：`start-windows.bat`
- 畫面：http://127.0.0.1:5173/
- 沒有 `backend/secrets/config.json` 時，網頁會先開設定再談載入資料

## Pipeline

```
fetch → group → report_by_llm → word
```

網頁右側是 4 步（下載 → 分組 → 報告 → Word）。「全流程自動完成」只處理勾選項目，從下載開始。列出 ID 在左上「載入 ID」，不是步驟列的一步。

| 步驟 | 模組 | 產出 |
| --- | --- | --- |
| fetch | `backend.pipeline.fetch` | `backend/output/ado/` |
| group | `backend.pipeline.group` | 分組 |
| report_by_llm | `backend.pipeline.report_by_llm` | `backend/output/json/`（用 Bob） |
| word | `backend.pipeline.word` | `backend/output/report_*.docx` |

Prompt：`backend/templates/llm_prompt.txt`。

從專案根目錄：

```python
from backend.pipeline import run_from
run_from("fetch", [902, 939])   # 全流程（指定 ID）
run_from("group", [902, 939])   # ADO JSON 已在
run_from("word", [902, 939])    # 只重產 Word，不跑 Bob
```

「關聯分組」上一步會問要不要解綁。「查看結果」可編輯報告（含 Commit），也可「用 Bob 重新生成報告」。

## 查沒有 Redmine 的報告

```bash
python3 - << 'PY'
import json
from pathlib import Path
for path in sorted(Path('backend/output/json').glob('work_item_*.json')):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not str(data.get('redmine_id') or '').strip():
        ids = data.get('ado_ids') or [data.get('ado_id')]
        print(', '.join(f'#{x}' for x in ids), '-', (data.get('ado_subject') or '').splitlines()[0])
PY
```
