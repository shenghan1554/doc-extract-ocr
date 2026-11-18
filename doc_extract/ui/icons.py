# -*- coding: utf-8 -*-
"""Vector icons drawn with QPainter so the app needs no external icon files."""
from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (QColor, QFont, QIcon, QPainter, QPainterPath, QPen,
                         QPixmap, QPolygonF)

ACCENT = "#0F766E"
DARK = "#0F172A"


def _canvas(size: int = 64) -> tuple:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    return pm, p


def _icon_from_pixmap(pm: QPixmap) -> QIcon:
    return QIcon(pm)


def document_icon(color: str = ACCENT, size: int = 64) -> QIcon:
    pm, p = _canvas(size)
    s = size / 64.0
    pen = QPen(QColor(color), 4 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    rect = QRectF(15 * s, 8 * s, 34 * s, 48 * s)
    p.drawRoundedRect(rect, 5 * s, 5 * s)
    p.drawLine(QPointF(23 * s, 22 * s), QPointF(41 * s, 22 * s))
    p.drawLine(QPointF(23 * s, 31 * s), QPointF(41 * s, 31 * s))
    p.drawLine(QPointF(23 * s, 40 * s), QPointF(35 * s, 40 * s))
    p.end()
    return _icon_from_pixmap(pm)


def camera_icon(color: str = "#FFFFFF", size: int = 64) -> QIcon:
    pm, p = _canvas(size)
    s = size / 64.0
    pen = QPen(QColor(color), 3.6 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    body = QRectF(9 * s, 20 * s, 46 * s, 30 * s)
    p.drawRoundedRect(body, 7 * s, 7 * s)
    p.drawRoundedRect(QRectF(23 * s, 13 * s, 18 * s, 9 * s), 3 * s, 3 * s)
    p.drawEllipse(QRectF(25 * s, 27 * s, 15 * s, 15 * s))
    p.drawEllipse(QRectF(44 * s, 26 * s, 3 * s, 3 * s))
    p.end()
    return _icon_from_pixmap(pm)


def upload_icon(color: str = "#FFFFFF", size: int = 64) -> QIcon:
    pm, p = _canvas(size)
    s = size / 64.0
    pen = QPen(QColor(color), 4 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(32 * s, 10 * s), QPointF(32 * s, 39 * s))
    p.drawLine(QPointF(20 * s, 21 * s), QPointF(32 * s, 9 * s))
    p.drawLine(QPointF(44 * s, 21 * s), QPointF(32 * s, 9 * s))
    p.drawLine(QPointF(13 * s, 42 * s), QPointF(13 * s, 50 * s))
    p.drawLine(QPointF(13 * s, 50 * s), QPointF(51 * s, 50 * s))
    p.drawLine(QPointF(51 * s, 50 * s), QPointF(51 * s, 42 * s))
    p.end()
    return _icon_from_pixmap(pm)


def copy_icon(color: str = "#475569", size: int = 64) -> QIcon:
    pm, p = _canvas(size)
    s = size / 64.0
    pen = QPen(QColor(color), 3.4 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(22 * s, 9 * s, 30 * s, 38 * s), 4 * s, 4 * s)
    p.drawRoundedRect(QRectF(12 * s, 19 * s, 30 * s, 38 * s), 4 * s, 4 * s)
    p.end()
    return _icon_from_pixmap(pm)


def refresh_icon(color: str = "#475569", size: int = 64) -> QIcon:
    pm, p = _canvas(size)
    s = size / 64.0
    pen = QPen(QColor(color), 3.6 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(14 * s, 14 * s, 36 * s, 36 * s), 40 * 16, 280 * 16)
    p.drawLine(QPointF(48 * s, 12 * s), QPointF(48 * s, 24 * s))
    p.drawLine(QPointF(48 * s, 24 * s), QPointF(36 * s, 24 * s))
    p.end()
    return _icon_from_pixmap(pm)


def export_icon(kind: str, color: str = "#FFFFFF", size: int = 64) -> QIcon:
    pm, p = _canvas(size)
    s = size / 64.0
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(7 * s, 7 * s, 50 * s, 50 * s), 10 * s, 10 * s)
    label = {"docx": "W", "pdf": "PDF", "xlsx": "X"}.get(kind, "?")
    font = QFont("Arial", int((25 if kind != "pdf" else 17) * s))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, label)
    p.end()
    return _icon_from_pixmap(pm)


def logo_pixmap(size: int = 128) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    s = size / 128.0
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(ACCENT))
    p.drawRoundedRect(QRectF(0, 0, size, size), 26 * s, 26 * s)
    # document
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(34 * s, 23 * s, 58 * s, 78 * s), 8 * s, 8 * s)
    p.setBrush(QColor("#D1FAE5"))
    p.drawRoundedRect(QRectF(44 * s, 36 * s, 38 * s, 6 * s), 3 * s, 3 * s)
    p.drawRoundedRect(QRectF(44 * s, 50 * s, 30 * s, 6 * s), 3 * s, 3 * s)
    p.drawRoundedRect(QRectF(44 * s, 64 * s, 36 * s, 6 * s), 3 * s, 3 * s)
    # scan line
    pen = QPen(QColor("#5EEAD4"), 6 * s, Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(24 * s, 82 * s), QPointF(104 * s, 82 * s))
    # corner marks
    pen = QPen(QColor("#FFFFFF"), 5 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.drawLine(QPointF(17 * s, 44 * s), QPointF(17 * s, 25 * s))
    p.drawLine(QPointF(17 * s, 25 * s), QPointF(30 * s, 25 * s))
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(sz))
    return icon
