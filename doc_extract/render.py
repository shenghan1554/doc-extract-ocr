# -*- coding: utf-8 -*-
"""HTML/text rendering helpers used by the live preview and clipboard."""
from __future__ import annotations

import html as _html
from typing import List

from .models import Block, DocumentResult, PageResult, TableData
from .table_utils import table_to_html


def _esc(text: str) -> str:
    return _html.escape(text or "").replace("\n", "<br/>")


def document_html(document: DocumentResult, show_confidence: bool = False) -> str:
    """Return a Qt-friendly rich text representation of the whole document."""
    rows: List[str] = []
    title = _esc(document.title or "未命名文档")
    rows.append(
        '<div style="font-family:\'Microsoft YaHei UI\',\'Microsoft YaHei\',sans-serif;'
        'color:#0f172a;">'
    )
    rows.append('<h1 style="font-size:22px;text-align:center;margin:2px 0 4px 0;">%s</h1>' % title)
    rows.append(
        '<p style="text-align:center;color:#64748b;font-size:11px;margin:0 0 14px 0;">'
        '识别时间：%s &nbsp;·&nbsp; %d 页 &nbsp;·&nbsp; %d 个表格 &nbsp;·&nbsp; %s</p>'
        % (_esc(document.created_at), len(document.pages),
           document.total_tables, _esc(document.engine))
    )
    rows.append('<hr style="border:0;border-top:1px solid #e2e8f0;"/>')
    for page_idx, page in enumerate(document.pages):
        if len(document.pages) > 1:
            rows.append(
                '<p style="color:#94a3b8;font-size:10px;margin:14px 0 6px 0;">'
                '第 %d 页 / %d</p>' % (page.number, len(document.pages))
            )
        for block in page.blocks:
            rows.append(block_html(block, show_confidence))
    if not document.plain_text.strip():
        rows.append('<p style="color:#94a3b8;text-align:center;margin-top:30px;">'
                    '未识别到文字内容</p>')
    rows.append("</div>")
    return "".join(rows)


def block_html(block: Block, show_confidence: bool = False) -> str:
    conf = ""
    if show_confidence and block.confidence:
        conf = ('<span style="color:#94a3b8;font-size:9px;"> %.0f%%</span>'
                % (block.confidence * 100))
    if block.kind == "table" and block.table:
        return ('<div style="margin:8px 0 12px 0;">%s%s</div>'
                % (table_to_html(block.table), conf))
    text = _esc(block.text)
    if not text.strip():
        return ""
    if block.kind == "title":
        return ('<h2 style="font-size:18px;margin:14px 0 6px 0;color:#0f172a;">%s%s</h2>'
                % (text, conf))
    if block.kind == "heading":
        return ('<h3 style="font-size:15px;margin:11px 0 5px 0;color:#334155;">%s%s</h3>'
                % (text, conf))
    if block.kind == "figure":
        return ('<p style="text-align:center;color:#94a3b8;font-size:11px;">'
                '［图片区域］%s</p>' % conf)
    return ('<p style="font-size:13px;line-height:1.65;margin:3px 0 7px 0;'
            'text-align:justify;">%s%s</p>' % (text, conf))


def document_plain_text(document: DocumentResult, page_markers: bool = False) -> str:
    chunks: List[str] = []
    for page in document.pages:
        if page_markers and len(document.pages) > 1:
            chunks.append("──────── 第 %d 页 ────────" % page.number)
        if page.plain_text:
            chunks.append(page.plain_text)
    body = "\n\n".join(chunks).strip()
    title = (document.title or "").strip()
    if title and not body.startswith(title):
        body = title + ("\n\n" + body if body else "")
    return body


def tables_plain_text(document: DocumentResult) -> str:
    blocks = []
    for i, table in enumerate(document.tables, 1):
        blocks.append("表格 %d\n%s" % (i, table.to_tsv()))
    return "\n\n".join(blocks)


def page_html(page: PageResult) -> str:
    doc = DocumentResult(title="第 %d 页" % page.number, pages=[page],
                         engine=page.engine)
    return document_html(doc)
