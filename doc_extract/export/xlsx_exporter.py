# -*- coding: utf-8 -*-
"""Excel (.xlsx) export: readable text sheet + one editable sheet per table."""
from __future__ import annotations

import os
import re
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ..models import DocumentResult, TableData

THIN = Side(style="thin", color="CBD5E1")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", fgColor="EAF2F8")
TITLE_FILL = PatternFill("solid", fgColor="0F766E")
TEXT_COLOR = "1E293B"


def _safe_sheet_name(name: str, used: set) -> str:
    name = re.sub(r"[\[\]\:\*\?\/\\]", "_", name or "表格")
    name = name[:28] or "表格"
    base = name
    i = 2
    while name in used:
        name = "%s_%d" % (base, i)
        i += 1
    used.add(name)
    return name


def _safe_text(value: str) -> str:
    value = (value or "").replace("\x00", "")
    return value


def _write_cell(ws, row: int, col: int, value: str, header: bool = False,
                font_size: float = 10) -> None:
    cell = ws.cell(row=row, column=col)
    cell.value = _safe_text(value)
    if isinstance(cell.value, str) and cell.value.startswith("="):
        cell.data_type = "s"
    cell.font = Font(name="微软雅黑", size=font_size, bold=header,
                     color=TEXT_COLOR)
    cell.alignment = Alignment(wrap_text=True, vertical="top",
                               horizontal="left")
    cell.border = BORDER
    if header:
        cell.fill = HEADER_FILL


def _auto_width(ws, max_col: int, max_row: int) -> None:
    widths = {}
    for c in range(1, max_col + 1):
        longest = 8
        for r in range(1, min(max_row, 200) + 1):
            val = ws.cell(row=r, column=c).value
            if not val:
                continue
            for line in str(val).splitlines():
                # CJK chars are roughly two columns wide.
                width = sum(2 if ord(ch) > 127 else 1 for ch in line)
                longest = max(longest, width)
        widths[c] = min(max(longest + 3, 10), 52)
    for c, width in widths.items():
        ws.column_dimensions[get_column_letter(c)].width = width


def _write_table_sheet(ws, table: TableData, caption: str) -> None:
    ws.sheet_view.showGridLines = False
    ws.merge_cells(start_row=1, start_column=1, end_row=1,
                   end_column=max(table.n_cols, 1))
    title = ws.cell(row=1, column=1, value=caption)
    title.font = Font(name="微软雅黑", size=13, bold=True, color="FFFFFF")
    title.fill = TITLE_FILL
    title.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 28

    start = 3
    rows, cols = table.n_rows, table.n_cols
    for r in range(rows):
        for c in range(cols):
            try:
                rs, cs = table.spans[r][c]
            except (IndexError, TypeError):
                rs, cs = (1, 1)
            if rs == 0 and cs == 0:
                continue
            value = table.grid[r][c] if c < len(table.grid[r]) else ""
            _write_cell(ws, start + r, c + 1, value, header=(r == 0),
                        font_size=9.5)
            if (rs > 1 or cs > 1) and (r + rs <= rows) and (c + cs <= cols):
                ws.merge_cells(start_row=start + r, start_column=c + 1,
                               end_row=start + r + rs - 1,
                               end_column=c + cs)
    for r in range(start, start + rows):
        ws.row_dimensions[r].height = 22
    ws.freeze_panes = "A%d" % (start + 1)
    _auto_width(ws, cols, start + rows - 1)


def _write_text_sheet(ws, document: DocumentResult) -> None:
    ws.sheet_view.showGridLines = False
    ws.merge_cells("A1:C1")
    title = ws["A1"]
    title.value = document.title or "文档内容"
    title.font = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
    title.fill = TITLE_FILL
    title.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30

    ws["A2"] = "页"
    ws["B2"] = "类型"
    ws["C2"] = "内容"
    for c in range(1, 4):
        cell = ws.cell(row=2, column=c)
        cell.font = Font(name="微软雅黑", bold=True, size=10)
        cell.fill = HEADER_FILL
        cell.border = BORDER
        cell.alignment = Alignment(vertical="center")

    row = 3
    for page in document.pages:
        for block in page.blocks:
            if block.kind == "table" and block.table:
                content = block.table.to_text()
                kind = "表格"
            else:
                content = block.text or ""
                kind = {"title": "标题", "heading": "小标题"}.get(block.kind, "正文")
            if not content.strip():
                continue
            _write_cell(ws, row, 1, str(page.number), font_size=9)
            _write_cell(ws, row, 2, kind, font_size=9)
            _write_cell(ws, row, 3, content, font_size=10)
            ws.row_dimensions[row].height = max(20, min(120, 16 * (content.count("\n") + 1)))
            row += 1
    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 9
    ws.column_dimensions["C"].width = 86
    ws.freeze_panes = "A3"


def export_xlsx(document: DocumentResult, output_path: str) -> str:
    """Write ``document`` to an .xlsx file and return the absolute path."""
    wb = Workbook()
    ws = wb.active
    ws.title = "全文"
    _write_text_sheet(ws, document)

    used = {"全文"}
    for i, table in enumerate(document.tables, 1):
        if table.is_empty():
            continue
        name = _safe_sheet_name("表格%d" % i, used)
        sh = wb.create_sheet(name)
        _write_table_sheet(sh, table, "表格 %d · 共 %d 行 %d 列" %
                           (i, table.n_rows, table.n_cols))

    info = wb.create_sheet("说明", 0)
    info.sheet_view.showGridLines = False
    info["A1"] = "文档提取"
    info["A1"].font = Font(name="微软雅黑", size=18, bold=True, color="0F766E")
    info["A3"] = "文件"
    info["B3"] = document.source_path or "—"
    info["A4"] = "识别时间"
    info["B4"] = document.created_at
    info["A5"] = "识别引擎"
    info["B5"] = document.engine
    info["A6"] = "页数"
    info["B6"] = len(document.pages)
    info["A7"] = "表格数"
    info["B7"] = document.total_tables
    info["A8"] = "说明"
    info["B8"] = "“全文”工作表保留阅读顺序；“表格N”工作表保留合并单元格，可直接编辑。"
    for r in range(3, 9):
        info.cell(row=r, column=1).font = Font(name="微软雅黑", bold=True, size=10)
        info.cell(row=r, column=1).fill = HEADER_FILL
        info.cell(row=r, column=1).border = BORDER
        info.cell(row=r, column=2).font = Font(name="微软雅黑", size=10)
        info.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        info.cell(row=r, column=2).border = BORDER
    info.column_dimensions["A"].width = 14
    info.column_dimensions["B"].width = 72

    out = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wb.save(out)
    return out
