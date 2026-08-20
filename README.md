# ADO → 測試報告 Word

把 Azure DevOps 裡的 Issue 做成測試報告 Word。平常只要開網頁操作，不必寫程式。

## 使用

### 1. 啟動

用資料夾裡的啟動檔，它會檢查 Python 3.9+、Node.js 18+ 和套件，缺的會幫你裝，然後一次開好畫面。視窗請留著；要結束時按 `Ctrl+C`，前後端會一起停。

**Mac**

在 Finder 雙擊 `start-mac.command`。若提示沒有執行權限，先在終端機執行一次：

```bash
chmod +x start-mac.command
```

再雙擊，或執行：

```bash
./start-mac.command
```

如果需要輸入密碼請輸入。



**Windows**

在資料夾裡雙擊 `start-windows.bat`。

### 2. 打開畫面

安裝完成後就可以用瀏覽器開 [http://127.0.0.1:5173/](http://127.0.0.1:5173/)。

### 3. 填設定

點畫面左上角齒輪。需要：


| 欄位              | 填什麼                                                               |
| --------------- | ----------------------------------------------------------------- |
| ADO 組織          | Azure DevOps 網址裡的組織名稱                                             |
| ADO 專案          | 專案名稱                                                              |
| PAT             | Azure DevOps 個人存取權杖，至少要有 Work Items 讀取權限                          |
| IBM Bob API Key | [申請 Inference key](https://bob.ibm.com/docs/ide/account/api-keys) |


存檔即可。這些資料只存在你電腦上的 `secrets/config.json`，不要提交到 git。

### 4. 產出 Word

1. 按左上角重新整理，從 Azure DevOps 列出 Issue。
2. 在左邊表格勾選要做成報告的項目。
3. 右邊按「全流程自動完成」，或依步驟按執行（列出 → 下載 → 分組 → 整理報告 → 填 Word）。
4. 完成後，Word 在專案裡的 `output/`，檔名類似 `report_20260820_110000.docx`。

建議先勾 1 筆試跑，確認設定沒問題再勾多筆。

## 流程圖

Pipeline 總覽

## 目錄

1. [使用](#使用)
2. [流程圖](#流程圖)
3. [檔案結構](#檔案結構)
4. [Related ADO 合併](#related-ado-合併)
5. [Word 產出方式](#word-產出方式)
6. [欄位怎麼來](#欄位怎麼來)
7. [後端說明](#後端說明)

## 檔案結構

```
ADO_2_WORD/
├── start-mac.command / start-windows.bat   # 雙擊啟動
├── backend/                                # 後端（抓 ADO、整理、填 Word）
├── frontend/                               # 網頁畫面
├── docs/                                   # 流程圖
├── templates/                              # Word 範本、預覽頁、整理用 prompt
├── secrets/config.json                     # 本機設定（勿提交）
└── output/
    ├── ado/                # 從 ADO 抓下來的 JSON 與圖片
    ├── json/               # 整理後的報告 JSON
    └── report_*.docx       # 最終 Word
```

## Related ADO 合併

`group` 讀已下載的 `output/ado/work_item_*.json`，從每張單的 `relations` 抽出指向其他 Work Item 的連結（網址含 `/workItems/{id}`），用 BFS 往外走：直接連到的、以及再連出去的都會進同一組。不看 Redmine，也不限定關聯類型名稱必須叫 Related。

還沒下載成 JSON 的 ID 會跳過，不會進組。每張單最多只出現在一組。畫面上兩筆以上才標成有關聯；代表 ID 用組內最小編號。

整理報告時一組只跑一次，結果寫成 `output/json/work_item_{最小ID}.json`，`ado_ids` 列出整組。

例如 `902` 的 relations 連到 `939`（或反過來，或再經第三張單連上）：

```json
[[902, 939]]
```

## Word 產出方式

所有勾選的項目合併成**一份** Word，依 ADO 編號由小到大排列。每組一個區塊（主旨表＋測試項目＋測試附件）。標題編號由 Word 自動延續。標題抽不到 Redmine 時，區塊標題只寫 `ADO#…`。

檔名用產出當下時間：`report_YYYYMMDD_HHMMSS.docx`。

## 欄位怎麼來

**直接從 ADO 填**


| 報告欄位    | 來源                                                                   |
| ------- | -------------------------------------------------------------------- |
| ADO 主旨  | `System.Title`                                                       |
| 測試環境    | 固定 `QAS`                                                             |
| Site    | `SIT-1` → `US-1`，`SIT-2` → `US-2`                                    |
| 測試日期    | 離開 `Testing` 的日期；沒進過 Testing 但已 Done 則用進入 Done 那天（多單用「、」分隔，同一天也各列一次） |
| 測試人員    | 變更歷史最後一次把狀態改成 `Testing` 的操作者                                         |
| 審核人員    | 空                                                                    |
| 測試結果    | `System.State`                                                       |
| Redmine | 標題結尾 `(63852.64178)`；標題沒有則不寫                                         |
| 版本號     | 空（ADO 無穩定欄位）                                                         |


**從描述／複測留言整理**

- 測試項目、測試資料、預期結果
- 步驟說明與截圖路徑（`[img:相對路徑]`）
- 整理用文字在 `templates/llm_prompt.txt`，改完後重跑「整理報告」那一步即可

## 後端說明

給要在程式裡呼叫 pipeline、或改後端的人看。網頁操作請看上面的[使用](#使用)。

### 啟動服務

分兩個終端機：

```bash
python3 -m backend.app
```

```bash
cd frontend
npm run dev
```

畫面在 port 5173；後端在 port 5000。Vite 會把 `/api`、`/static` 轉到後端。[http://127.0.0.1:5000/](http://127.0.0.1:5000/) 是原本的預覽頁。

產出 Word 需要 `python-docx`（啟動腳本會裝；手動環境可執行 `python3 -m pip install python-docx`）。

### Python 函式

```python
from backend.pipeline import run_from, run_step

# 從 fetch 一路跑到 Word
run_from("fetch", [902, 939])

# 只跑單一步
run_step("fetch", [902, 939])
run_step("group", [902, 939])
run_step("word", [902, 939])

# 全專案（先 list_ids）
run_from("list_ids")
```

也可傳字串或物件：`"[902, 939]"`、`{"ids": [902, 939]}`、`{"groups": [[902, 939]]}`。


| 從哪步                         | 呼叫                              |
| --------------------------- | ------------------------------- |
| ① 全專案                       | `run_from("list_ids")`          |
| ② 指定 ID                     | `run_from("fetch", [902, 939])` |
| ③ ADO JSON 已在 `output/ado/` | `run_from("group", [902, 939])` |
| ⑤ 報告 JSON 已在 `output/json/` | `run_from("word", [902, 939])`  |


### HTTP API

```bash
# 從 fetch 跑到 Word
curl -s -X POST http://127.0.0.1:5000/api/run \
  -H 'Content-Type: application/json' \
  -d '{"from":"fetch","ids":[902,939]}'

# 只跑 fetch
curl -s -X POST http://127.0.0.1:5000/api/fetch \
  -H 'Content-Type: application/json' \
  -d '[902, 939]'
```

`POST /api/run` 的 `from` 可以是 `list_ids`、`fetch`、`group`、`report_by_llm`、`word`。

### Pipeline 步驟


| 步驟              | 輸入     | 輸出                                        | 寫入檔案                   |
| --------------- | ------ | ----------------------------------------- | ---------------------- |
| `list_ids`      | （無）    | `[{id, title, work_item_type, state}, …]` | 無                      |
| `fetch`         | ID 陣列  | 成功抓到的 ID                                  | `output/ado/`          |
| `group`         | ID 陣列  | 分組 `[[902,939],[1329]]`                   | 無                      |
| `report_by_llm` | ID 或分組 | 處理完的分組                                    | `output/json/`         |
| `word`          | ID 或分組 | docx 路徑（單一）                               | `output/report_*.docx` |


輸入格式：

```json
[902, 939]
```

分組格式（`group` 輸出）：

```json
[[902, 939], [1329]]
```

主要檔案：`backend/pipeline/` 各步驟、`backend/pipeline/run.py`（`run_step`／`run_from`）、`backend/frontend_api.py`（網頁 API）。