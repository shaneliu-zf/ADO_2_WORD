# ADO → 測試報告 Word

從 Azure DevOps 抓 Issue，整理成測試報告 JSON，再填進 Word 範本。

建議用 `python3 main.py` 一鍵跑全專案；其餘情境用分步 pipe，見下方 [使用](#使用)。

## 流程圖

### 總覽

`python3 main.py` 從 ① 跑到 ⑤，產出 `output/report_*.docx`。

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
HTML 預覽樣板：`templates/work_item.html`、`templates/index.html`、`templates/style.css`  
Bob system prompt：`templates/llm_prompt.txt`

## 檔案結構

```
ADO_2_WORD/
├── main.py                 # 一鍵入口：全專案 list → … → word
├── README.md
├── docs/
│   ├── pipeline.drawio           # Draw.io 原檔
│   └── pipeline-overview.svg     # 匯出的總覽圖
├── scripts/
│   └── export_diagrams.sh        # draw.io → SVG
│
├── # —— Pipeline 步驟 ——
├── list_ids.py             # 1/5 WIQL 列出專案全部 Issue ID
├── fetch.py                # 2/5 從 ADO 抓 Issue → HTML + 圖片
├── group.py                # 3/5 Related + 同 Redmine 分組（不用 Bob）
├── report_by_llm.py               # 4/5 HTML → 報告 JSON（Bob + 規則填 meta）
├── word.py                 # 5/5 JSON → 合併成一份 Word
│
├── utils/                  # 共用工具
│   ├── ado_client.py       # Azure DevOps HTTP API
│   ├── bob_llm.py          # IBM Bob chat／JSON 呼叫
│   ├── pipeline_io.py      # stdin／stdout JSON、階段 log
│   ├── report_schema.py    # 測試報告 JSON 欄位契約
│   ├── work_item_parser.py # 讀／解析 fetch 產出的 HTML（欄位、Redmine、關聯）
│   ├── paths.py            # 路徑常數
│   └── config_io.py        # 讀 secrets/config.json
│
├── templates/
│   ├── 參考目標文件.docx   # Word 範本
│   ├── work_item.html      # 單筆 Issue HTML 樣板
│   ├── index.html          # Issue 目錄 HTML 樣板
│   ├── style.css           # HTML 預覽樣式
│   └── llm_prompt.txt      # Bob 抽出 test_items／test_steps 的 system prompt
├── secrets/
│   ├── config.json.example
│   └── config.json         # 本機機密（勿提交）
└── output/
    ├── html/               # work_item_*.html、*_files/、index.html、style.css
    ├── json/               # work_item_902.json
    └── report_YYYYMMDD_HHMMSS.docx
```



### 檔案說明


| 類型  | 檔案                                                   | 做什麼                                                |
| --- | ---------------------------------------------------- | -------------------------------------------------- |
| 入口  | `main.py`                                            | 全專案一鍵跑 list → fetch → group → report_by_llm → word |
| 步驟  | `list_ids.py`                                        | WIQL 列出專案全部 Issue ID                               |
| 步驟  | `fetch.py`                                           | 抓 ADO、下載圖、存 HTML                                   |
| 步驟  | `group.py`                                           | 讀「關聯」，同 Redmine 才合併                                |
| 步驟  | `report_by_llm.py`                                   | 呼叫 Bob，寫出報告 JSON（**扣 Bobcoins**）                   |
| 步驟  | `word.py`                                            | 把所有報告填進一份 Word                                     |
| 共用  | `utils/ado_client.py`                                | PAT 驗證、API URL、抓 work item／留言                      |
| 共用  | `utils/bob_llm.py`                                   | Bob `chat_completion`／`chat_json`                  |
| 共用  | `utils/pipeline_io.py`                               | 讀寫 pipeline JSON、階段分隔 log                          |
| 共用  | `utils/report_schema.py`                             | 報告欄位定義與讀取時驗證                                       |
| 共用  | `utils/work_item_parser.py`                          | 從 HTML 抽欄位、Redmine、Related ID                      |
| 設定  | `utils/paths.py`／`utils/config_io.py`                | 路徑與設定檔                                             |
| 資源  | `templates/`                                         | Word／HTML／CSS 樣板                                   |
| 資源  | `secrets/`                                           | PAT、Bob key                                        |
| 產出  | `output/html/`、`output/json/`、`output/report_*.docx` | 中間產物與最終 Word                                       |




## 使用

在專案根目錄執行。

### 一鍵完整跑

```bash
python3 main.py
```

WIQL 列出專案全部 Issue，再跑 fetch → group → report_by_llm → word（**會對每一組呼叫 Bob**）。

fetch 不下載圖片：

```bash
python3 main.py --no-images
```



### 分步 pipe

Pipe 串法：`上一步 stdout → 下一步 stdin`，兩邊都是 ID 的 JSON。

#### ① 起（全專案，等同 `main.py`）

不必 `echo`，直接從 `list_ids.py` 開始：

```bash
python3 list_ids.py \
  | python3 fetch.py \
  | python3 group.py \
  | python3 report_by_llm.py \
  | python3 word.py
```



#### ② 起（指定 ID）

第一步前用 `echo` 餵 ID：

```bash
echo '[902, 939]' \
  | python3 fetch.py \
  | python3 group.py \
  | python3 report_by_llm.py \
  | python3 word.py
```



#### ③ 起（HTML 需已在 `output/html/`）

```bash
echo '[902, 939]' \
  | python3 group.py \
  | python3 report_by_llm.py \
  | python3 word.py
```



#### ⑤ 起（JSON 需已在 `output/json/`）

```bash
echo '[902, 939]' | python3 word.py
```

也可以只跑單一步，例如預覽分組：`echo '[902, 939]' | python3 group.py`（結果印在 stderr，stdout 是 `[[902,939],…]`）。

建議先用單筆 ID 試跑 Bob，確認 key 沒問題再跑多筆。

## Pipeline 契約


| 步驟                 | stdin  | stdout                  | 副作用（檔案）                | 用 Bob？            |
| ------------------ | ------ | ----------------------- | ---------------------- | ----------------- |
| `list_ids.py`      | （無）    | `[902, 939, …]`         | 無                      | 否                 |
| `fetch.py`         | ID 陣列  | 成功抓到的 ID                | `output/html/`         | 否                 |
| `group.py`         | ID 陣列  | 分組 `[[902,939],[1329]]` | 無                      | 否                 |
| `report_by_llm.py` | ID 或分組 | 處理完的分組                  | `output/json/`         | **是**             |
| `word.py`          | ID 或分組 | docx 路徑（單一）             | `output/report_*.docx` | 否                 |
| `main.py`          | （無）    | docx 路徑                 | 全專案完整跑                 | report_by_llm 階段會 |


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

1. 讀 HTML「關聯」，找 Related Work Item。
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
| 測試日期    | `System.CreatedDate`                                |
| 測試人員    | `System.CreatedBy`                                  |
| 審核人員    | 空                                                   |
| 測試結果    | `System.State`                                      |
| Redmine | 標題結尾 `(63852.64178)`；標題沒有則不寫 |
| 版本號     | 空（ADO 無穩定欄位）                                        |


**Bob 只整理描述／複測留言**

- `test_items`：測試項目、測試資料、預期結果
- `test_steps`：步驟說明與截圖路徑（`[img:相對路徑]`）
- System prompt 在 `templates/llm_prompt.txt`，可直接編輯後重跑 `report_by_llm.py`



## 注意

- 只有 `report_by_llm.py`（或 `main.py` 跑到 report_by_llm）會扣 Bobcoins。
- 呼叫 Bob 時 User-Agent 必須是 `bobshell`，否則會被 Cloudflare 擋住。
- Word 範本會保留封面、目錄、測試目的，刪掉範例 `ADO#681`，再填入資料。
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

