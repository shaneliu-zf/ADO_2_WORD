# API 說明

後端在 [http://127.0.0.1:5000/](http://127.0.0.1:5000/)。網頁走 Vite（5173）時，`/api`、`/static`、`/docs` 與 `/style.css` 會轉到後端。失敗時多半回 `{"error": "…"}`。

不開網頁、直接用 Python 跑 pipeline，見 [本地執行後端程式說明](backend-local.md)。

## 網頁

Vue 畫面用的 API（`backend/app.py`）。

| 方法 | 路徑 | 說明 |
| --- | --- | --- |
| `GET` | `/api/config` | 讀設定 |
| `GET` | `/api/config/status` | 設定檔是否存在；另回 `demo_mode` |
| `PUT` | `/api/config` | 存設定 |
| `GET` | `/api/session` | 目前勾選與步驟 |
| `PUT` | `/api/session` | 更新勾選／步驟。可傳 `ids`、`selectedIds`、`currentStep`、`reachedStep`、`listed`、`restoreListed` |
| `GET` | `/api/ado/ids` | 從 Azure DevOps 列出專案全部 ID，回 `{"ids":[…]}` |
| `POST` | `/api/items/summaries` | 載入勾選 ID 的摘要（網頁「載入 ID」） |
| `GET` | `/api/items` | 目前項目列表；可帶 `?ids=` |
| `GET` | `/api/items/<id>` | 報告 JSON |
| `GET` | `/api/items/<id>/html` | ADO 原文 HTML |
| `POST` | `/api/items/<id>/refresh` | 重抓該張 ADO |
| `POST` | `/api/items/<id>/regenerate-report` | 用 Bob 重產該組報告 |
| `PUT` | `/api/items/<id>` | 儲存報告 JSON（會驗證欄位與測項／步驟形狀） |
| `POST` | `/api/items/<id>/images` | 上傳圖片（`multipart` 欄位 `file`） |
| `POST` | `/api/items/delete` | 刪除項目（body：`{"ids":[…]}`） |
| `GET` | `/api/groups` | 分組；可帶 `?ids=` |
| `DELETE` | `/api/groups` | 解除分組；可傳 `{"ids":[…]}` 只解部分 |
| `POST` | `/api/pipeline/run` | 跑步驟，SSE 串流 log。body：`{"script","ids"}`。`script` 可用 `fetch`／`group`／`report`（=`report_by_llm`）／`word`／`main`；`main` 是全流程，只跑傳入的 ID（從 fetch 開始）。沒傳 `ids` 時用目前工作區 ID（`main` 除外，一定要有 ID）。事件：`log`／`error`／`done`（`done` 可帶 session 與 `docx`） |
| `POST` | `/api/pipeline/abort` | 中止正在跑的步驟 |
| `GET` | `/api/pipeline/download` | 下載剛產出的 `report_*.docx`（可帶 `?file=`）。傳完後後端會刪檔 |
| `GET` | `/docs/<filename>` | 提供 `docs/` 檔案（例如設定說明） |
| `GET` | `/static/ado/<path>` | 本機 ADO 附件（圖片等） |
