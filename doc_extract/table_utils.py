# -*- coding: utf-8 -*-
"""Tolerant HTML table parser and renderer.

PaddleOCR / SLANet models occasionally emit slightly malformed markup and OCR
text can contain ``<`` characters.  The parser below only relies on table
structure tags and never lets markup from a cell escape into the UI.
"""
from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
from typing import List, Optional, Tuple

from .models import TableData

_VOID_BR = re.compile(r"<br\s*/?>", re.I)
_TAG = re.compile(r"<[^>]{0,200}>")
_SPACE = re.compile(r"[ \t]+")


class _Cell(object):
    __slots__ = ("text", "rowspan", "colspan")

    def __init__(self, rowspan: int = 1, colspan: int = 1) -> None:
        self.text: List[str] = []
        self.rowspan = max(1, min(rowspan, 100))
        self.colspan = max(1, min(colspan, 50))

    def value(self) -> str:
        text = "".join(self.text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [_SPACE.sub(" ", ln).strip() for ln in text.split("\n")]
        # Remove repeated empty lines, keep the cell compact.
        compact = []
        for ln in lines:
            if ln or (compact and compact[-1]):
                compact.append(ln)
        return "\n".join(compact).strip()


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.rows: List[List[_Cell]] = []
        self._row: Optional[List[_Cell]] = None
        self._cell: Optional[_Cell] = None
        self._table_depth = 0
        self._saw_table = False
        self._ignore_nested = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._saw_table = True
            else:
                self._ignore_nested += 1
            return
        if self._ignore_nested:
            if tag == "tr":
                self._ignore_nested += 1
            return
        if tag == "tr":
            self._row = []
            self.rows.append(self._row)
            return
        if tag in ("td", "th"):
            if self._row is None:
                self._row = []
                self.rows.append(self._row)
            d = dict(attrs)
            try:
                rs = int(d.get("rowspan", 1) or 1)
            except ValueError:
                rs = 1
            try:
                cs = int(d.get("colspan", 1) or 1)
            except ValueError:
                cs = 1
            self._cell = _Cell(rs, cs)
            self._row.append(self._cell)
            return
        if tag == "br" and self._cell is not None:
            self._cell.text.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag.lower() == "br" and self._cell is not None:
            self._cell.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "table":
            if self._ignore_nested:
                self._ignore_nested -= 1
            self._table_depth = max(0, self._table_depth - 1)
            return
        if self._ignore_nested:
            return
        if tag in ("td", "th"):
            self._cell = None
            return
        if tag == "tr":
            self._row = None
            return
        if tag in ("p", "div", "li") and self._cell is not None:
            self._cell.text.append("\n")

    def handle_data(self, data: str) -> None:
        if self._cell is not None and not self._ignore_nested:
            self._cell.text.append(data)


def _normalise(raw_rows: List[List[_Cell]]) -> Tuple[List[List[str]], List[List[Tuple[int, int]]]]:
    raw_rows = [r for r in raw_rows if r]
    if not raw_rows:
        return [], []
    max_cols = 0
    for row in raw_rows:
        # occupancy width including rowspans from above is accounted for later;
        # this upper bound is enough to allocate the grid.
        max_cols = max(max_cols, sum(c.colspan for c in row))
    max_cols = max(1, min(max_cols, 200))
    n_rows = len(raw_rows)
    grid = [["" for _ in range(max_cols)] for _ in range(n_rows)]
    spans = [[(1, 1) for _ in range(max_cols)] for _ in range(n_rows)]
    occupied = [[False for _ in range(max_cols)] for _ in range(n_rows)]

    for r, row in enumerate(raw_rows):
        c = 0
        for cell in row:
            while c < max_cols and occupied[r][c]:
                c += 1
            if c >= max_cols:
                break
            value = cell.value()
            rs = min(cell.rowspan, n_rows - r)
            cs = min(cell.colspan, max_cols - c)
            grid[r][c] = value
            spans[r][c] = (rs, cs)
            for rr in range(r, r + rs):
                for cc in range(c, c + cs):
                    occupied[rr][cc] = True
                    if rr != r or cc != c:
                        grid[rr][cc] = ""
                        spans[rr][cc] = (0, 0)
            c += cs
    return grid, spans


def _fallback_table(html: str) -> TableData:
    text = _html.unescape(html or "")
    text = _VOID_BR.sub("\n", text)
    text = _TAG.sub("", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    grid = [[ln] for ln in lines]
    spans = [[(1, 1)] for _ in grid]
    return TableData(grid=grid, spans=spans, html=html or "")


def parse_table_html(html: str) -> TableData:
    """Parse model HTML into a rectangular grid with merge information."""
    if not html or "<t" not in html.lower():
        return _fallback_table(html)
    parser = _TableParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - malformed model output must not crash OCR
        return _fallback_table(html)
    grid, spans = _normalise(parser.rows)
    if not grid:
        return _fallback_table(html)
    return TableData(grid=grid, spans=spans, html=html)


def table_to_html(table: TableData, border: bool = True) -> str:
    """Render a table as a safe standalone HTML fragment."""
    if not table or not table.grid:
        return ""
    style = (
        ' style="border-collapse:collapse;width:100%;font-size:13px;"'
        if border else ""
    )
    out = ["<table%s>" % style]
    n_rows = len(table.grid)
    n_cols = max((len(r) for r in table.grid), default=0)
    for r in range(n_rows):
        out.append("<tr>")
        for c in range(n_cols):
            try:
                rs, cs = table.spans[r][c]
            except (IndexError, TypeError):
                rs, cs = (1, 1)
            if rs == 0 and cs == 0:
                continue
            value = table.grid[r][c] if c < len(table.grid[r]) else ""
            value = _html.escape(value or "").replace("\n", "<br/>")
            attrs = ""
            if rs > 1:
                attrs += ' rowspan="%d"' % rs
            if cs > 1:
                attrs += ' colspan="%d"' % cs
            td_style = (
                ' style="border:1px solid #cbd5e1;padding:5px 6px;'
                'vertical-align:top;white-space:pre-wrap;"' if border else ""
            )
            out.append("<td%s%s>%s</td>" % (attrs, td_style, value))
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def table_from_rows(rows: List[List[str]], bbox=None) -> TableData:
    """Build a TableData from an already expanded list of rows."""
    rows = [[str(c or "") for c in row] for row in rows if row]
    width = max((len(r) for r in rows), default=0)
    rows = [r + [""] * (width - len(r)) for r in rows]
    spans = [[(1, 1) for _ in range(width)] for _ in rows]
    return TableData(grid=rows, spans=spans, bbox=bbox)
