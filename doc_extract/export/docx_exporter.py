# -*- coding: utf-8 -*-
"""Word (.docx) export with headings, paragraphs and merged tables."""
from __future__ import annotations

import os
from typing import List

from docx import Document as DocxDocument
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from ..models import Block, DocumentResult, PageResult, TableData

BODY_FONT = "宋体"
HEADING_FONT = "微软雅黑"


def _set_font(run, name: str, size: float, bold: bool = False,
              color=None) -> None:
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        rfonts.set(qn(attr), name)


def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _set_cell_margins(cell, top=60, bottom=60, left=90, right=90) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for tag, value in (("top", top), ("bottom", bottom),
                       ("left", left), ("right", right)):
        node = tc_mar.find(qn("w:" + tag))
        if node is None:
            node = OxmlElement("w:" + tag)
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _add_text_block(doc, block: Block) -> None:
    text = (block.text or "").strip()
    if not text:
        return
    if block.kind in ("title",):
        p = doc.add_paragraph()
        p.style = doc.styles["Heading 1"]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        _set_font(run, HEADING_FONT, 18, True, (31, 41, 55))
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(8)
        return
    if block.kind in ("heading",):
        p = doc.add_paragraph()
        p.style = doc.styles["Heading 2"]
        run = p.add_run(text)
        _set_font(run, HEADING_FONT, 14, True, (31, 41, 55))
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        return
    if block.kind in ("figure",):
        p = doc.add_paragraph()
        run = p.add_run("［图片区域］")
        _set_font(run, BODY_FONT, 9, False, (148, 163, 184))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return
    p = doc.add_paragraph()
    p.style = doc.styles["Normal"]
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.45
    p.paragraph_format.space_after = Pt(4)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        run = p.add_run(line)
        _set_font(run, BODY_FONT, 10.5, False, (30, 41, 59))
        if i < len(lines) - 1:
            run.add_break()


def _add_table(doc, table_data: TableData, caption: str = "") -> None:
    if table_data.is_empty():
        return
    if caption:
        p = doc.add_paragraph()
        run = p.add_run(caption)
        _set_font(run, HEADING_FONT, 9.5, True, (71, 85, 105))
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(3)
    rows, cols = table_data.n_rows, table_data.n_cols
    table = doc.add_table(rows=rows, cols=cols)
    table.style = doc.styles["Table Grid"]
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for r in range(rows):
        for c in range(cols):
            cell = table.cell(r, c)
            _set_cell_margins(cell)
            try:
                rs, cs = table_data.spans[r][c]
            except (IndexError, TypeError):
                rs, cs = (1, 1)
            if rs == 0 and cs == 0:
                continue
            if rs > 1 or cs > 1:
                bottom = min(rows - 1, r + max(rs, 1) - 1)
                right = min(cols - 1, c + max(cs, 1) - 1)
                cell = cell.merge(table.cell(bottom, right))
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            value = table_data.grid[r][c] if c < len(table_data.grid[r]) else ""
            lines = value.split("\n") if value else [""]
            for i, line in enumerate(lines):
                run = p.add_run(line)
                _set_font(run, BODY_FONT, 9, bool(r == 0), (15, 23, 42))
                if i < len(lines) - 1:
                    run.add_break()
            if r == 0:
                _shade(cell, "EAF2F8")
    # Keep tables from feeling cramped.
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def export_docx(document: DocumentResult, output_path: str) -> str:
    """Write ``document`` to a .docx file and return the absolute path."""
    docx = DocxDocument()
    docx.core_properties.author = "盛晗"
    docx.core_properties.last_modified_by = "盛晗"
    docx.core_properties.title = document.title or "文档提取"
    docx.core_properties.comments = "由文档提取生成 · 作者：盛晗"
    section = docx.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    normal = docx.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    # Light document header.
    header_p = section.header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = header_p.add_run("文档提取 · PP-OCRv5 mobile")
    _set_font(hr, HEADING_FONT, 8.5, False, (148, 163, 184))

    # Title.
    title = document.title or "未命名文档"
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    _set_font(run, HEADING_FONT, 20, True, (15, 23, 42))
    p.paragraph_format.space_after = Pt(4)

    meta = docx.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_run = meta.add_run(
        "识别时间：%s    页数：%d    表格：%d" %
        (document.created_at, len(document.pages), document.total_tables)
    )
    _set_font(meta_run, BODY_FONT, 9, False, (100, 116, 139))
    meta.paragraph_format.space_after = Pt(16)

    table_no = 0
    for page_idx, page in enumerate(document.pages):
        if page_idx > 0:
            docx.add_page_break()
            p = docx.add_paragraph()
            run = p.add_run("第 %d 页" % page.number)
            _set_font(run, HEADING_FONT, 9, False, (148, 163, 184))
            p.paragraph_format.space_after = Pt(8)
        for block in page.blocks:
            if block.kind == "table" and block.table:
                table_no += 1
                _add_table(docx, block.table, "表 %d" % table_no)
            else:
                _add_text_block(docx, block)

    if not document.pages or not document.plain_text.strip():
        p = docx.add_paragraph()
        run = p.add_run("（未识别到文字内容）")
        _set_font(run, BODY_FONT, 11, False, (148, 163, 184))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    out = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    docx.save(out)
    return out
