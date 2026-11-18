# -*- coding: utf-8 -*-
"""Document data model shared by the OCR pipeline, UI and exporters.

The model is deliberately plain Python (dataclasses only) so that it can be
used on the legacy Python 3.8 / Windows 7 build too.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

BBox = Tuple[int, int, int, int]


def _clean(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(lines).strip()


@dataclass
class TableData:
    """A reconstructed table.

    ``grid`` contains the visible/anchor value in every grid position and an
    empty string in positions covered by a merge.  ``spans[r][c]`` is
    ``(rowspan, colspan)`` and is ``(0, 0)`` for covered positions.
    """

    grid: List[List[str]] = field(default_factory=list)
    spans: List[List[Tuple[int, int]]] = field(default_factory=list)
    html: str = ""
    bbox: Optional[BBox] = None
    confidence: float = 1.0

    @property
    def n_rows(self) -> int:
        return len(self.grid)

    @property
    def n_cols(self) -> int:
        return max((len(r) for r in self.grid), default=0)

    def is_empty(self) -> bool:
        return not any(cell.strip() for row in self.grid for cell in row)

    def to_tsv(self) -> str:
        lines = []
        for row in self.grid:
            cells = [c.replace("\t", " ").replace("\n", " ") for c in row]
            lines.append("\t".join(cells))
        return "\n".join(lines)

    def to_text(self) -> str:
        lines = []
        for row in self.grid:
            lines.append(" | ".join(c for c in row if c.strip()))
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid": self.grid,
            "spans": [[list(s) for s in row] for row in self.spans],
            "html": self.html,
            "bbox": list(self.bbox) if self.bbox else None,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableData":
        spans = [[tuple(s) for s in row] for row in data.get("spans", [])]
        return cls(grid=data.get("grid", []), spans=spans,
                   html=data.get("html", ""),
                   bbox=tuple(data["bbox"]) if data.get("bbox") else None,
                   confidence=float(data.get("confidence", 1.0)))


@dataclass
class Block:
    kind: str = "text"  # title | heading | text | list | table | figure | header | footer
    text: str = ""
    bbox: Optional[BBox] = None
    table: Optional[TableData] = None
    level: int = 0
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "bbox": list(self.bbox) if self.bbox else None,
            "table": self.table.to_dict() if self.table else None,
            "level": self.level,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        table = TableData.from_dict(data["table"]) if data.get("table") else None
        return cls(kind=data.get("kind", "text"), text=data.get("text", ""),
                   bbox=tuple(data["bbox"]) if data.get("bbox") else None,
                   table=table, level=int(data.get("level", 0)),
                   confidence=float(data.get("confidence", 1.0)))


@dataclass
class PageResult:
    number: int = 1
    source: str = ""
    image_path: str = ""
    width: int = 0
    height: int = 0
    blocks: List[Block] = field(default_factory=list)
    elapsed: float = 0.0
    engine: str = ""
    warnings: List[str] = field(default_factory=list)

    def add_text(self, text: str, bbox: Optional[BBox] = None,
                 kind: str = "text", level: int = 0,
                 confidence: float = 1.0) -> None:
        text = _clean(text)
        if text:
            self.blocks.append(Block(kind=kind, text=text, bbox=bbox,
                                     level=level, confidence=confidence))

    def add_table(self, table: TableData, kind: str = "table") -> None:
        if table and not table.is_empty():
            self.blocks.append(Block(kind=kind, text=table.to_text(),
                                     bbox=table.bbox, table=table))

    def sort_blocks(self) -> None:
        self.blocks.sort(key=lambda b: (
            (b.bbox[1] if b.bbox else 0), (b.bbox[0] if b.bbox else 0)
        ))

    @property
    def plain_text(self) -> str:
        out = []
        for b in self.blocks:
            if b.kind == "table" and b.table:
                out.append(b.table.to_text())
            elif b.text:
                out.append(b.text)
        return "\n\n".join(out).strip()

    @property
    def tables(self) -> List[TableData]:
        return [b.table for b in self.blocks if b.kind == "table" and b.table]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "source": self.source,
            "image_path": self.image_path,
            "width": self.width,
            "height": self.height,
            "elapsed": round(self.elapsed, 3),
            "engine": self.engine,
            "warnings": self.warnings,
            "blocks": [b.to_dict() for b in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageResult":
        return cls(number=int(data.get("number", 1)),
                   source=data.get("source", ""),
                   image_path=data.get("image_path", ""),
                   width=int(data.get("width", 0)),
                   height=int(data.get("height", 0)),
                   blocks=[Block.from_dict(b) for b in data.get("blocks", [])],
                   elapsed=float(data.get("elapsed", 0.0)),
                   engine=data.get("engine", ""),
                   warnings=list(data.get("warnings", [])))


@dataclass
class DocumentResult:
    title: str = "未命名文档"
    source_path: str = ""
    pages: List[PageResult] = field(default_factory=list)
    created_at: str = ""
    engine: str = "PP-OCRv5 mobile · PP-Structure"
    elapsed: float = 0.0

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def plain_text(self) -> str:
        return "\n\n".join(p.plain_text for p in self.pages if p.plain_text)

    @property
    def tables(self) -> List[TableData]:
        out = []
        for page in self.pages:
            out.extend(page.tables)
        return out

    @property
    def total_tables(self) -> int:
        return len(self.tables)

    @property
    def total_chars(self) -> int:
        return sum(len(p.plain_text) for p in self.pages)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source_path": self.source_path,
            "created_at": self.created_at,
            "engine": self.engine,
            "elapsed": round(self.elapsed, 3),
            "pages": [p.to_dict() for p in self.pages],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentResult":
        return cls(title=data.get("title", "未命名文档"),
                   source_path=data.get("source_path", ""),
                   pages=[PageResult.from_dict(p) for p in data.get("pages", [])],
                   created_at=data.get("created_at", ""),
                   engine=data.get("engine", ""),
                   elapsed=float(data.get("elapsed", 0.0)))
