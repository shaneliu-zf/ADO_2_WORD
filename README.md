# ADO → 測試報告 Word

從 Azure DevOps 抓 Issue，整理成測試報告 JSON，再填進 Word 範本。

各步驟用函式或 Flask JSON 呼叫，見下方 [使用](#使用)。

## 流程圖

### 總覽

![Pipeline 總覽](/docs/pipeline-overview.svg)

## 目錄

1. [流程圖](#流程圖)
2. [環境](#環境)
3. [設定](#設定)
4. [檔案結構](#檔案結構)
5. [使用](#使用)
6. [Pipeline 契約](#pipeline-契約)
7. [Related ADO 合併](#related-ado-合併)
8. [Word 產出方式](#word-產出方式)
9. [欄位怎麼來](#欄位怎麼來)
10. [注意](#注意)
11. [Bob LLM 模組](#bob-llm-模組)

## 環境

- Python 3.9+
- 產出 Word 需要：

```bash
python3 -m pip install python-docx
```

## 設定

```bash
cp secrets/config.json.example secrets/config.json
```

`secrets/config.json` 需要：


| 欄位             | 說明                                   |
| -------------- | ------------------------------------ |
| `organization` | ADO 組織                               |
| `project`      | ADO 專案                               |
| `pat`          | Azure DevOps PAT（至少 Work Items Read） |
| `bob_api_key`  | IBM Bob Inference API key            |


Bob key 申請：[https://bob.ibm.com/docs/ide/account/api-keys](https://bob.ibm.com/docs/ide/account/api-keys) ，申請 Inference key。

Word 範本：`templates/參考目標文件.docx`  
預覽頁：`templates/viewer.html`、`templates/style.css`（fetch 會複製到 `output/ado/`）  
Bob system prompt：`templates/llm_prompt.txt`

## 檔案結構

```
ADO_2_WORD/
├── backend/
│   ├── app.py                  # 本機預覽 ＋ POST /api/… 丟 JSON
│   ├── pipeline/               # Pipeline 步驟
│   │   ├── run.py              # run_step／run_from（直接丟 JSON）
│   │   ├── list_ids.py         # 1/5 WIQL 列出專案全部 Work Item
│   │   ├── fetch.py            # 2/5 從 ADO 抓 Issue → JSON + 圖片
│   │   ├── group.py            # 3/5 Related 分組
│   │   ├── report_by_llm.py    # 4/5 ADO JSON → 報告 JSON（Bob）
│   │   └── word.py             # 5/5 報告 JSON → 合併成一份 Word
│   └── utils/                  # 共用工具
│       ├── ado_client.py       # Azure DevOps HTTP API
│       ├── bob_llm.py          # IBM Bob chat／JSON 呼叫
│       ├── pipeline_io.py      # stdin／stdout JSON、階段 log
│       ├── report_schema.py    # 測試報告 JSON 欄位契約
│       ├── work_item_parser.py # 讀／解析 fetch 產出的 ADO JSON
│       ├── paths.py            # 路徑常數
│       └── config_io.py        # 讀 secrets/config.json
├── frontend/                   # SPA 前端（待開發）
├── docs/
│   ├── pipeline.drawio           # Draw.io 原檔
│   └── pipeline-overview.svg     # 匯出的總覽圖
├── scripts/
│   └── export_diagrams.sh        # draw.io → SVG
├── templates/
│   ├── 參考目標文件.docx   # Word 範本
│   ├── viewer.html         # 單一預覽頁（讀 output/ado/*.json）
│   ├── style.css           # 預覽樣式
│   └── llm_prompt.txt      # Bob system prompt
├── secrets/
│   ├── config.json.example
│   └── config.json         # 本機機密（勿提交）
├── requirements.txt
└── output/
    ├── ado/                # work_item_*.json、*_files/、index.json、index.html
    ├── json/               # Bob 報告 JSON（work_item_902.json）
    └── report_YYYYMMDD_HHMMSS.docx
```



### 檔案說明


| 類型  | 檔案                                                   | 做什麼                                                |
| --- | ---------------------------------------------------- | -------------------------------------------------- |
| 步驟  | `backend/pipeline/list_ids.py`                       | 列出專案全部 Work Item（ID、標題、類型、狀態）             |
| 步驟  | `backend/pipeline/fetch.py`                          | 抓 ADO、下載圖、存 JSON                                   |
| 步驟  | `backend/pipeline/group.py`                          | 讀 relations，Related 直接合併                             |
| 步驟  | `backend/pipeline/report_by_llm.py`                  | 呼叫 Bob，寫出報告 JSON（**扣 Bobcoins**）                   |
| 步驟  | `backend/pipeline/word.py`                           | 把所有報告填進一份 Word                                     |
| 共用  | `backend/pipeline/run.py`                            | `run_step`／`run_from`，直接丟 JSON                        |
| 共用  | `backend/utils/ado_client.py`                        | PAT 驗證、API URL、抓 work item／留言                      |
| 共用  | `backend/utils/bob_llm.py`                           | Bob `chat_completion`／`chat_json`                  |
| 共用  | `backend/utils/pipeline_io.py`                       | 讀寫 pipeline JSON、階段分隔 log                          |
| 共用  | `backend/utils/report_schema.py`                     | 報告欄位定義與讀取時驗證                                       |
| 共用  | `backend/utils/work_item_parser.py`                  | 從 ADO JSON 抽欄位、Redmine、Related ID                  |
| 設定  | `backend/utils/paths.py`／`backend/utils/config_io.py` | 路徑與設定檔                                           |
| 資源  | `templates/`                                         | Word／預覽頁／CSS 樣板                                   |
| 資源  | `secrets/`                                           | PAT、Bob key                                        |
| 產出  | `output/ado/`、`output/json/`、`output/report_*.docx` | 中間產物與最終 Word                                       |




## 使用

在專案根目錄執行。先開預覽伺服器（也提供 API）：

```bash
python3 -m backend.app
```

瀏覽器開 http://127.0.0.1:5000/ ：左邊是目前的 ADO，右邊是五個步驟與「下一步」（每次只跑一步、處理勾選的 Issue）。

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

| 從哪步 | 呼叫 |
| --- | --- |
| ① 全專案 | `run_from("list_ids")` |
| ② 指定 ID | `run_from("fetch", [902, 939])` |
| ③ ADO JSON 已在 `output/ado/` | `run_from("group", [902, 939])` |
| ⑤ 報告 JSON 已在 `output/json/` | `run_from("word", [902, 939])` |

建議先用單筆 ID 試跑 Bob，確認 key 沒問題再跑多筆。

### Flask JSON

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

## Pipeline 契約


| 步驟                 | stdin  | stdout                  | 副作用（檔案）                | 用 Bob？            |
| ------------------ | ------ | ----------------------- | ---------------------- | ----------------- |
| `backend/pipeline/list_ids.py`      | （無）    | `[{id, title, work_item_type, state}, …]` | 無                      | 否                 |
| `backend/pipeline/fetch.py`         | ID 陣列  | 成功抓到的 ID                | `output/ado/`          | 否                 |
| `backend/pipeline/group.py`         | ID 陣列  | 分組 `[[902,939],[1329]]` | 無                      | 否                 |
| `backend/pipeline/report_by_llm.py` | ID 或分組 | 處理完的分組                  | `output/json/`         | **是**             |
| `backend/pipeline/word.py`          | ID 或分組 | docx 路徑（單一）             | `output/report_*.docx` | 否                 |


輸入格式：

```json
[902, 939]
```

分組格式（`group` 輸出）：

```json
[[902, 939], [1329]]
```



## Related ADO 合併

`group.py` 規則（不呼叫 Bob）：

1. 讀 ADO JSON 的 `relations`，找 Related Work Item。
2. 兩邊標題抽到**相同且非空**的 Redmine 編號 → 合併。標題沒有 Redmine 則不合併。
3. 合併後 `report_by_llm.py` 只對該組呼叫一次 Bob；JSON 用 `ado_ids` 保留所有 ADO。

例如 `902`、`939` 標題都是 Redmine `63852.64178`：

```json
{
  "ado_id": 902,
  "ado_ids": [902, 939],
  "redmine_id": "63852.64178"
}
```

若只是 Related、但 Redmine 編號不同或抽不到，則不合併。

## Word 產出方式

所有 ADO 合併成**一份** Word，依 ADO 編號由小到大排列，每組一個 ADO 區塊（主旨表＋測試項目＋測試附件）。標題編號由 Word 自動編號延續，因此 `3`、`3.1`、`4`、`4.1` 會自動對齊。標題沒有 Redmine 時，區塊標題只寫 `ADO#…`，目錄一併更新。

檔名為產出當下時間：`report_YYYYMMDD_HHMMSS.docx`，例如 `report_20260817_181230.docx`。

## 欄位怎麼來

**Python 直接填（不經 Bob）**


| 報告欄位    | 來源                                                  |
| ------- | --------------------------------------------------- |
| ADO 主旨  | `System.Title`                                      |
| 測試環境    | 固定 `QAS`                                            |
| Site    | `SIT-1` → `US-1`，`SIT-2` → `US-2`                   |
| 測試日期    | 變更歷史最後一次離開 `Testing` 的日期（多單用「、」分隔） |
| 測試人員    | 變更歷史最後一次把狀態改成 `Testing` 的操作者              |
| 審核人員    | 空                                                   |
| 測試結果    | `System.State`                                      |
| Redmine | 標題結尾 `(63852.64178)`；標題沒有則不寫 |
| 版本號     | 空（ADO 無穩定欄位）                                        |


**Bob 只整理描述／複測留言**

- `test_items`：測試項目、測試資料、預期結果
- `test_steps`：步驟說明與截圖路徑（`[img:相對路徑]`）
- System prompt 在 `templates/llm_prompt.txt`，可直接編輯後重跑 `report_by_llm.py`



## 注意

- 只有 `report_by_llm.py` 會扣 Bobcoins。
- 呼叫 Bob 時 User-Agent 必須是 `bobshell`，否則會被 Cloudflare 擋住。
- Word 範本會保留封面、目錄、測試目的，刪掉範例 `ADO#681`，再填入資料。
- group／Bob 讀 `output/ado/*.json`。預覽用 `python3 -m backend.app`。
- `secrets/config.json` 已列入 `.gitignore`，不要提交 PAT 或 Bob key。



## Bob LLM 模組

之後若要在別的腳本呼叫 Bob：

```python
from utils.bob_llm import chat_completion, chat_json, load_bob_config

config = load_bob_config()

text = chat_completion(
    [{"role": "user", "content": "用一句話說明這張單"}],
    config=config,
)

data = chat_json(
    [
        {"role": "system", "content": "只回傳 JSON"},
        {"role": "user", "content": "..."},
    ],
    config=config,
)
```

