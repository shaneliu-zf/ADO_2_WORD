#!/usr/bin/env python3
"""虛構 WMS 專案 LumenWMS 的 ADO 假資料（與客戶環境無關）。"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from backend.demo.images import DEMO_IMAGE_SPECS, write_demo_images
from backend.demo.template import build_demo_template
from backend.utils.paths import DEMO_FILES_DIR, DEMO_TEMPLATE_PATH

ORG = "demo-org"
PROJECT = "LumenWMS"
ORIGIN = f"https://dev.azure.com/{ORG}"
PROJECT_ID = "33333333-dddd-eeee-ffff-444444444444"
REPO_ID = "11111111-aaaa-bbbb-cccc-222222222222"

MEI = {"displayName": "林雅婷", "uniqueName": "mei.lin@example.com"}
KEN = {"displayName": "陳建宏", "uniqueName": "ken.chen@example.com"}
AVA = {"displayName": "王詩涵", "uniqueName": "ava.wang@example.com"}
WEI = {"displayName": "張志偉", "uniqueName": "wei.chang@example.com"}
YU = {"displayName": "黃冠宇", "uniqueName": "yu.huang@example.com"}

IMAGE_GUIDS = {
    "print_error.png": "aaaaaaaa-0001-4000-8000-000000000001",
    "label_preview.png": "aaaaaaaa-0002-4000-8000-000000000002",
    "inventory_count.png": "aaaaaaaa-0003-4000-8000-000000000003",
    "excel_columns.png": "aaaaaaaa-0004-4000-8000-000000000004",
    "scan_fail.png": "aaaaaaaa-0005-4000-8000-000000000005",
    "permission_dialog.png": "aaaaaaaa-0006-4000-8000-000000000006",
}


def attachment_url(filename: str) -> str:
    guid = IMAGE_GUIDS[filename]
    return f"{ORIGIN}/_apis/wit/attachments/{guid}?fileName={filename}"


def work_item_url(work_item_id: int) -> str:
    return f"{ORIGIN}/{PROJECT}/_apis/wit/workItems/{work_item_id}"


def img_tag(filename: str) -> str:
    return f'<img src="{attachment_url(filename)}">'


def git_vstfs(sha: str) -> str:
    return f"vstfs:///Git/Commit/{PROJECT_ID}/{REPO_ID}/{sha}"


def person_block(person: dict[str, str]) -> dict[str, str]:
    return {"displayName": person["displayName"], "uniqueName": person["uniqueName"]}


def _html(*parts: str) -> str:
    return "<div>" + "".join(parts) + "</div>"


def _p(text: str) -> str:
    return f"<p>{text}</p>"


def _b(label: str) -> str:
    return f"<p><b>{label}</b></p>"


def _ol(*items: str) -> str:
    return "<ol>" + "".join(f"<li>{item}</li>" for item in items) + "</ol>"


def _history(rev: int, date: str, by: dict[str, str], field: str, old: str, new: str) -> dict[str, Any]:
    return {
        "rev": rev,
        "revisedDate": date,
        "revisedBy": person_block(by),
        "fields": {field: {"oldValue": old, "newValue": new}},
    }


def _related(work_item_id: int) -> dict[str, Any]:
    return {
        "rel": "System.LinkTypes.Related",
        "url": work_item_url(work_item_id),
        "attributes": {"name": "Related"},
    }


def _attached(filename: str) -> dict[str, Any]:
    return {
        "rel": "AttachedFile",
        "url": attachment_url(filename),
        "attributes": {"name": filename},
    }


def _commit_rel(sha: str, message: str, date: str) -> dict[str, Any]:
    return {
        "rel": "ArtifactLink",
        "url": git_vstfs(sha),
        "attributes": {
            "name": "Fixed in Commit",
            "comment": message,
            "resourceCreatedDate": date,
        },
    }


def _comment(comment_id: int, text: str, date: str, by: dict[str, str]) -> dict[str, Any]:
    return {
        "id": comment_id,
        "text": text,
        "createdDate": date,
        "createdBy": person_block(by),
    }


def _item(
    *,
    work_item_id: int,
    work_item_type: str,
    title: str,
    state: str,
    area: str,
    assigned: dict[str, str],
    created: dict[str, str],
    created_date: str,
    changed_date: str,
    category: str,
    program: str,
    description: str,
    comments: list[dict[str, Any]],
    updates: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "System.Id": work_item_id,
        "System.WorkItemType": work_item_type,
        "System.Title": title,
        "System.State": state,
        "System.AssignedTo": person_block(assigned),
        "System.CreatedBy": person_block(created),
        "System.CreatedDate": created_date,
        "System.ChangedBy": person_block(assigned),
        "System.ChangedDate": changed_date,
        "System.AreaPath": f"{PROJECT}\\{area}",
        "System.AreaLevel2": area,
        "System.NodeName": area,
        "System.IterationPath": f"{PROJECT}\\Sprint 18",
        "System.Tags": "",
        "System.Description": description,
        "Custom.Category": category,
        "Custom.Program": program,
        "Custom.Systems": "LumenWMS",
        "Custom.IssuePriority": "High" if state in {"Done", "Testing"} else "Medium",
        "Custom.Case": "",
        "Custom.Step": "",
        "Custom.Tag": "",
        "Custom.PrimaryCause": "",
        "Custom.Solution": "",
    }
    if extra_fields:
        fields.update(extra_fields)
    return {
        "id": work_item_id,
        "rev": 8,
        "fields": fields,
        "relations": relations,
        "comments": comments,
        "updates": updates,
    }


SHA_LABEL = "a1b2c3d4e5f6789012345678901234567890abcd"
SHA_PERM = "b2c3d4e5f6789012345678901234567890abcde1"
SHA_EXCEL = "c3d4e5f6789012345678901234567890abcdef12"

COMMITS: dict[str, dict[str, Any]] = {
    SHA_LABEL: {
        "comment": "fix: restore default shipping label template",
        "author": {"name": KEN["displayName"], "date": "2026-03-28T04:12:00Z"},
        "remoteUrl": f"{ORIGIN}/{PROJECT}/_git/lumen-wms/commit/{SHA_LABEL}",
    },
    SHA_PERM: {
        "comment": "fix: persist role permissions after save",
        "author": {"name": KEN["displayName"], "date": "2026-04-08T09:40:00Z"},
        "remoteUrl": f"{ORIGIN}/{PROJECT}/_git/lumen-wms/commit/{SHA_PERM}",
    },
    SHA_EXCEL: {
        "comment": "fix: align export columns with report header",
        "author": {"name": KEN["displayName"], "date": "2026-04-15T02:18:00Z"},
        "remoteUrl": f"{ORIGIN}/{PROJECT}/_git/lumen-wms/commit/{SHA_EXCEL}",
    },
}


def _flow(*steps: tuple[str, dict[str, str], str, str]) -> list[dict[str, Any]]:
    updates = []
    for index, (date, by, old, new) in enumerate(steps, start=2):
        updates.append(_history(index, date, by, "System.State", old, new))
    return updates


ITEMS: dict[int, dict[str, Any]] = {
    8401: _item(
        work_item_id=8401,
        work_item_type="Issue",
        title="[Shipping] 出貨單無法列印物流標籤 (64001)",
        state="Done",
        area="SIT1",
        assigned=MEI,
        created=WEI,
        created_date="2026-03-12T02:10:00Z",
        changed_date="2026-03-30T08:00:00Z",
        category="Bug",
        program="Shipping",
        extra_fields={
            "Custom.PrimaryCause": "標籤服務在宅配通路回傳空範本",
            "Custom.Solution": "補上預設標籤範本並加上空值檢查",
            "Custom.Step": "出貨作業",
        },
        description=_html(
            _b("Issue"),
            _p("出貨作業按下「列印標籤」後畫面出現錯誤，標籤機沒有出紙。宅配通路較容易重現。"),
            _b("Expected Result"),
            _p("應依出貨單帶出物流標籤並送列印。"),
            _b("Retro Steps"),
            _ol("開啟出貨單 SO-20260312-018", "選擇宅配並按下去列印標籤", "觀察預覽與實體列印"),
            _p("測試資料：MO: 000010031510、USN: USN8401001、CSN: CSN-8401"),
            img_tag("print_error.png"),
        ),
        comments=[
            _comment(
                11,
                _html(
                    _p("Step 1: 用 SO-20260312-018 重現，錯誤訊息為 template not found。"),
                    _p("Step 2: 套用修正後複測，標籤可預覽並送印。測試 OK。"),
                    img_tag("label_preview.png"),
                ),
                "2026-03-29T03:20:00Z",
                MEI,
            ),
            _comment(12, "<p>Redmine 64001 已同步關閉。</p>", "2026-03-30T01:10:00Z", AVA),
        ],
        updates=_flow(
            ("2026-03-13T01:00:00Z", AVA, "New", "Analyze"),
            ("2026-03-18T06:30:00Z", KEN, "Analyze", "Develop"),
            ("2026-03-28T05:00:00Z", MEI, "Develop", "Testing"),
            ("2026-03-30T08:00:00Z", MEI, "Testing", "Done"),
        ),
        relations=[
            _related(8402),
            _attached("print_error.png"),
            _attached("label_preview.png"),
            _commit_rel(SHA_LABEL, "fix: restore default shipping label template", "2026-03-28T04:12:00Z"),
        ],
    ),
    8402: _item(
        work_item_id=8402,
        work_item_type="Issue",
        title="[Shipping] 標籤預覽畫面空白",
        state="Done",
        area="SIT1",
        assigned=MEI,
        created=WEI,
        created_date="2026-03-12T02:40:00Z",
        changed_date="2026-03-30T08:05:00Z",
        category="Bug",
        program="Shipping",
        extra_fields={"Custom.PrimaryCause": "與 8401 同一空範本", "Custom.Solution": "共用修正"},
        description=_html(
            _b("Issue"),
            _p("列印前的預覽視窗是空白，沒有標籤內容。與無法列印同一條路徑。"),
            _b("Expected Result"),
            _p("預覽應顯示收件人、條碼與出貨單號。"),
            _p("測試資料：MO: 000010031510"),
        ),
        comments=[
            _comment(21, "<p>Step 1: 與 8401 一併複測。測試通過。</p>", "2026-03-29T03:40:00Z", MEI),
        ],
        updates=_flow(
            ("2026-03-13T01:05:00Z", AVA, "New", "Analyze"),
            ("2026-03-18T06:35:00Z", KEN, "Analyze", "Develop"),
            ("2026-03-28T05:05:00Z", MEI, "Develop", "Testing"),
            ("2026-03-30T08:05:00Z", MEI, "Testing", "Done"),
        ),
        relations=[_related(8401)],
    ),
    8410: _item(
        work_item_id=8410,
        work_item_type="Issue",
        title="[Inventory] 盤點數量加總與實際不符 (64012)",
        state="Testing",
        area="SIT2",
        assigned=MEI,
        created=YU,
        created_date="2026-04-02T01:15:00Z",
        changed_date="2026-04-20T04:00:00Z",
        category="Bug",
        program="Inventory",
        extra_fields={"Custom.PrimaryCause": "小數庫存四捨五入後再加總", "Custom.Step": "盤點作業"},
        description=_html(
            _b("Issue"),
            _p("倉庫盤點單合計與各儲位加總差 2 件，A 區儲位有小數數量時較明顯。"),
            _b("Expected Result"),
            _p("盤點合計應等於各儲位數量加總，小數位依設定顯示。"),
            _b("Retro Steps"),
            _ol("開啟盤點單 IC-20260402-004", "匯入 A 區儲位", "比對合計與明細"),
            _p("測試資料：MO: 000010040211、CPN: CPN-INV-004"),
            img_tag("inventory_count.png"),
        ),
        comments=[
            _comment(
                31,
                _html(_p("Step 1: 已可重現差 2 件。"), _p("Step 2: 修正後進行複測。")),
                "2026-04-20T03:50:00Z",
                MEI,
            ),
        ],
        updates=_flow(
            ("2026-04-03T02:00:00Z", AVA, "New", "Analyze"),
            ("2026-04-10T07:20:00Z", KEN, "Analyze", "Develop"),
            ("2026-04-20T04:00:00Z", MEI, "Develop", "Testing"),
        ),
        relations=[_attached("inventory_count.png")],
    ),
    8415: _item(
        work_item_id=8415,
        work_item_type="Task",
        title="[Order] 批次匯入訂單支援 CSV",
        state="Develop",
        area="SIT1",
        assigned=KEN,
        created=AVA,
        created_date="2026-04-05T08:00:00Z",
        changed_date="2026-04-18T09:10:00Z",
        category="Enhance",
        program="Order",
        extra_fields={"Custom.IssuePriority": "Medium"},
        description=_html(
            _b("Issue"),
            _p("客服希望能用 CSV 一次匯入多筆訂單，不必逐筆建檔。"),
            _b("Expected Result"),
            _p("上傳符合欄位的 CSV 後建立訂單，並列出成功／失敗列。"),
            _p("測試資料：檔名 orders_sample.csv，含 20 筆。"),
        ),
        comments=[_comment(41, "<p>欄位對照表已放在 wiki，開發中。</p>", "2026-04-12T02:00:00Z", KEN)],
        updates=_flow(
            ("2026-04-06T01:00:00Z", AVA, "New", "Analyze"),
            ("2026-04-11T03:30:00Z", KEN, "Analyze", "Develop"),
        ),
        relations=[],
    ),
    8420: _item(
        work_item_id=8420,
        work_item_type="Issue",
        title="[Report] 匯出 Excel 欄位錯位 (64033)",
        state="Done",
        area="SIT2",
        assigned=MEI,
        created=YU,
        created_date="2026-04-08T03:22:00Z",
        changed_date="2026-04-16T07:40:00Z",
        category="Bug",
        program="Report",
        extra_fields={"Custom.PrimaryCause": "選用欄位順序與表頭不一致", "Custom.Solution": "依表頭重建欄位對應"},
        description=_html(
            _b("Issue"),
            _p("庫存報表匯出 Excel 後，「可用量」寫進備註欄，後面欄位全部錯一位。"),
            _b("Expected Result"),
            _p("欄位名稱與資料列對齊。"),
            _ol("開啟庫存報表", "勾選可用量與備註", "匯出 xlsx"),
            _p("測試資料：Site SIT2、期間 2026/04/01–2026/04/07"),
            img_tag("excel_columns.png"),
        ),
        comments=[
            _comment(51, "<p>Step 1: 複測匯出 50 列，欄位正確。測試 OK。</p>", "2026-04-16T06:10:00Z", MEI),
        ],
        updates=_flow(
            ("2026-04-09T01:00:00Z", AVA, "New", "Analyze"),
            ("2026-04-12T04:00:00Z", KEN, "Analyze", "Develop"),
            ("2026-04-15T03:00:00Z", MEI, "Develop", "Testing"),
            ("2026-04-16T07:40:00Z", MEI, "Testing", "Done"),
        ),
        relations=[
            _related(8421),
            _attached("excel_columns.png"),
            _commit_rel(SHA_EXCEL, "fix: align export columns with report header", "2026-04-15T02:18:00Z"),
        ],
    ),
    8421: _item(
        work_item_id=8421,
        work_item_type="Task",
        title="[Report] 匯出檔名含非法字元",
        state="Done",
        area="SIT2",
        assigned=KEN,
        created=YU,
        created_date="2026-04-08T03:40:00Z",
        changed_date="2026-04-16T07:45:00Z",
        category="Bug",
        program="Report",
        extra_fields={"Custom.Solution": "檔名去掉 / \\ : * ?"},
        description=_html(
            _b("Issue"),
            _p("報表名稱含斜線時，瀏覽器下載失敗。與欄位錯位同一匯出流程。"),
            _b("Expected Result"),
            _p("檔名改寫成合法字元後仍可下載。"),
        ),
        comments=[_comment(61, "<p>與 8420 一併驗證。測試通過。</p>", "2026-04-16T06:20:00Z", MEI)],
        updates=_flow(
            ("2026-04-09T01:10:00Z", AVA, "New", "Analyze"),
            ("2026-04-12T04:10:00Z", KEN, "Analyze", "Develop"),
            ("2026-04-15T03:10:00Z", MEI, "Develop", "Testing"),
            ("2026-04-16T07:45:00Z", MEI, "Testing", "Done"),
        ),
        relations=[_related(8420)],
    ),
    8430: _item(
        work_item_id=8430,
        work_item_type="Issue",
        title="[Mobile] 行動盤點掃碼無反應",
        state="Analyze",
        area="SIT1",
        assigned=AVA,
        created=YU,
        created_date="2026-04-18T05:00:00Z",
        changed_date="2026-04-19T02:30:00Z",
        category="Bug",
        program="Mobile",
        extra_fields={"Custom.IssuePriority": "High"},
        description=_html(
            _b("Issue"),
            _p("倉儲人員用手持裝置掃儲位條碼，畫面沒有帶入儲位，也沒有錯誤訊息。"),
            _b("Expected Result"),
            _p("掃碼後帶入儲位並可繼續盤點。"),
            _p("測試資料：儲位 A-12-04、裝置 LumenGo。"),
            img_tag("scan_fail.png"),
        ),
        comments=[
            _comment(
                71,
                "<p>現場錄影已附。請 SA 先確認相機權限。BUG #64100</p>",
                "2026-04-18T08:12:00Z",
                YU,
            ),
        ],
        updates=_flow(("2026-04-19T02:30:00Z", AVA, "New", "Analyze")),
        relations=[_attached("scan_fail.png")],
    ),
    8440: _item(
        work_item_id=8440,
        work_item_type="Issue",
        title="[Auth] 角色權限儲存後未生效 (64048)",
        state="Done",
        area="SIT1",
        assigned=MEI,
        created=WEI,
        created_date="2026-04-01T06:00:00Z",
        changed_date="2026-04-10T08:20:00Z",
        category="Bug",
        program="Auth",
        extra_fields={
            "Custom.PrimaryCause": "權限快取未失效",
            "Custom.Solution": "儲存後清快取並重讀角色",
        },
        description=_html(
            _b("Issue"),
            _p("管理員調整「僅能看報表」後，使用者重新登入仍可進入出貨作業。"),
            _b("Expected Result"),
            _p("儲存後立即依新角色顯示選單。"),
            _ol("建立測試帳號 demo.viewer", "改角色為報表唯讀", "重新登入檢查選單"),
            img_tag("permission_dialog.png"),
        ),
        comments=[
            _comment(81, "<p>Step 1: 複測選單已隱藏出貨。測試 OK。</p>", "2026-04-10T07:00:00Z", MEI),
        ],
        updates=_flow(
            ("2026-04-02T01:00:00Z", AVA, "New", "Analyze"),
            ("2026-04-06T04:00:00Z", KEN, "Analyze", "Develop"),
            ("2026-04-09T02:00:00Z", MEI, "Develop", "Testing"),
            ("2026-04-10T08:20:00Z", MEI, "Testing", "Done"),
        ),
        relations=[
            _attached("permission_dialog.png"),
            _commit_rel(SHA_PERM, "fix: persist role permissions after save", "2026-04-08T09:40:00Z"),
        ],
    ),
    8450: _item(
        work_item_id=8450,
        work_item_type="Issue",
        title="[Dashboard] 庫存水位圖表週末資料缺失",
        state="Review",
        area="SIT2",
        assigned=KEN,
        created=AVA,
        created_date="2026-04-14T01:40:00Z",
        changed_date="2026-04-22T03:00:00Z",
        category="Performance",
        program="Dashboard",
        extra_fields={"Custom.IssuePriority": "Low"},
        description=_html(
            _b("Issue"),
            _p("首頁庫存水位折線圖在週六、週日是斷的，週一又接上。排程可能略過週末。"),
            _b("Expected Result"),
            _p("七天都有資料點，無異動時可為 0 或沿用前值。"),
        ),
        comments=[_comment(91, "<p>排程已改為每日；待 Review 看圖表。</p>", "2026-04-22T02:50:00Z", KEN)],
        updates=_flow(
            ("2026-04-15T02:00:00Z", AVA, "New", "Analyze"),
            ("2026-04-18T05:00:00Z", KEN, "Analyze", "Develop"),
            ("2026-04-21T03:00:00Z", MEI, "Develop", "Testing"),
            ("2026-04-22T03:00:00Z", KEN, "Testing", "Review"),
        ),
        relations=[],
    ),
    8460: _item(
        work_item_id=8460,
        work_item_type="Issue",
        title="[Print] 舊版條碼格式不再支援",
        state="Cancel",
        area="SIT1",
        assigned=AVA,
        created=WEI,
        created_date="2026-02-20T04:00:00Z",
        changed_date="2026-03-01T02:00:00Z",
        category="CR",
        program="Print",
        extra_fields={"Custom.IssuePriority": "Low"},
        description=_html(
            _b("Issue"),
            _p("有人提出要繼續印 Code 39 舊格式。產品已全面改 Code 128。"),
            _b("Expected Result"),
            _p("若確定不再支援，本單取消即可。"),
        ),
        comments=[_comment(101, "<p>與產品確認後取消，不列入測試。</p>", "2026-03-01T01:50:00Z", AVA)],
        updates=_flow(
            ("2026-02-21T01:00:00Z", AVA, "New", "Analyze"),
            ("2026-03-01T02:00:00Z", AVA, "Analyze", "Cancel"),
        ),
        relations=[],
    ),
    8470: _item(
        work_item_id=8470,
        work_item_type="Issue",
        title="[Receiving] 收貨完成未更新庫存",
        state="To Do",
        area="SIT2",
        assigned=YU,
        created=WEI,
        created_date="2026-04-24T07:00:00Z",
        changed_date="2026-04-24T07:00:00Z",
        category="Bug",
        program="Receiving",
        extra_fields={"Custom.IssuePriority": "High"},
        description=_html(
            _b("Issue"),
            _p("收貨單按完成後，庫存查詢仍是舊數量，約隔 10 分鐘才出現。"),
            _b("Expected Result"),
            _p("完成當下庫存可用量更新。"),
            _p("測試資料：ASN-20260424-009、料號 LM-1008"),
        ),
        comments=[],
        updates=[],
        relations=[],
    ),
    8480: _item(
        work_item_id=8480,
        work_item_type="Issue",
        title="[Master] 供應商主檔重複建檔 (64055)",
        state="Done",
        area="SIT1",
        assigned=MEI,
        created=WEI,
        created_date="2026-03-05T02:00:00Z",
        changed_date="2026-03-22T06:00:00Z",
        category="Data",
        program="Master",
        extra_fields={
            "Custom.PrimaryCause": "統編未做唯一檢查",
            "Custom.Solution": "儲存前比對統編並提示既有供應商",
        },
        description=_html(
            _b("Issue"),
            _p("同一個統編可以建兩筆供應商，採購單會選到錯誤的一筆。"),
            _b("Expected Result"),
            _p("重複統編時阻擋並顯示原供應商代碼。"),
            _p("測試資料：統編 12345678、供應商代碼 V-1001"),
        ),
        comments=[
            _comment(111, "<p>Step 1: 重複統編已擋住。測試 OK。</p>", "2026-03-21T04:10:00Z", MEI),
        ],
        updates=_flow(
            ("2026-03-06T01:00:00Z", AVA, "New", "Analyze"),
            ("2026-03-12T03:00:00Z", KEN, "Analyze", "Develop"),
            ("2026-03-20T02:00:00Z", MEI, "Develop", "Testing"),
            ("2026-03-22T06:00:00Z", MEI, "Testing", "Done"),
        ),
        relations=[],
    ),
}


EXTRACTS: dict[tuple[int, ...], dict[str, Any]] = {
    (8401, 8402): {
        "test_items": [
            {
                "no": 1,
                "item_name": "宅配出貨單可列印物流標籤",
                "test_data": ["MO: 000010031510", "USN: USN8401001", "出貨單: SO-20260312-018"],
                "expected_result": "預覽顯示收件人與條碼，並可送印",
            }
        ],
        "test_steps": [
            {"no": 1, "description": "開啟出貨單並選擇宅配通路", "images": ["print_error.png"]},
            {"no": 2, "description": "按下去列印標籤，確認預覽與列印", "images": ["label_preview.png"]},
        ],
    },
    (8401,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "出貨單列印物流標籤",
                "test_data": ["MO: 000010031510", "USN: USN8401001"],
                "expected_result": "可帶出標籤並送印",
            }
        ],
        "test_steps": [
            {"no": 1, "description": "重現列印失敗", "images": ["print_error.png"]},
            {"no": 2, "description": "修正後複測列印", "images": ["label_preview.png"]},
        ],
    },
    (8402,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "標籤預覽有內容",
                "test_data": ["MO: 000010031510"],
                "expected_result": "預覽顯示收件人、條碼與出貨單號",
            }
        ],
        "test_steps": [{"no": 1, "description": "開啟標籤預覽", "images": []}],
    },
    (8410,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "盤點單合計等於儲位加總",
                "test_data": ["MO: 000010040211", "盤點單: IC-20260402-004", "CPN: CPN-INV-004"],
                "expected_result": "合計與明細加總一致",
            }
        ],
        "test_steps": [
            {"no": 1, "description": "匯入 A 區儲位並比對合計", "images": ["inventory_count.png"]},
        ],
    },
    (8415,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "CSV 批次匯入訂單",
                "test_data": ["檔名: orders_sample.csv", "筆數: 20"],
                "expected_result": "成功列建立訂單，失敗列有原因",
            }
        ],
        "test_steps": [{"no": 1, "description": "上傳 CSV 並查看匯入結果", "images": []}],
    },
    (8420, 8421): {
        "test_items": [
            {
                "no": 1,
                "item_name": "庫存報表匯出欄位對齊且檔名合法",
                "test_data": ["Site: SIT2", "期間: 2026/04/01–2026/04/07"],
                "expected_result": "xlsx 欄位與表頭一致，檔名不含非法字元",
            }
        ],
        "test_steps": [
            {"no": 1, "description": "勾選可用量與備註後匯出", "images": ["excel_columns.png"]},
        ],
    },
    (8420,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "庫存報表匯出欄位對齊",
                "test_data": ["Site: SIT2"],
                "expected_result": "可用量與備註各在正確欄位",
            }
        ],
        "test_steps": [{"no": 1, "description": "匯出並核對欄位", "images": ["excel_columns.png"]}],
    },
    (8421,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "匯出檔名不含非法字元",
                "test_data": ["報表名稱含斜線"],
                "expected_result": "可下載且檔名已改寫",
            }
        ],
        "test_steps": [{"no": 1, "description": "以含斜線的報表名稱匯出", "images": []}],
    },
    (8430,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "行動盤點掃儲位條碼",
                "test_data": ["儲位: A-12-04", "裝置: LumenGo"],
                "expected_result": "掃碼後帶入儲位",
            }
        ],
        "test_steps": [{"no": 1, "description": "用手持裝置掃儲位條碼", "images": ["scan_fail.png"]}],
    },
    (8440,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "調整角色後選單立即生效",
                "test_data": ["帳號: demo.viewer", "角色: 報表唯讀"],
                "expected_result": "重新登入後看不到出貨作業",
            }
        ],
        "test_steps": [
            {"no": 1, "description": "改角色並重新登入檢查選單", "images": ["permission_dialog.png"]},
        ],
    },
    (8450,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "庫存水位圖含週末資料點",
                "test_data": ["期間含週六週日"],
                "expected_result": "七天都有資料點",
            }
        ],
        "test_steps": [{"no": 1, "description": "開啟首頁折線圖核對週末", "images": []}],
    },
    (8460,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "確認不再支援舊條碼格式",
                "test_data": ["格式: Code 39"],
                "expected_result": "本單取消，不列入測試範圍",
            }
        ],
        "test_steps": [{"no": 1, "description": "與產品確認後結案", "images": []}],
    },
    (8470,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "收貨完成即時更新庫存",
                "test_data": ["ASN-20260424-009", "料號: LM-1008"],
                "expected_result": "完成當下可用量更新",
            }
        ],
        "test_steps": [{"no": 1, "description": "完成收貨單後立刻查庫存", "images": []}],
    },
    (8480,): {
        "test_items": [
            {
                "no": 1,
                "item_name": "供應商統編不可重複",
                "test_data": ["統編: 12345678", "供應商: V-1001"],
                "expected_result": "重複統編被阻擋並顯示原代碼",
            }
        ],
        "test_steps": [{"no": 1, "description": "用既有統編新建供應商", "images": []}],
    },
}


def all_ids() -> list[int]:
    return sorted(ITEMS)


def get_item(work_item_id: int) -> dict[str, Any]:
    item = ITEMS.get(int(work_item_id))
    if item is None:
        raise RuntimeError(
            f"展示模式沒有 Work Item #{work_item_id}。"
            f"可用 ID：{', '.join(str(i) for i in all_ids())}"
        )
    return item


def summaries(work_item_ids: list[int]) -> list[dict[str, Any]]:
    rows = []
    for work_item_id in work_item_ids:
        item = get_item(work_item_id)
        fields = item["fields"]
        rows.append(
            {
                "id": item["id"],
                "fields": {
                    "System.Id": item["id"],
                    "System.Title": fields["System.Title"],
                    "System.WorkItemType": fields["System.WorkItemType"],
                    "System.State": fields["System.State"],
                },
            }
        )
    return rows


def work_item_payload(work_item_id: int) -> dict[str, Any]:
    item = get_item(work_item_id)
    return {"id": item["id"], "rev": item["rev"], "fields": item["fields"], "relations": item["relations"]}


def comments_payload(work_item_id: int) -> list[dict[str, Any]]:
    return list(get_item(work_item_id)["comments"])


def updates_payload(work_item_id: int) -> list[dict[str, Any]]:
    return list(get_item(work_item_id)["updates"])


def git_commit_payload(repository_id: str, commit_id: str) -> dict[str, Any]:
    sha = (commit_id or "").lower()
    payload = COMMITS.get(sha)
    if payload is None or (repository_id and repository_id != REPO_ID):
        raise RuntimeError(f"展示模式沒有此 Commit：{commit_id}")
    return payload


def _remap_images(extract: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    allowed: list[str] = []
    for item in items:
        for path in (item.get("images") or {}).values():
            text = str(path)
            if text and text not in allowed:
                allowed.append(text)
    out = deepcopy(extract)
    for step in out.get("test_steps") or []:
        mapped: list[str] = []
        for src in step.get("images") or []:
            name = Path(str(src)).name
            match = next((path for path in allowed if Path(path).name.endswith(name) or name in path), None)
            if match and match not in mapped:
                mapped.append(match)
        step["images"] = mapped
    return out


def _synthesize_extract(items: list[dict[str, Any]]) -> dict[str, Any]:
    test_items = []
    steps = []
    for index, item in enumerate(items, start=1):
        title = str((item.get("fields") or {}).get("System.Title") or item.get("title") or "")
        test_items.append(
            {
                "no": index,
                "item_name": title.split("]")[-1].strip() or title,
                "test_data": [],
                "expected_result": "依描述驗證",
            }
        )
        steps.append({"no": index, "description": f"依 ADO #{item.get('id')} 描述操作", "images": []})
    return {"test_items": test_items, "test_steps": steps}


def demo_extract_for(work_item_ids: list[int], items: list[dict[str, Any]]) -> dict[str, Any]:
    key = tuple(sorted(int(value) for value in work_item_ids))
    extract = EXTRACTS.get(key)
    if extract is None:
        merged_items: list[dict[str, Any]] = []
        merged_steps: list[dict[str, Any]] = []
        for work_item_id in key:
            part = EXTRACTS.get((work_item_id,))
            if not part:
                continue
            merged_items.extend(deepcopy(part.get("test_items") or []))
            merged_steps.extend(deepcopy(part.get("test_steps") or []))
        if merged_items:
            for index, row in enumerate(merged_items, start=1):
                row["no"] = index
            for index, row in enumerate(merged_steps, start=1):
                row["no"] = index
            extract = {"test_items": merged_items, "test_steps": merged_steps}
        else:
            extract = _synthesize_extract(items)
    return _remap_images(extract, items)


def copy_attachment(url: str, dest: Path) -> None:
    ensure_demo_assets()
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    name = (query.get("fileName") or query.get("filename") or [Path(parsed.path).name])[0]
    name = Path(str(name)).name
    src = DEMO_FILES_DIR / name
    if not src.is_file():
        guid = Path(parsed.path).name
        for filename, image_guid in IMAGE_GUIDS.items():
            if guid == image_guid or guid[:8] == image_guid[:8]:
                src = DEMO_FILES_DIR / filename
                break
    if not src.is_file():
        raise FileNotFoundError(f"展示模式找不到附件：{url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())


def ensure_demo_assets() -> None:
    write_demo_images()
    missing = [name for name in DEMO_IMAGE_SPECS if not (DEMO_FILES_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"展示圖片寫入失敗：{', '.join(missing)}")
    build_demo_template(DEMO_TEMPLATE_PATH)
