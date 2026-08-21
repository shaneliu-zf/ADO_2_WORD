#!/usr/bin/env python3
"""依實際 ADO 標題重寫 Word 目錄。"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree

from backend.pipeline.word.oxml import elm_text, paragraph_style


def max_bookmark_id(root: etree._Element) -> int:
    ids = []
    for node in root.iter(qn("w:bookmarkStart")):
        raw = node.get(qn("w:id")) or ""
        if raw and str(raw).isdigit():
            ids.append(int(raw))
    return max(ids, default=0)


def replace_toc_bookmark(p_elm: etree._Element, bookmark: str) -> None:
    for instr in p_elm.iter(qn("w:instrText")):
        text = instr.text or ""
        if "_Toc" in text:
            instr.text = re.sub(r"_Toc\d+", bookmark, text)


def set_toc_texts(p_elm: etree._Element, number: str, title: str) -> None:
    nodes = list(p_elm.iter(qn("w:t")))
    if not nodes:
        return
    nodes[0].text = f"{number} "
    if len(nodes) > 1:
        nodes[1].text = title


def set_heading_bookmark(p_elm: etree._Element, name: str, bookmark_id: int) -> None:
    for start in list(p_elm.iter(qn("w:bookmarkStart"))):
        old_name = start.get(qn("w:name")) or ""
        if old_name.startswith("_Toc") or old_name == name:
            old_id = start.get(qn("w:id"))
            parent = start.getparent()
            if parent is not None:
                parent.remove(start)
            for end in list(p_elm.iter(qn("w:bookmarkEnd"))):
                if end.get(qn("w:id")) == old_id:
                    end_parent = end.getparent()
                    if end_parent is not None:
                        end_parent.remove(end)
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    p_elm.insert(0, start)
    p_elm.append(end)


def collect_ado_outline(body: etree._Element) -> list[dict[str, Any]]:
    outline: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for child in body:
        if child.tag != qn("w:p"):
            continue
        style = paragraph_style(child)
        text = elm_text(child).strip()
        if style == "2" and text.startswith("ADO"):
            current = {"heading": child, "title": text, "items": None, "attach": None, "commits": None}
            outline.append(current)
        elif current is not None and style == "4" and text == "測試項目":
            current["items"] = child
        elif current is not None and style == "4" and text == "測試附件":
            current["attach"] = child
        elif current is not None and style == "4" and text == "Commit":
            current["commits"] = child
    return outline


def refresh_toc(doc: Document) -> None:
    """依實際 ADO 標題重寫目錄（標題沒有 Redmine 就不出現）。"""
    body = doc.element.body
    sdt = body.find(qn("w:sdt"))
    if sdt is None:
        return
    content = sdt.find(qn("w:sdtContent"))
    if content is None:
        return

    outline = collect_ado_outline(body)
    toc_paras = list(content)
    proto_by_kind: dict[str, etree._Element] = {}
    ado_toc_paras: list[etree._Element] = []
    for para in toc_paras:
        text = elm_text(para)
        if "ADO#" in text:
            proto_by_kind.setdefault("heading", para)
            ado_toc_paras.append(para)
        elif ado_toc_paras and "測試項目" in text:
            proto_by_kind.setdefault("items", para)
            ado_toc_paras.append(para)
        elif ado_toc_paras and "測試附件" in text:
            proto_by_kind.setdefault("attach", para)
            ado_toc_paras.append(para)
        elif ado_toc_paras and text.strip() == "Commit":
            proto_by_kind.setdefault("commits", para)
            ado_toc_paras.append(para)
        elif ado_toc_paras and "變動紀錄" in text:
            ado_toc_paras.append(para)

    if "heading" not in proto_by_kind:
        return

    insert_before = ado_toc_paras[-1].getnext() if ado_toc_paras else None
    for para in ado_toc_paras:
        parent = para.getparent()
        if parent is not None:
            parent.remove(para)

    next_id = max_bookmark_id(doc.element) + 1
    for index, block in enumerate(outline, start=2):
        entries = [
            ("heading", f"{index}", block["title"], block["heading"]),
            ("items", f"{index}.1", "測試項目", block.get("items")),
            ("attach", f"{index}.2", "測試附件", block.get("attach")),
            ("commits", f"{index}.3", "Commit", block.get("commits")),
        ]
        for kind, number, title, heading_elm in entries:
            proto = proto_by_kind.get(kind) or (proto_by_kind.get("attach") if kind == "commits" else None)
            if proto is None or heading_elm is None:
                continue
            bookmark = f"_Toc{next_id}"
            set_heading_bookmark(heading_elm, bookmark, next_id)
            next_id += 1
            toc_para = deepcopy(proto)
            set_toc_texts(toc_para, number, title)
            replace_toc_bookmark(toc_para, bookmark)
            if insert_before is not None:
                insert_before.addprevious(toc_para)
            else:
                content.append(toc_para)

    for para in list(content):
        nodes = list(para.iter(qn("w:t")))
        if not nodes:
            continue
        number = (nodes[0].text or "").strip()
        if re.fullmatch(r"\d+(?:\.\d+)*", number) and not (nodes[0].text or "").endswith(" "):
            nodes[0].text = f"{number} "


def ensure_heading_number_space(doc: Document) -> None:
    """標題編號與文字之間用空格分隔，避免 11ADO#846。"""
    numbering_part = getattr(doc.part, "numbering_part", None)
    if numbering_part is None:
        return
    heading_styles = {"2", "4", "5", "6", "7"}
    for lvl in numbering_part.element.iter(qn("w:lvl")):
        pstyle = lvl.find(qn("w:pStyle"))
        if pstyle is None or pstyle.get(qn("w:val")) not in heading_styles:
            continue
        suff = lvl.find(qn("w:suff"))
        if suff is None:
            suff = OxmlElement("w:suff")
            lvltext = lvl.find(qn("w:lvlText"))
            if lvltext is not None:
                lvltext.addnext(suff)
            else:
                lvl.append(suff)
        suff.set(qn("w:val"), "space")
