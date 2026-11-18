# -*- coding: utf-8 -*-
"""PDF export with embedded Chinese fonts and selectable text."""
from __future__ import annotations

import os
from typing import List, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from ..models import Block, DocumentResult, TableData

WIN_FONTS = r"C:\Windows\Fonts"
_FONT_CACHE = {}


def _font_paths() -> Tuple[str, str]:
    candidates = [
        (os.path.join(WIN_FONTS, "simsun.ttc"), os.path.join(WIN_FONTS, "simhei.ttf")),
        (os.path.join(WIN_FONTS, "msyh.ttc"), os.path.join(WIN_FONTS, "msyhbd.ttc")),
        (os.path.join(WIN_FONTS, "Deng.ttf"), os.path.join(WIN_FONTS, "Dengb.ttf")),
    ]
    for body, bold in candidates:
        if os.path.exists(body) and os.path.exists(bold):
            return body, bold
    return "", ""


def _register_fonts() -> Tuple[str, str]:
    if _FONT_CACHE.get("ready"):
        return _FONT_CACHE["body"], _FONT_CACHE["bold"]
    body_path, bold_path = _font_paths()
    body_name, bold_name = "DocBody", "DocBold"
    if body_path:
        try:
            kwargs = {"subfontIndex": 0} if body_path.lower().endswith(".ttc") else {}
            pdfmetrics.registerFont(TTFont(body_name, body_path, **kwargs))
            bkwargs = {"subfontIndex": 0} if bold_path.lower().endswith(".ttc") else {}
            pdfmetrics.registerFont(TTFont(bold_name, bold_path, **bkwargs))
            pdfmetrics.registerFontFamily(body_name, normal=body_name,
                                          bold=bold_name, italic=body_name,
                                          boldItalic=bold_name)
        except Exception:  # noqa: BLE001
            body_name = bold_name = "STSong-Light"
            if body_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(UnicodeCIDFont(body_name))
    else:
        body_name = bold_name = "STSong-Light"
        if body_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(body_name))
    _FONT_CACHE.update(ready=True, body=body_name, bold=bold_name)
    return body_name, bold_name


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;")


def _para(text: str, style: ParagraphStyle) -> Paragraph:
    value = _esc(text).replace("\n", "<br/>")
    return Paragraph(value, style)


def _styles(body: str, bold: str):
    return {
        "title": ParagraphStyle(
            "DocTitle", fontName=bold, fontSize=20, leading=28,
            alignment=TA_CENTER, textColor=colors.HexColor("#0F172A"),
            spaceAfter=5, wordWrap="CJK"),
        "meta": ParagraphStyle(
            "DocMeta", fontName=body, fontSize=8.5, leading=13,
            alignment=TA_CENTER, textColor=colors.HexColor("#64748B"),
            spaceAfter=16, wordWrap="CJK"),
        "h1": ParagraphStyle(
            "DocH1", fontName=bold, fontSize=14, leading=21,
            textColor=colors.HexColor("#1E293B"), spaceBefore=12,
            spaceAfter=6, wordWrap="CJK"),
        "h2": ParagraphStyle(
            "DocH2", fontName=bold, fontSize=12, leading=18,
            textColor=colors.HexColor("#334155"), spaceBefore=9,
            spaceAfter=4, wordWrap="CJK"),
        "body": ParagraphStyle(
            "DocBody", fontName=body, fontSize=10.5, leading=17.5,
            alignment=TA_JUSTIFY, textColor=colors.HexColor("#1E293B"),
            firstLineIndent=21, spaceAfter=4, wordWrap="CJK"),
        "caption": ParagraphStyle(
            "DocCaption", fontName=bold, fontSize=8.5, leading=12,
            textColor=colors.HexColor("#475569"), spaceBefore=6,
            spaceAfter=3, wordWrap="CJK"),
        "page": ParagraphStyle(
            "DocPage", fontName=body, fontSize=9, leading=12,
            textColor=colors.HexColor("#94A3B8"), spaceAfter=10,
            wordWrap="CJK"),
        "cell": ParagraphStyle(
            "DocCell", fontName=body, fontSize=8, leading=11.5,
            textColor=colors.HexColor("#0F172A"), wordWrap="CJK"),
        "cell_head": ParagraphStyle(
            "DocCellHead", fontName=bold, fontSize=8, leading=11.5,
            textColor=colors.HexColor("#0F172A"), wordWrap="CJK"),
    }


def _table_flowable(table_data: TableData, styles, avail_width: float):
    rows, cols = table_data.n_rows, table_data.n_cols
    data: List[List[object]] = []
    spans = []
    for r in range(rows):
        row = []
        for c in range(cols):
            try:
                rs, cs = table_data.spans[r][c]
            except (IndexError, TypeError):
                rs, cs = (1, 1)
            if rs == 0 and cs == 0:
                row.append("")
                continue
            value = table_data.grid[r][c] if c < len(table_data.grid[r]) else ""
            row.append(_para(value, styles["cell_head"] if r == 0 else styles["cell"]))
            if rs > 1 or cs > 1:
                spans.append(("SPAN", (c, r), (c + cs - 1, r + rs - 1)))
        data.append(row)
    if not data or cols == 0:
        return None
    # Uneven very wide tables are hard to read; cap the width per column.
    col_width = avail_width / max(cols, 1)
    tbl = Table(data, colWidths=[col_width] * cols, repeatRows=1,
                hAlign="LEFT", splitByRow=1)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2F8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    style.extend(spans)
    tbl.setStyle(TableStyle(style))
    return tbl


def export_pdf(document: DocumentResult, output_path: str) -> str:
    """Write ``document`` to a PDF file and return the absolute path."""
    body_font, bold_font = _register_fonts()
    styles = _styles(body_font, bold_font)
    max_cols = max([t.n_cols for t in document.tables] or [0])
    pagesize = landscape(A4) if max_cols > 6 else A4
    is_landscape = pagesize[0] > pagesize[1]
    margins = (1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm) if is_landscape \
        else (2.0 * cm, 2.0 * cm, 2.2 * cm, 2.2 * cm)
    out = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc = SimpleDocTemplate(
        out, pagesize=pagesize,
        leftMargin=margins[0], rightMargin=margins[1],
        topMargin=margins[2], bottomMargin=margins[3],
        title=document.title or "文档提取", author="盛晗",
        subject="PP-OCRv5 mobile / PP-Structure 识别结果",
        creator="文档提取 · 盛晗",
    )

    story: List[object] = []
    story.append(_para(document.title or "未命名文档", styles["title"]))
    story.append(_para(
        "识别时间：%s    页数：%d    表格：%d    引擎：%s" %
        (document.created_at, len(document.pages), document.total_tables,
         document.engine), styles["meta"]))
    avail = pagesize[0] - margins[0] - margins[1]
    table_no = 0

    for page_idx, page in enumerate(document.pages):
        if page_idx > 0:
            story.append(PageBreak())
        for block in page.blocks:
            if block.kind == "table" and block.table:
                table_no += 1
                story.append(_para("表 %d" % table_no, styles["caption"]))
                flow = _table_flowable(block.table, styles, avail)
                if flow is not None:
                    story.append(flow)
                    story.append(Spacer(1, 6))
                continue
            text = (block.text or "").strip()
            if not text:
                continue
            if block.kind in ("title", "heading"):
                story.append(_para(text, styles["h1"] if block.kind == "title" else styles["h2"]))
            elif block.kind == "figure":
                story.append(_para("［图片区域］", styles["meta"]))
            else:
                story.append(_para(text, styles["body"]))

    if not story:
        story.append(_para("（未识别到文字内容）", styles["meta"]))

    def _on_page(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont(body_font, 9)
        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.drawCentredString(pagesize[0] / 2.0, 1.2 * cm,
                                 "第 %d 页" % doc_obj.page)
        canvas.setFont(body_font, 7.5)
        canvas.drawRightString(pagesize[0] - margins[1], 1.2 * cm,
                               "文档提取 · PP-OCRv5 mobile")
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return out
