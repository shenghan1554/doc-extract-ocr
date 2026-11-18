# -*- coding: utf-8 -*-
"""Image preview canvas with layout-block overlays."""
from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView

from ..models import Block

COLORS = {
    "title": "#2563EB",
    "heading": "#7C3AED",
    "table": "#059669",
    "caption": "#D97706",
    "figure": "#64748B",
    "text": "#94A3B8",
}


class PreviewView(QGraphicsView):
    def __init__(self, parent=None) -> None:
        QGraphicsView.__init__(self, parent)
        self.setObjectName("Preview")
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._box_items: List[QGraphicsRectItem] = []
        self._auto_fit = True
        self._show_boxes = True
        self._placeholder = "拖入图片或 PDF\n或点击「上传识别」"
        self._blocks: List[Block] = []

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        self.viewport().update()

    def clear(self) -> None:
        self._scene.clear()
        self._pixmap_item = None
        self._box_items = []
        self._blocks = []
        self.viewport().update()

    def set_image(self, path: str, blocks: Optional[List[Block]] = None,
                  show_boxes: bool = True) -> None:
        pm = QPixmap(path)
        if pm.isNull():
            self.clear()
            return
        self._scene.clear()
        self._box_items = []
        self._pixmap_item = self._scene.addPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))
        self._blocks = blocks or []
        self._show_boxes = show_boxes
        if show_boxes:
            self._draw_boxes()
        self._auto_fit = True
        self.fit()
        # The view may not have its final size until the surrounding layout has
        # been processed, so fit again on the next event-loop turn.
        QTimer.singleShot(0, self.fit)

    def showEvent(self, event) -> None:
        QGraphicsView.showEvent(self, event)
        if self._pixmap_item is not None and self._auto_fit:
            QTimer.singleShot(0, self.fit)

    def _draw_boxes(self) -> None:
        if not self._pixmap_item:
            return
        font = QFont("Microsoft YaHei UI", 8)
        for block in self._blocks:
            if not block.bbox:
                continue
            x1, y1, x2, y2 = block.bbox
            if x2 <= x1 or y2 <= y1:
                continue
            color = QColor(COLORS.get(block.kind, "#94A3B8"))
            pen = QPen(color, 2.2)
            pen.setCosmetic(True)
            item = QGraphicsRectItem(QRectF(x1, y1, x2 - x1, y2 - y1))
            item.setPen(pen)
            item.setBrush(QBrush(Qt.NoBrush))
            item.setZValue(2)
            self._scene.addItem(item)
            self._box_items.append(item)
            if block.kind in ("table", "title") and (x2 - x1) > 40:
                label = "表格" if block.kind == "table" else "标题"
                text_item = self._scene.addSimpleText(label, font)
                text_item.setBrush(color)
                text_item.setPos(x1 + 3, max(0, y1 - 17))
                text_item.setZValue(3)
                self._box_items.append(text_item)

    def set_boxes_visible(self, visible: bool) -> None:
        self._show_boxes = visible
        if not self._pixmap_item:
            return
        if visible:
            if not self._box_items:
                self._draw_boxes()
            for item in self._box_items:
                item.setVisible(True)
        else:
            for item in self._box_items:
                item.setVisible(False)

    def fit(self) -> None:
        if not self._pixmap_item:
            self.resetTransform()
            return
        self._auto_fit = True
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def actual_size(self) -> None:
        self._auto_fit = False
        self.resetTransform()

    def zoom(self, factor: float) -> None:
        self._auto_fit = False
        self.scale(factor, factor)

    def resizeEvent(self, event) -> None:
        QGraphicsView.resizeEvent(self, event)
        if self._auto_fit and self._pixmap_item:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
            event.accept()
            return
        QGraphicsView.wheelEvent(self, event)

    def paintEvent(self, event) -> None:
        QGraphicsView.paintEvent(self, event)
        if self._pixmap_item is None:
            p = QPainter(self.viewport())
            p.setRenderHint(QPainter.Antialiasing, True)
            rect = self.viewport().rect()
            p.setPen(QColor("#94A3B8"))
            font = QFont("Microsoft YaHei UI")
            font.setPixelSize(13)
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, self._placeholder)
            p.end()
