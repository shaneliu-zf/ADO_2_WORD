# API 說明

後端在 [http://127.0.0.1:5000/](http://127.0.0.1:5000/)。網頁走 Vite（5173）時，`/api` 與 `/static` 會轉到後端。失敗時多半回 `{"error": "…"}`。

直接用 Python 呼叫 pipeline，見 [本地執行後端程式說明](backend-local.md)。

## Pipeline

用 JSON 跑步驟。全流程從指定 ID 的 `fetch` 開始，不是專案全部。`from` 可以是 `fetch`、`group`、`report_by_llm`、`word`。

```bash
# 全流程：指定 ID，從 fetch 跑到 Word
curl -s -X POST http://127.0.0.1:5000/api/run \
  -H 'Content-Type: application/json' \
  -d '{"from":"fetch","ids":[902,939]}'

# 只跑 fetch
curl -s -X POST http://127.0.0.1:5000/api/fetch \
  -H 'Content-Type: application/json' \
  -d '[902, 939]'

# 列出專案全部 ID
curl -s http://127.0.0.1:5000/api/ado/ids
# {"ids":[902,939,…]}

# 同上，另含標題、類型、狀態
curl -s -X POST http://127.0.0.1:5000/api/list_ids
```

| 方法 | 路徑 | 說明 |
| --- | --- | --- |
| `POST` | `/api/run` | 從指定步驟跑到 Word。body 可為 ID 陣列，或 `{"from","ids","groups"}` |
| `POST` | `/api/<step>` | 只跑單一步。`<step>` 為 `list_ids`、`fetch`、`group`、`report_by_llm`、`word` |
| `GET` | `/api/reports` | 已有報告 JSON 的 ID 列表 |
| `GET` | `/api/report/<id>` | 讀一份報告 JSON |

可加 `"no_images": true`。輸入格式見 [本地執行後端程式說明](backend-local.md#pipeline-步驟)。

## 網頁

Vue 畫面用的 API（`backend/frontend_api.py`）。

| 方法 | 路徑 | 說明 |
| --- | --- | --- |
| `GET` | `/api/config` | 讀設定 |
| `GET` | `/api/config/status` | 設定檔是否存在 |
| `PUT` | `/api/config` | 存設定 |
| `GET` | `/api/session` | 目前勾選與步驟 |
| `PUT` | `/api/session` | 更新勾選／步驟 |
| `GET` | `/api/ado/ids` | 從 Azure DevOps 列出專案全部 ID，回 `{"ids":[…]}` |
| `POST` | `/api/items/summaries` | 載入勾選 ID 的摘要 |
| `GET` | `/api/items` | 目前項目列表 |
| `GET` | `/api/items/<id>` | 報告 JSON |
| `GET` | `/api/items/<id>/html` | ADO 原文 HTML |
| `POST` | `/api/items/<id>/refresh` | 重抓該張 ADO |
| `POST` | `/api/items/<id>/regenerate-report` | 用 Bob 重產該組報告 |
| `PUT` | `/api/items/<id>` | 儲存報告 JSON |
| `POST` | `/api/items/<id>/images` | 上傳圖片（`multipart` 欄位 `file`） |
| `POST` | `/api/items/delete` | 刪除項目（body：`{"ids":[…]}`） |
| `GET` | `/api/groups` | 分組 |
| `DELETE` | `/api/groups` | 解除分組；可傳 `{"ids":[…]}` 只解部分 |
| `POST` | `/api/pipeline/run` | 跑步驟，SSE 串流 log。body：`{"script","ids"}`。`main` 是全流程，只跑傳入的 ID（從 fetch 開始） |
| `POST` | `/api/pipeline/abort` | 中止正在跑的步驟 |
| `GET` | `/api/pipeline/download` | 下載最新一份 `report_*.docx` |
