# 本地執行後端程式說明

不開網頁、直接在 Python 裡呼叫 pipeline。請在專案根目錄執行（設定檔用 `backend/secrets/config.json`）。

平常開網頁請看 [README](../README.md)；用 HTTP 呼叫見 [API 說明](api.md)。

## 呼叫

全流程對應網頁「全流程自動完成」：只處理指定的 ID（等同勾選項目），從 `fetch` 一路跑到 Word。不會先列出、也不會跑專案全部 Work Item。

```python
from backend.pipeline import run_from, run_step

# 全流程（指定 ID）
run_from("fetch", [902, 939])

# 只跑單一步
run_step("fetch", [902, 939])
run_step("group", [902, 939])
run_step("word", [902, 939])
```

也可傳字串或物件：`"[902, 939]"`、`{"ids": [902, 939]}`、`{"groups": [[902, 939]]}`。

| 從哪步 | 呼叫 |
| --- | --- |
| 指定 ID 全流程 | `run_from("fetch", [902, 939])` |
| ADO JSON 已在 `backend/output/ado/` | `run_from("group", [902, 939])` |
| 報告 JSON 已在 `backend/output/json/` | `run_from("word", [902, 939])` |

`run_from("word", …)` 只重產 Word，不跑 Bob。

只列出專案全部 ID（不會接著跑 fetch）：

```python
rows = run_step("list_ids")  # [{id, title, work_item_type, state}, …]
ids = [row["id"] for row in rows]
```

## Pipeline 步驟

```
fetch → group → report_by_llm → word
```

| 步驟 | 輸入 | 輸出 | 寫入檔案 |
| --- | --- | --- | --- |
| `fetch` | ID 陣列 | 成功抓到的 ID | `backend/output/ado/` |
| `group` | ID 陣列 | 分組 `[[id, id], …]` | — |
| `report_by_llm` | ID 或分組 | 處理完的分組 | `backend/output/json/` |
| `word` | ID 或分組 | docx 路徑（單一） | `backend/output/report_*.docx` |

輸入格式：

```json
[902, 939]
```

分組格式（`group` 輸出）：

```json
[[902, 939], [1329]]
```

主要檔案：`backend/pipeline/` 各步驟、`backend/pipeline/run.py`（`run_step`／`run_from`）。
