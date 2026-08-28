# ADO_2_WORD 技術棧與功能清單

把 Azure DevOps Work Item 做成測試報告 Word。平常走網頁操作；pipeline 與檔案在後端。

- 啟動：`start-mac.command` / `start-windows.bat`
- 畫面：[http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- 後端 API：[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## 目錄

- [技術棧](#技術棧)
  - [執行環境](#執行環境)
  - [前端](#前端frontend)
  - [後端](#後端backend)
  - [外部服務](#外部服務)
  - [本機產出](#本機產出)
- [架構與流程](#架構與流程)
- [演算法與實作技術](#演算法與實作技術)
  - [圖與分組](#圖與分組)
  - [平行與同步](#平行與同步)
  - [分頁、批次、去重](#分頁批次去重)
  - [正規式與字串處理](#正規式與字串處理)
  - [Markdown／HTML](#markdownhtml)
  - [LLM 與 JSON](#llm-與-json)
  - [歷史推導（線性掃描）](#歷史推導線性掃描)
  - [表格、篩選、勾選](#表格篩選勾選)
  - [統計與圖](#統計與圖)
  - [Word／OOXML](#wordooxml)
  - [認證、傳輸、啟動](#認證傳輸啟動)
- [功能清單](#功能清單)
  - [啟動與設定](#啟動與設定)
  - [載入與清單](#載入與清單)
  - [Pipeline](#pipeline)
  - [ADO 原文：Markdown 渲染與 HTML](#ado-原文markdown-渲染與-html)
  - [測試報告編輯](#測試報告編輯)
  - [分析頁](#分析頁-dashboard)
  - [Word 產出細節](#word-產出細節)
  - [資料解析（給報告與分析用）](#資料解析給報告與分析用)
  - [開發與本機 API](#開發與本機-api)
- [畫面一覽](#畫面一覽)
- [開發歷程（依 commit）](#開發歷程依-commit)
  - [2026-08-18　起步：純 Python Pipeline](#2026-08-18-起步純-python-pipeline)
  - [2026-08-19　搬進 backend，再接上 Vue](#2026-08-19-搬進-backend再接上-vue)
  - [2026-08-20　能自己開、能渲染、能分析](#2026-08-20-能自己開能渲染能分析)
  - [2026-08-21　版本號與大重構](#2026-08-21-版本號與大重構)

---

## 技術棧

### 執行環境

| 項目 | 版本／說明 |
| --- | --- |
| Python | 3.9+（啟動檔會檢查；優先用 3.12） |
| Node.js | 18+ |
| 作業系統 | macOS、Windows（各有啟動腳本） |

啟動檔會檢查 Python／Node 與套件，缺的會幫你裝，然後一次開前後端。視窗請留著；`Ctrl+C` 會一起停。

### 前端（`frontend/`）

| 套件 | 用途 |
| --- | --- |
| Vue 3 | 畫面與組件 |
| TypeScript | 型別 |
| Vite 6 | 開發伺服器（`127.0.0.1:5173`）、打包 |
| Vue Router 4 | `/` 列表、`/dashboard` 分析 |
| Pinia | 項目清單、pipeline 狀態 |
| Axios | 一般 REST |
| `fetch` + SSE | pipeline 長任務串流 log |
| PrimeVue 4（Aura + IBM Blue preset） | DataTable、Dialog、Button、Toast、Confirm 等 |
| PrimeIcons | 圖示 |

開發時 Vite 把 `/api`、`/static`、`/docs`、`/style.css` 轉到 Flask `5000`。前端只透過 HTTP 跟後端說話，不自己抓 ADO、分組、呼叫 Bob、或填 Word。

### 後端（`backend/`）

| 套件 | 用途 |
| --- | --- |
| Flask | REST API、靜態檔、SSE |
| python-docx | 讀寫 Word 範本 |
| lxml | 操作 docx 的 OOXML |
| markdown | 把 ADO 裡的 Markdown 轉成 HTML 預覽 |

Python 標準函式庫：`urllib`（ADO／Bob HTTP）、`concurrent.futures.ThreadPoolExecutor`（平行抓取）、`threading`（Lock／Event／背景執行緒）、`queue.Queue`（SSE 事件）、`base64`（PAT Basic Auth）、`re`（解析）、`json`、`html`、`uuid`、`io.BytesIO`（docx 讀寫）。

協定與格式：HTTP／REST、SSE（`text/event-stream`）、`multipart/form-data`（上傳圖）、JSON、HTML、Markdown、WIQL、OOXML／WordprocessingML（`.docx`）、Basic Auth、OpenAI-compatible Chat Completions。

| 模組 | 職責 |
| --- | --- |
| `app.py` | HTTP 路由 |
| `workspace.py` | 工作區：勾選、步驟、listed／groups |
| `items.py` | 項目列表、刪除、上傳圖片 |
| `ado_preview.py` | ADO 原文 HTML 頁 |
| `pipeline_job.py` | 背景跑 pipeline，SSE 推 log |
| `pipeline/` | fetch → group → report_by_llm → word |
| `pipeline/word/` | 填範本：`oxml.py`、`blocks.py`、`toc.py` |
| `utils/paths.py` | 路徑常數（templates、secrets、output 都在 backend 底下） |
| `utils/report_schema.py` | 報告 JSON 契約；Bob 寫入與畫面儲存都會驗證 |
| `utils/work_item_parser.py` | 解析 ADO JSON、Redmine、關聯、Commit、Markdown／HTML |
| `utils/ado_client.py` | Azure DevOps REST |
| `utils/bob_llm.py` | IBM Bob Inference（OpenAI-compatible chat） |

### 外部服務

| 服務 | 用途 |
| --- | --- |
| Azure DevOps REST | 列出 ID、抓 Work Item、留言、更新歷史、附件、Git commit |
| IBM Bob Inference | `https://api.us-east.bob.ibm.com/inference/v1`，模型 `premium`，用來產生測試報告 JSON |

設定存在本機 `backend/secrets/config.json`（勿提交）：ADO 組織、專案、PAT、Bob API Key。PAT 需要 Work Items 讀取，以及 Code 讀取（補 Commit 作者與訊息）。

### 本機產出

| 路徑 | 內容 |
| --- | --- |
| `backend/output/ado/` | fetch 的 Work Item JSON、附件圖片、`listed.json`、`groups.json`、`ui_session.json` |
| `backend/output/json/` | Bob 報告 JSON（`work_item_*.json`） |
| `backend/output/report_*.docx` | 合併後的 Word；網頁下載後會刪暫存 |
| `backend/templates/參考目標文件.docx` | Word 範本 |
| `backend/templates/llm_prompt.txt` | Bob system prompt |

也可不開網頁、在專案根目錄用 Python 呼叫 `backend.pipeline.run_from`／`run_step`。說明見 `docs/backend-local.md`；HTTP 見 `docs/api.md`。

---

## 架構與流程

前後端分離。網頁右側 4 步：

```
下載資料 → 關聯分組 → 產生報告 → 合併成 Word
```

對應後端：`fetch` → `group` → `report_by_llm` → `word`。

列出 ID 在左上「載入 ID」，不是步驟列的一步。「全流程自動完成」只處理勾選項目，從下載開始。

```
瀏覽器 (Vue, :5173)
    │  HTTP / SSE（Vite proxy）
    ▼
Flask (:5000)
    ├── Azure DevOps
    ├── IBM Bob
    └── backend/output/、templates/
```

---

## 演算法與實作技術

依實際程式羅列，不是紙上規格。

### 圖與分組

- **BFS（廣度優先搜尋）**：關聯分組把 Related Work Item 當成無向圖。從某一 ID 出發，佇列 `pending` + 集合 `seen` 走完所有連到的項目，得到同一連通分量；不要求 Redmine 相同。見 `backend/pipeline/group.py` 的 `related_group()`。
- **連通分量覆蓋**：對尚未處理的 ID 再跑一次 BFS，直到清單都進某一組（`processed` 集合）。
- **關聯邊抽取**：從 relations 網址用正規式抓 `/workItems/(\d+)`。
- **前端組鍵**：`Map<id, Group>`；`groupKey` 用組的 `primary_id`。表格先依組頭欄位排序，組內再依 ID 升冪；`rowspan` 只畫組頭核取方塊。

### 平行與同步

- **執行緒池**：列出摘要 8 worker、fetch 最多 12、單筆 Work Item 內欄位／留言／歷史 3 路並行、圖片與 Git commit 各 6、Bob 報告 8。
- **生產者–消費者**：pipeline 在 daemon thread 跑；log 經 `queue.Queue` 交給 Flask `stream_with_context` 推 SSE。
- **互斥鎖**：`threading.Lock` 保護「是否正在跑」與 `ui_session.json` 寫入。
- **取消**：`threading.Event` 當 abort 旗標；sink 寫 log 時若已中止就丟例外。
- **Flask `threaded=True`**：開發伺服器可同時服務 API 與 SSE。

### 分頁、批次、去重

- **WIQL keyset 分頁**：`WHERE [System.Id] > last_id ORDER BY [System.Id] ASC`，每批最多 20000，避免 offset 漏資料。
- **`$skip` / `$top` 分頁**：Work Item updates，每頁 200。
- **continuationToken 分頁**：留言 API，每頁 200。
- **批次 API**：`wit/workitemsbatch` 一次最多 200 個 ID。
- **去重**：圖片 URL、commit SHA、貼上的 ID（`Set` + 保留出現順序）。

### 正規式與字串處理

- **Redmine**：標題結尾 `(63852)`／`(63852.64178)`；否則留言 `BUG #`／`redmine`。
- **Site**：Area Path 等欄位找 `SIT-1`／`SIT-2` → `US-1`／`US-2`。
- **Git commit**：40 位 SHA、`vstfs:///Git/Commit/…`、網頁 `/_git/…/commit/`。
- **圖片**：HTML `<img src>`、Markdown `![alt](url)`、ADO `:::image source="…"`。
- **Markdown 偵測**：標題、清單、粗體、fence、表格、`:::image`。
- **貼上 ID**：前端 `/\d+/g` 掃出數字。
- **HTML→純文字（給 Bob）**：標籤換成換行／清單符號，長 URL 收成 `[url]`，再截斷（描述 3000、留言 1000 字）。
- **有用留言過濾**：含複測／Pass／Fail／編號步驟才送給 LLM。
- **圖片網址替換**：遠端 URL 換成本機路徑時，**較長 URL 先替**，避免短字串誤傷長網址。

### Markdown／HTML

- Python `markdown`：`extra`（表格、fence 等）、`sane_lists`；純 Markdown 再加 `nl2br`。
- 失敗則退回原始 fragment；整頁渲染再失敗則友善錯誤 HTML。
- 前端 `DOMParser` 改連結（拿掉 `javascript:`／`data:`）、相對路徑改絕對；iframe `sandbox` 預覽。
- 導出用 `Blob` + 臨時 object URL 觸發下載。

### LLM 與 JSON

- Bob：OpenAI-compatible `/chat/completions`，模型 `premium`，`temperature=0`，`max_tokens` 最高 8192。
- 回覆解析：先拆 ` ```json ` fence → `json.loads` → 取最外層 `{…}` → 仍失敗則 **括號配對修復**（掃過字串／跳脫，數未閉合的 `{` `[`，從最後合法位置截斷再補 `]`／`}`）。
- Prompt 用 `lru_cache(maxsize=1)` 讀一次檔。
- 寫入前走 `validate_report`（型別、必填、測項／步驟形狀）。

### 歷史推導（線性掃描）

- 從頭掃 `history`，**最後一次**把狀態改成 Analyze／Develop／Testing 的人 → SA／工程師／測試人員。
- 測試日期：最後一次**離開 Testing**；沒進過 Testing 但已 Done，改用進入 Done 那天。

### 表格、篩選、勾選

- **列篩選**：ID／標題子字串（標題不分大小寫）；類型／狀態／下載／關聯／報告為多選交集。
- **組排序**：比組頭那一列的欄位（字串 `localeCompare`，數字相減），再乘排序方向。
- **表頭全選（三態）**：有篩選時先只選可見列 → 再按選全部 → 再按清空。indeterminate = 有勾但尚未真全選。
- **前置檢查**：依目標步驟用集合差找出缺 fetch／group／report 的 ID。

### 統計與圖

- **頻率表**：`Map<label, count>`，再依次數降冪（次數相同比標籤）。
- **甜甜圈圖**：SVG `stroke-dasharray`；半徑 `15.915` 使圓周約 100，百分比可直接當 dash。`stroke-dashoffset` 累加各切片。
- **長條圖**：寬度 = `value / max(values)`。
- 標題模組：`^\[([^\]]+)\]`，取前 10 名。

### Word／OOXML

- **原型複製**：從範本剪出 `ADO#XXXX` 區塊（`deepcopy` XML），每份報告貼一塊。
- **欄寬比例縮放**：`new = round(old * target / sum)`，最後一欄吃掉四捨五入誤差（dxa 單位、固定版面）。
- **目錄**：掃標題大綱，複製 TOC 列原型，改編號與 `_Toc` bookmark，對到各 Heading。
- **編號空格**：改 numbering part 的 `w:suff=space`，避免 `11ADO#846`。
- **BytesIO 整檔讀寫**，避開 Windows 檔案鎖與中文路徑。
- 字型：Microsoft YaHei、`w:eastAsia=zh-TW`。

### 認證、傳輸、啟動

- ADO PAT：`Authorization: Basic` + Base64(`:` + PAT)（使用者名空白）。
- 設定與 session：本機 JSON；圖片上傳 UUID 檔名，單檔 10MB。
- Word 下載：64KB chunk streaming，傳完 `unlink`。
- Vite 開發 proxy 轉 `/api`、`/static`、`/docs`。
- 啟動檔：檢查 Python／Node 版本、裝套件；等 TCP 5173 可連再開瀏覽器。
- 展示模式（`demo_mode`）：本機虛構 Work Item，不打客戶 ADO。

---

## 功能清單

### 啟動與設定

- **一鍵啟動**：Mac `start-mac.command`、Windows `start-windows.bat`；檢查 Python 3.9+、Node 18+，缺套件會安裝，再同時開 Vite 與 Flask。
- **設定對話框**：ADO 組織、專案、PAT、IBM Bob API Key；PAT／Key 用密碼欄可顯示／隱藏。
- **首次強制設定**：沒有 `config.json` 時會先開設定，不能關掉，存檔才繼續。
- **設定說明**：對話框連到 `/docs/設定說明.docx`。
- **工作階段記憶**：勾選、目前步驟、已完成步驟寫在 `ui_session.json`，重整頁面會還原。

### 載入與清單

- **載入 ID**：可貼編號（如 `841, 842, 845`），向 ADO 撈 Type、State、Title。
- **填入全部 ID**：從專案列出全部 Work Item ID，再按載入。
- **空清單提示**：沒資料時問要不要從 ADO 取得 ID 與 Title。
- **項目表格**：ID、Type、State（色標 Tag）、Title；可排序、列篩選（文字、多選）。
- **關聯組勾選**：Related 合併後同一組共用一個核取方塊（rowspan）；全選／反選。
- **Pipeline 執行中鎖定勾選**，避免跑一半改範圍。
- **只留下勾選項目**：從目前清單拿掉未勾選的（本機檔案不刪）。
- **刪除**：永久刪本機 ADO JSON、附件與報告。
- **狀態欄**：已下載可「查看資料」；關聯分組顯示組成員與 Redmine；已產生報告可「查看結果」。

### Pipeline

- **全流程自動完成**：勾選項目從 fetch 一路到 Word。
- **逐步執行**：下載資料 → 關聯分組 → 產生報告 → 合併成 Word；可上一步。
- **上一步解綁**：從分組退回時可選是否解除已合併的關聯。
- **略過／重做**：已下載或已有報告時，可略過或重新產生。
- **前置檢查**：後面步驟若缺前面產出，會列出缺什麼，可選先補完再繼續。
- **中止執行**：送出中止信號，停止正在跑的步驟。
- **SSE 即時 log**：右側可開「顯示 log」；下載／報告步驟會從 log 解析進度條。
- **Word 下載**：完成後問「是否下載？」；檔名如 `report_20260820_110000.docx`。按「是」由瀏覽器下載，傳完後端刪暫存；按「否」檔留在 `backend/output/`。

各步驟細節：

| 步驟 | 做什麼 |
| --- | --- |
| **下載資料** | 並行抓 Work Item（預設 12 worker）：欄位、留言、更新歷史、附件圖片、關聯 Git commit（作者／訊息需 Code 讀取）。圖片從 HTML、`![alt](url)`、ADO `:::image`、AttachedFile 收集。 |
| **關聯分組** | 從 Related Work Item BFS 合併成一組；網頁寫 `groups.json`。 |
| **產生報告** | 並行（預設 8 worker）把組交給 Bob，產出符合契約的測試報告 JSON。主旨、測試環境、Site、版本、日期、測試人員等由程式補；測項／步驟由 LLM。可從標題或留言抽 Redmine。 |
| **合併成 Word** | 依範本複製 ADO 區塊，填 meta、測項表、步驟與圖片、Commit 表；套 Microsoft YaHei；依實際標題重寫目錄。 |

也可只重產 Word（不跑 Bob）：`run_from("word", [902, 939])`。

### ADO 原文：Markdown 渲染與 HTML

ADO 描述、ReproSteps、留言等可能是 HTML、Markdown，或兩者混用。後端 `render_rich_html` 會：

1. 把 Markdown 圖片 `![alt](url)` 與 ADO `:::image source="…"` 轉成 `<img>`。
2. 偵測 Markdown（標題、清單、粗體、程式碼區塊、表格等）時用 Python `markdown`（`extra`、`sane_lists`；純 Markdown 再加 `nl2br`）。
3. 本機附件改成 `/static/ado/…`，預覽才能顯示圖。
4. 解析失敗則退回原始 fragment 或跳脫純文字，不讓整頁掛掉。

產出是完整 HTML 文件（`GET /api/items/<id>/html`），含自訂／系統欄位、變動歷史、描述、留言、關聯、Commit。

網頁「查看資料」用 iframe（`srcdoc` + sandbox）預覽這份 HTML。

**導出 HTML**：對話框「導出 HTML」下載 `ado_<id>.html`。會把相對路徑改成絕對網址、連結新分頁，離線／另開也可看。

**從 ADO 更新**：單筆重抓該張 Work Item（含圖片與 Commit），預覽立刻刷新。

### 測試報告編輯

「查看結果」開報告對話框：

- 檢視基本資訊、Test Items、Test Steps（含圖）、Commit。
- **編輯／儲存**：改主旨、環境、Site、版本、日期、人員、Redmine、測項、步驟、Commit；儲存走報告 JSON 驗證。
- **新增／刪除**測項、步驟、Commit。
- **上傳步驟圖片**（png／jpeg／gif／webp／bmp，單檔上限 10MB），寫進該組報告。
- **用 Bob 重新生成報告**：依目前 ADO 資料重產該組（會扣 Bobcoins），覆蓋現有內容；執行中不可重產。

報告 JSON 契約（`report_schema`）必填：`ado_id`、`ado_ids`、`ado_subject`、`test_items`、`test_steps`。選填：`redmine_id`、測試環境、Site、版本、日期、測試／審核人員、`commits`。

### 分析頁 `/dashboard`

只讀已載入項目，沒有另開統計 API。

- 統計卡：已下載／清單、Issue／Task、有／無 Redmine、未關閉。
- 甜甜圈圖：類型、Redmine、狀態、Category。
- 長條：建立月份、指派人、創建者、SA（最後改成 Analyze）、工程師（Develop）、測試人員（Testing）、標題模組（`[xxx]`，最多 10）。
- 點卡片、圖例或長條可開該分類清單；可複製 ID；點標題可開 ADO 原文預覽。
- 建立月份、人員、Category 等需本機已下載 ADO JSON。

### Word 產出細節

- 依範本 `ADO#XXXX` 區塊複製，多組報告各一塊。
- Meta 表：ADO 主旨、測試環境、Site、版本號、測試日期、測試人員、審核人員。
- Test Items 表：編號、名稱、測試資料、預期、結果。
- 測試附件：步驟說明當小標，插入步驟圖片。
- Commit 表：SHA、訊息、作者、日期；合併組可加 ADO 欄。
- 標題含 ADO 編號與 Redmine（有的話）；多 ID 由小到大排。
- 目錄依實際 ADO 標題重寫；內文字型 Microsoft YaHei。
- 用位元組讀寫 docx，避開 Windows 檔案鎖與中文路徑問題。

### 資料解析（給報告與分析用）

- **Redmine**：優先標題結尾 `(63852)`／`(63852.64178)`，否則留言裡的 `BUG #`／`redmine`。
- **Site**：從 Area Path 等欄位辨 SIT-1／SIT-2 → `US-1`／`US-2`。
- **SA／工程師／測試人員**：變更歷史裡最後一次把狀態改成 Analyze／Develop／Testing 的人。
- **Git Commit**：ArtifactLink（`vstfs:///Git/Commit/…` 或網頁 commit URL），再向 ADO Git API 補作者與訊息。

### 開發與本機 API

- 列出／載入 ID、讀寫設定與 session、項目 CRUD、單筆 refresh／regenerate、HTML 預覽、上傳圖、分組讀寫與解綁、pipeline SSE、Word 下載、靜態 ADO 附件與 `docs/`。
- Pipeline 別名：`report` = `report_by_llm`；`main` = 指定 ID 全流程（從 fetch 起）。
- CLI 仍有 `list_ids`（會查整個專案）；網頁列出 ID 走「載入 ID」，不要跟右側四步混成同一套編號。

---

## 畫面一覽

| 位置 | 內容 |
| --- | --- |
| 左上 | 載入 ID、只留下勾選、刪除、分析、設定 |
| 左中 | 項目表格（篩選、關聯組、查看資料／結果） |
| 左下 | 可開關的執行 Log |
| 右側 | 全流程、四步驟、進度、上一步／執行／中止、顯示 log |
| 對話框 | 設定、載入 ID、ADO 原文（預覽／導出 HTML／從 ADO 更新）、報告（編輯／重產 Bob） |
| `/dashboard` | 統計與圖表 |

---

## 開發歷程（依 commit）

從 2026-08-18 到 08-21，由 CLI pipeline 變成前後端網頁，中間經過一次把後端拆模組的大重構。下列是實際做過的事，不是每一筆 commit 的逐字紀錄。

### 2026-08-18　起步：純 Python Pipeline

**`4f02c61` 初始提交：ADO → Word 測試報告 Pipeline**

- 專案根目錄腳本：`list_ids` → `fetch` → `group` → `report_by_llm` → `word`。
- Related Work Item 直接合併（不限 Redmine 相同）。
- Redmine 優先從標題結尾抓，沒有才看留言。
- Word：測項表對齊寬度、標題數字加空格、目錄由程式重寫。
- Bob 參數寫死在程式裡；`config` 只需 ADO 與 `bob_api_key`。
- 加入 `AGENTS.md`、`.cursor/skills/ado2word/`。

當時沒有 Vue，預覽是 `templates/` 裡的靜態 HTML。

### 2026-08-19　搬進 backend，再接上 Vue

**`9bab832` 將 Pipeline 移到 backend，並完成預覽與報告欄位**（結構重整）

- 根目錄的 `fetch.py`／`word.py`／`utils/` 整包搬到 `backend/`。
- Flask 可逐步跑 pipeline。
- 報告 JSON 補變動紀錄；測試人員、測試日期改從 Testing 狀態歷史推導。
- 本機 HTML 預覽頁（後來的 `viewer.html`）。

**`f4b24d7` 加入 Vue 前端第一版，並以 Flask API／SSE 接上既有 pipeline**（新前端）

- Vue 3 + Vite + PrimeVue + Pinia。
- 列表、篩選、逐步執行、報告編輯改由畫面操作。
- 後端新增 API（當時集中在 `frontend_api.py`），pipeline log 用 SSE 推到前端。

### 2026-08-20　能自己開、能渲染、能分析

**`8f37a03` 完善前端設定與報告編輯，並加入 Mac／Windows 雙擊啟動腳本**

- 設定對話框（ADO／PAT／Bob Key）；沒有 `config.json` 會先逼你填。
- 報告編輯加強（測項／步驟／上傳圖片）。
- **Markdown 渲染**：偵測 HTML／Markdown／ADO `:::image`，轉成可預覽 HTML。
- `start-mac.command`、`start-windows.bat`／`.ps1`：檢查並安裝 Python、Node 與套件，不再用專案虛擬環境。

**`ef3f1d5` 更新一點前端的部分**

- 關聯組用 rowspan 合併勾選欄。
- 步驟進度條、中止執行。
- Markdown 解析失敗時 fallback，避免整頁掛掉。
- Bob JSON 截斷修復等後端穩定性。

**`ad1c882` HTML 預覽防崩潰**

- 圖片路徑改寫加上 `try/except`（含 `RecursionError`）。
- 渲染失敗回友善錯誤頁，不再 HTTP 500。

**`04ceb70` dashboard**

- 新增 `/dashboard`：類型、狀態、Redmine、人員等統計。

**`bdbe18c` Bug Fix**

- 表格排序 icon 真正會排序。
- 修復報告編輯。
- 上一步會重置後面步驟狀態。

**`ca8455e` commit 紀錄寫入 Word**

- 從 Work Item 關聯抽出 Git commit，補作者／訊息。
- 報告 JSON、編輯畫面、Word 都有 Commit 表。

**`687c4f6` 修復編輯、補 JSON 缺的 key**

- 編輯儲存與型別對齊；報告欄位補齊。

**`8bdfd89` v1.0.0**（第一個版本標）

- 左上「載入 ID」／「填入全部 ID」／刪除。
- ADO 原文「從 ADO 更新」（單筆重抓）。
- 上一步可選擇是否解綁關聯分組。
- 分析入口進 dashboard。

### 2026-08-21　版本號與大重構

**`1e09e7c` v1.1.0**

- 「用 Bob 重新生成報告」（單組重跑 LLM）。
- `templates/`、`secrets`、`output` 收到 `backend/` 底下。
- 補 `docs/api.md`、`docs/backend-local.md`；精簡 README／AGENTS。

**`24839be` v2.0.0**（最大一次重構）

後端拆檔，不再把 API 與檔案處理全塞在 `frontend_api.py`：

| 拆出來的模組 | 職責 |
| --- | --- |
| `app.py` | 只放路由 |
| `workspace.py` | 勾選、步驟、listed／groups |
| `items.py` | 項目列表、刪除、上傳圖 |
| `pipeline_job.py` | SSE 長任務 |
| `ado_preview.py` | ADO 原文 HTML |
| `pipeline/word/` | `oxml.py`／`blocks.py`／`toc.py` |

前端也收斂：拿掉獨立 `DetailView`；載入 ID 拆成 `ImportIdsDialog`；dashboard 圖表拆成 `DonutChart`／`BarList`。新增「只留下勾選項目」、步驟前置檢查、Word 完成後選位置儲存（存完刪暫存）。Windows 啟動改成單一 `.bat`。

**`ae14550` v2.0.1**

- **導出 HTML**（下載 `ado_<id>.html`，相對路徑改絕對網址）。
- ADO 預覽改成自含樣式的完整頁（之後離線也能看）。

**`2219481` v2.0.2 設定說明**

- 設定對話框連到 `/docs/設定說明.docx`；Vite 轉發 `/docs`。

**`72787ef` v2.1.0 更新勾選邏輯**

- 表頭全選分三層：先選目前篩選結果 → 再按選全部 → 再按取消全選。
- Tooltip 說明下一步會做什麼。

**`fe85e28` v2.2.0 更新 UI 主題色及 Icon；啟動檔自動開瀏覽器**

- PrimeVue 改 IBM Blue（`#0F62FE`）；左上 IBM logo。
- Mac／Windows 啟動檔等 5173 就緒後自動開本機畫面。

**`2a2d2f2` v2.2.1 說明文件更新**

- README、API、本地執行說明與 skill 對齊當時行為（例如 Word 下載後刪暫存）。

