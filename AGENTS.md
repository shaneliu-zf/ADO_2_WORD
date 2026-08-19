# ADO_2_WORD — AI Agent 工作指南

本文件整理這個專案的結構、設計決策與 AI 協作規範，方便接手的 AI 快速上手。

---

## 專案目的

從 Azure DevOps 抓 Issue，透過 IBM Bob 整理成測試報告 JSON，最後填進 Word 範本，產出 `output/report_*.docx`。

---

## Pipeline 架構

```
list_ids → fetch → group → report_by_llm → word
```


| 步驟  | 檔案                                  | stdin  | stdout             | 副作用                    | 用 Bob？ |
| --- | ----------------------------------- | ------ | ------------------ | ---------------------- | ------ |
| 1/5 | `backend/pipeline/list_ids.py`      | —      | `[{id, title, …}, …]` | —                      | 否      |
| 2/5 | `backend/pipeline/fetch.py`         | ID 陣列  | 成功 ID              | `output/ado/`          | 否      |
| 3/5 | `backend/pipeline/group.py`         | ID 陣列  | 分組 `[[id, id], …]` | —                      | 否      |
| 4/5 | `backend/pipeline/report_by_llm.py` | ID 或分組 | 分組                 | `output/json/`         | **是**  |
| 5/5 | `backend/pipeline/word.py`          | ID 或分組 | docx 路徑            | `output/report_*.docx` | 否      |


---



## 重要設計決策（已確認，勿擅改）



### config.json 欄位

`secrets/config.json` 只需要：

- `organization`、`project`、`pat`（ADO）
- `ado_base_url`（預設 `https://dev.azure.com`，可省略）
- `bob_api_key`（必填，用 Inference key）

**以下已移除**，不要加回去：`bob_base_url`、`bob_model`、`bob_team_id`、`bob_instance_id`、`bob_auth_scheme`。  
這些都硬編碼在 `backend/utils/bob_llm.py` 的常數：`BOB_BASE_URL`、`BOB_MODEL`、`BOB_AUTH_SCHEME`、`BOB_USER_AGENT`。

### Redmine 抽取

- **優先**從標題結尾抓，例如 `(63852.64178)` → `63852.64178`。
- 標題沒有，再從**留言**找（`BUG #`、`redmine` 關鍵字）。
- 都沒有 → `redmine_id` 空白 → Word 標題只寫 `ADO#…`，不出現 `Redmine#XXXX`。



### Related ADO 合併（group.py）

- Related Work Item **直接合併**，不管 Redmine 是否相同。
- 用 BFS 收集，確保間接 Related 也會被納入。



### Word 產出（word.py）

- 測試項目表寬度自動縮成與主旨表等寬（`fill_items_table` + `set_tbl_width`）。
- 目錄由程式重寫（`refresh_toc`），不依賴 Word 開啟時自動更新欄位（不設 `updateFields`）。
- 標題編號與文字之間用空格（`ensure_heading_number_space` 設 `suff=space`）。
- 沒有 Redmine 的 ADO 區塊標題格式：`ADO#902`（非 `ADO#902 / Redmine#XXXX`）。

### Fetch 產出

- 存 `output/ado/work_item_{id}.json` 與圖片，**不**再產單筆 HTML。
- JSON 含 `history`：每次更新的操作者、指派、狀態等（Updates API）。
- 預覽用一份 `templates/viewer.html`（fetch 會複製成 `output/ado/index.html`）去讀各個 JSON。
- 不要加回 `templates/work_item.html` 這類逐筆 HTML 樣板。

---



## 協作規範



### 不要加回使用者已刪除的內容

若使用者已刪除某段說明、欄位或功能，**不要補回**。以當前檔案版本為準。



---



## 常用操作



### 只重產 Word（不跑 Bob）

```python
from backend.pipeline import run_from
run_from("word", [902, 939])
```

### 從指定 ID 跑

```python
from backend.pipeline import run_from
run_from("fetch", [902, 939])
```

### 從 ③ 起（ADO JSON 已存在）

```python
from backend.pipeline import run_from
run_from("group", [902, 939])
```

### 從 ⑤ 起（報告 JSON 已存在）

```python
from backend.pipeline import run_from
run_from("word", [902, 939])
```

---



## 查 ADO 沒有 Redmine 的清單

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

