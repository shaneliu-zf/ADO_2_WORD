# ADO_2_WORD

把 Azure DevOps Issue 做成測試報告 Word。平常走網頁；pipeline 與檔案在後端。

- 啟動：`start-mac.command` / `start-windows.bat`
- 畫面：[http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- 重跑步驟、查產出：`.cursor/skills/ado2word/`

---

## 架構

前後端分離。


|                          | 職責                                                           |
| ------------------------ | ------------------------------------------------------------ |
| `frontend/`              | Vue + PrimeVue。畫面、狀態、呼叫 API。不要在前端重寫抓 ADO、分組、Bob、填 Word。      |
| `backend/`               | Flask（`app.py` 路由）+ `pipeline/`。工作區檔在 `workspace.py`，項目／報告在 `items.py`。Word 填範本在 `pipeline/word/`。 |
| `backend/utils/paths.py` | 路徑常數。`templates`、`secrets`、`output` 都在 backend 底下，不要加回專案根目錄。 |
| `backend/utils/report_schema.py` | 報告 JSON 契約。Bob 寫入與畫面儲存都會驗證。 |


前端只透過 HTTP 跟後端說話（`frontend/src/api/client.ts`）。

---

## 開發規範

- 改功能先看現有程式，不要假設文件裡有完整規格。
- 使用者已刪的說明、欄位、功能，不要補回。
- `backend/secrets/config.json` 本機專用、勿提交。
- 能小改就小改。不要順手大重構。

---

## 技術債

已知、暫時接受，不要在無關任務裡清掉或再疊一層：

- `app.py` 只放路由。新端點先跟現有風格，不要另開一套平行 API。
- Pipeline 仍有 `list_ids`；網頁列出 ID 走「載入 ID」，右側只有下載 → 分組 → 報告 → Word。兩邊不要硬湊成同一套步驟編號。

