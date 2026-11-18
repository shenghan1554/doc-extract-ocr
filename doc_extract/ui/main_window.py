# -*- coding: utf-8 -*-
"""Main window for 文档提取."""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QEvent, QSize, Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QFont, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                             QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QProgressBar,
                             QPushButton, QShortcut, QSizePolicy, QSpinBox,
                             QStackedWidget,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextBrowser, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..engine import ExtractOptions
from ..export import export_docx, export_pdf, export_xlsx
from ..models import DocumentResult, PageResult, TableData
from ..paths import (MODELS_DIR, OUTPUT_DIR, load_settings, save_settings)
from ..render import document_html, document_plain_text, tables_plain_text
from ..table_utils import table_to_html
from .camera import CameraDialog
from .icons import (app_icon, camera_icon, copy_icon, document_icon,
                    export_icon, logo_pixmap, upload_icon)
from .preview import PreviewView
from .theme import APP_QSS
from .worker import ExtractWorker

log = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
SUPPORTED = IMAGE_EXTS | {".pdf"}
DEFAULT_OPTIONS = {
    "output_dir": str(OUTPUT_DIR),
    "last_dir": str(Path.home() / "Documents"),
    "quality": "标准",
    "detect_tables": True,
    "keep_header_footer": False,
    "deskew": True,
    "threads": 0,
    "camera_index": -1,
}


def _safe_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n]+', "_", name or "识别结果").strip(" .")
    return (name or "识别结果")[:70]


class Card(QFrame):
    def __init__(self, parent=None) -> None:
        QFrame.__init__(self, parent)
        self.setObjectName("Card")


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None) -> None:
        QDialog.__init__(self, parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(520)
        self.settings = dict(settings)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)

        title = QLabel("设置")
        title.setStyleSheet("font-size:18px;font-weight:700;color:#0F172A;")
        lay.addWidget(title)
        tip = QLabel("设置仅影响本机，识别模型始终离线运行在 CPU 上。")
        tip.setObjectName("Muted")
        lay.addWidget(tip)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.addWidget(QLabel("默认导出目录"), 0, 0)
        self.output_edit = QLineEdit(str(self.settings.get("output_dir", OUTPUT_DIR)))
        grid.addWidget(self.output_edit, 0, 1)
        browse = QPushButton("浏览…")
        browse.setProperty("class", "secondary")
        browse.clicked.connect(self._browse)
        grid.addWidget(browse, 0, 2)

        grid.addWidget(QLabel("CPU 线程"), 1, 0)
        self.threads = QSpinBox()
        self.threads.setRange(0, 32)
        self.threads.setValue(int(self.settings.get("threads", 0) or 0))
        self.threads.setSpecialValueText("自动")
        grid.addWidget(self.threads, 1, 1)

        grid.addWidget(QLabel("识别选项"), 2, 0)
        opts = QVBoxLayout()
        self.keep_header = QCheckBox("保留页眉与页脚")
        self.keep_header.setChecked(bool(self.settings.get("keep_header_footer", False)))
        self.deskew = QCheckBox("自动纠偏（拍照倾斜时）")
        self.deskew.setChecked(bool(self.settings.get("deskew", True)))
        opts.addWidget(self.keep_header)
        opts.addWidget(self.deskew)
        grid.addLayout(opts, 2, 1, 1, 2)
        lay.addLayout(grid)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#E2E8F0;")
        lay.addWidget(line)
        about = QLabel(
            "文档提取 v%s\n作者：盛晗\n"
            "PP-OCRv5 mobile 文字识别 · PP-Structure 版面/表格还原\n"
            "ONNX Runtime CPU 推理 · 支持 Windows 7（兼容版）" % __version__
        )
        about.setObjectName("Muted")
        about.setWordWrap(True)
        lay.addWidget(about)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.setProperty("class", "secondary")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存设置")
        ok.setProperty("class", "primary")
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        lay.addLayout(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择默认导出目录",
                                                self.output_edit.text())
        if path:
            self.output_edit.setText(path)

    def values(self) -> dict:
        self.settings["output_dir"] = self.output_edit.text().strip() or str(OUTPUT_DIR)
        self.settings["threads"] = int(self.threads.value())
        self.settings["keep_header_footer"] = self.keep_header.isChecked()
        self.settings["deskew"] = self.deskew.isChecked()
        return self.settings


class MainWindow(QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)
        self.setObjectName("Root")
        self.setWindowTitle("%s v%s · PP-OCRv5" % (APP_NAME, __version__))
        self.setWindowIcon(app_icon())
        self.setAcceptDrops(True)
        self.resize(1280, 850)
        self.setMinimumSize(1020, 700)

        self.settings = dict(DEFAULT_OPTIONS)
        self.settings.update(load_settings())
        self.document: Optional[DocumentResult] = None
        self.worker: Optional[ExtractWorker] = None
        self.input_path: Optional[str] = None
        self._busy = False
        self._drag_path: Optional[str] = None
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._reset_status)

        self._build_ui()
        self._load_settings_to_ui()
        self._check_models()
        self._update_actions()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        QTimer.singleShot(120, self._show_window_ready)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(18, 16, 18, 12)
        body.setSpacing(14)
        body.addWidget(self._build_left_panel())
        body.addWidget(self._build_right_panel(), 1)
        root.addLayout(body, 1)
        root.addWidget(self._build_status_bar())

        self._add_shortcut("Ctrl+O", self._choose_file)
        self._add_shortcut("Ctrl+P", self._open_camera)
        self._add_shortcut("Ctrl+S", lambda: self._export("docx"))
        self._add_shortcut("Ctrl+Shift+S", lambda: self._export("pdf"))

    def _add_shortcut(self, key: str, callback) -> None:
        sc = QShortcut(QKeySequence(key), self)
        sc.activated.connect(callback)
        self._shortcuts = getattr(self, "_shortcuts", [])
        self._shortcuts.append(sc)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(78)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(22, 10, 22, 10)
        lay.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(46))
        logo.setFixedSize(46, 46)
        lay.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        t = QLabel(APP_NAME)
        t.setObjectName("AppTitle")
        sub = QLabel("PP-OCRv5 mobile · PP-Structure · 离线 CPU 识别 · v%s" % __version__)
        sub.setObjectName("AppSubtitle")
        titles.addWidget(t)
        titles.addWidget(sub)
        lay.addLayout(titles)
        lay.addStretch(1)

        self.model_badge = QLabel("模型检查中…")
        self.model_badge.setObjectName("BadgeReady")
        lay.addWidget(self.model_badge)

        self.settings_btn = QPushButton("设置")
        self.settings_btn.setProperty("class", "ghost")
        self.settings_btn.setToolTip("导出目录、CPU 线程与识别选项")
        self.settings_btn.clicked.connect(self._open_settings)
        lay.addWidget(self.settings_btn)

        self.camera_btn = QPushButton(" 拍照识别")
        self.camera_btn.setProperty("class", "secondary")
        self.camera_btn.setIcon(camera_icon("#0F172A", 40))
        self.camera_btn.setIconSize(QSize(18, 18))
        self.camera_btn.clicked.connect(self._open_camera)
        lay.addWidget(self.camera_btn)

        self.upload_btn = QPushButton(" 上传识别")
        self.upload_btn.setProperty("class", "primary")
        self.upload_btn.setIcon(upload_icon("#FFFFFF", 40))
        self.upload_btn.setIconSize(QSize(18, 18))
        self.upload_btn.clicked.connect(self._choose_file)
        lay.addWidget(self.upload_btn)
        return header

    def _build_left_panel(self) -> QWidget:
        card = Card()
        card.setMinimumWidth(290)
        card.setMaximumWidth(360)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(9)

        top = QHBoxLayout()
        label = QLabel("文档预览")
        label.setObjectName("SectionTitle")
        top.addWidget(label)
        top.addStretch(1)
        self.boxes_check = QCheckBox("版面框")
        self.boxes_check.setChecked(True)
        self.boxes_check.toggled.connect(self._toggle_boxes)
        top.addWidget(self.boxes_check)
        lay.addLayout(top)

        self.preview = PreviewView()
        self.preview.setMinimumHeight(330)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.preview, 1)

        self.page_list = QListWidget()
        self.page_list.setObjectName("Pages")
        self.page_list.setViewMode(QListWidget.IconMode)
        self.page_list.setIconSize(QSize(48, 64))
        self.page_list.setGridSize(QSize(60, 76))
        self.page_list.setSpacing(2)
        self.page_list.setMovement(QListWidget.Static)
        self.page_list.setResizeMode(QListWidget.Adjust)
        self.page_list.setWrapping(False)
        self.page_list.setFixedHeight(82)
        self.page_list.setVisible(False)
        self.page_list.currentRowChanged.connect(self._on_page_changed)
        lay.addWidget(self.page_list)

        self.file_meta = QLabel("尚未选择文件")
        self.file_meta.setObjectName("Muted")
        self.file_meta.setWordWrap(True)
        lay.addWidget(self.file_meta)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#E2E8F0;")
        lay.addWidget(line)

        opts_title = QLabel("识别选项")
        opts_title.setObjectName("SectionTitle")
        lay.addWidget(opts_title)
        row = QHBoxLayout()
        row.addWidget(QLabel("清晰度"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["极速", "标准", "高清"])
        self.quality_combo.setToolTip("标准适合大多数文档；高清更利于小字，耗时更长。")
        row.addWidget(self.quality_combo, 1)
        lay.addLayout(row)
        self.tables_check = QCheckBox("识别表格（PP-Structure）")
        self.tables_check.setChecked(True)
        lay.addWidget(self.tables_check)
        self.deskew_check = QCheckBox("自动纠偏")
        self.deskew_check.setChecked(True)
        lay.addWidget(self.deskew_check)

        tip = QLabel("模型全部在本地 CPU 运行，文件不会上传网络。")
        tip.setObjectName("Tiny")
        tip.setWordWrap(True)
        lay.addWidget(tip)
        return card

    def _build_right_panel(self) -> QWidget:
        card = Card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_empty_page())
        self.stack.addWidget(self._build_processing_page())
        self.stack.addWidget(self._build_result_page())
        lay.addWidget(self.stack, 1)
        return card

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 20, 30, 20)
        lay.addStretch(1)
        icon = QLabel()
        icon.setPixmap(document_icon("#0F766E", 96).pixmap(76, 76))
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        title = QLabel("把文档变成可编辑文字")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:23px;font-weight:700;color:#0F172A;")
        lay.addWidget(title)
        sub = QLabel("拍照或上传图片 / PDF，自动还原文字、版面与表格\n识别结果可直接复制，并导出 Word、PDF、Excel")
        sub.setAlignment(Qt.AlignCenter)
        sub.setObjectName("Muted")
        sub.setStyleSheet("color:#64748B;font-size:12px;line-height:1.7;")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        lay.addSpacing(10)
        row = QHBoxLayout()
        row.addStretch(1)
        camera = QPushButton("  拍照识别")
        camera.setProperty("class", "secondary")
        camera.setIcon(camera_icon("#0F172A", 40))
        camera.setIconSize(QSize(18, 18))
        camera.clicked.connect(self._open_camera)
        upload = QPushButton("  上传图片 / PDF")
        upload.setProperty("class", "primary")
        upload.setIcon(upload_icon("#FFFFFF", 40))
        upload.setIconSize(QSize(18, 18))
        upload.clicked.connect(self._choose_file)
        row.addWidget(camera)
        row.addWidget(upload)
        row.addStretch(1)
        lay.addLayout(row)
        formats = QLabel("JPG · PNG · BMP · TIFF · PDF    单文件最多 100 页")
        formats.setAlignment(Qt.AlignCenter)
        formats.setObjectName("Tiny")
        lay.addWidget(formats)

        drop = QFrame()
        drop.setObjectName("DropZone")
        drop.setMinimumHeight(92)
        dl = QVBoxLayout(drop)
        dl.setContentsMargins(16, 10, 16, 10)
        hint = QLabel("也可以将文件拖到窗口中")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#64748B;font-size:12px;")
        dl.addWidget(hint)
        lay.addSpacing(10)
        lay.addWidget(drop)
        lay.addStretch(2)
        return page

    def _build_processing_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        icon = QLabel()
        icon.setPixmap(logo_pixmap(84))
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        title = QLabel("正在识别文档")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:20px;font-weight:700;color:#0F172A;")
        lay.addWidget(title)
        self.processing_stage = QLabel("正在加载模型…")
        self.processing_stage.setAlignment(Qt.AlignCenter)
        self.processing_stage.setObjectName("Muted")
        lay.addWidget(self.processing_stage)
        note = QLabel("首次识别需加载模型，请稍候；识别过程完全在本地进行。")
        note.setAlignment(Qt.AlignCenter)
        note.setObjectName("Tiny")
        lay.addWidget(note)
        lay.addStretch(2)
        return page

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(22, 14, 18, 8)
        hl.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        self.result_title = QLabel("识别结果")
        self.result_title.setObjectName("ResultTitle")
        self.result_title.setWordWrap(False)
        self.result_stats = QLabel("")
        self.result_stats.setObjectName("Stat")
        self.result_stats.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        titles.addWidget(self.result_title)
        titles.addWidget(self.result_stats)
        hl.addLayout(titles, 1)
        self.copy_btn = QPushButton(" 复制全文")
        self.copy_btn.setProperty("class", "ghost")
        self.copy_btn.setIcon(copy_icon("#475569", 40))
        self.copy_btn.setIconSize(QSize(17, 17))
        self.copy_btn.setToolTip("复制全部文字；若在结果中选中了文字则复制选中部分")
        self.copy_btn.clicked.connect(self._copy_all)
        hl.addWidget(self.copy_btn)
        lay.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(20, 0, 20, 0)
        self.result_view = QTextBrowser()
        self.result_view.setOpenExternalLinks(False)
        self.result_view.setStyleSheet(
            "QTextBrowser{background:#FFFFFF;border:none;padding:4px 8px 12px 8px;}"
        )
        self.tabs.addTab(self.result_view, "识别结果")
        self.tables_page = self._build_tables_page()
        self.tabs.addTab(self.tables_page, "表格 (0)")
        lay.addWidget(self.tabs, 1)
        lay.addWidget(self._build_export_bar())
        return page

    def _build_tables_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 12, 4, 8)
        lay.setSpacing(8)
        top = QHBoxLayout()
        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(220)
        self.table_combo.currentIndexChanged.connect(self._show_table)
        top.addWidget(QLabel("选择表格"))
        top.addWidget(self.table_combo)
        top.addStretch(1)
        self.table_info = QLabel("")
        self.table_info.setObjectName("Muted")
        top.addWidget(self.table_info)
        copy = QPushButton(" 复制表格")
        copy.setProperty("class", "ghost")
        copy.setIcon(copy_icon("#475569", 40))
        copy.setIconSize(QSize(16, 16))
        copy.clicked.connect(self._copy_table)
        top.addWidget(copy)
        lay.addLayout(top)
        self.table_view = QTableWidget()
        self.table_view.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_view.setWordWrap(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.verticalHeader().setDefaultSectionSize(30)
        lay.addWidget(self.table_view, 1)
        return page

    def _build_export_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("ExportBar")
        bar.setFixedHeight(64)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 10, 18, 10)
        lab = QLabel("导出")
        lab.setObjectName("SectionTitle")
        lay.addWidget(lab)
        lay.addSpacing(4)
        self.word_btn = QPushButton(" Word")
        self.word_btn.setProperty("class", "export")
        self.word_btn.setIcon(export_icon("docx", "#2563EB", 36))
        self.word_btn.setIconSize(QSize(18, 18))
        self.word_btn.clicked.connect(lambda: self._export("docx"))
        lay.addWidget(self.word_btn)
        self.pdf_btn = QPushButton(" PDF")
        self.pdf_btn.setProperty("class", "export")
        self.pdf_btn.setIcon(export_icon("pdf", "#DC2626", 36))
        self.pdf_btn.setIconSize(QSize(18, 18))
        self.pdf_btn.clicked.connect(lambda: self._export("pdf"))
        lay.addWidget(self.pdf_btn)
        self.excel_btn = QPushButton(" 表格")
        self.excel_btn.setProperty("class", "export")
        self.excel_btn.setIcon(export_icon("xlsx", "#059669", 36))
        self.excel_btn.setIconSize(QSize(18, 18))
        self.excel_btn.clicked.connect(lambda: self._export("xlsx"))
        lay.addWidget(self.excel_btn)
        lay.addStretch(1)
        self.folder_btn = QPushButton("打开导出目录")
        self.folder_btn.setProperty("class", "ghost")
        self.folder_btn.clicked.connect(self._open_output_dir)
        lay.addWidget(self.folder_btn)
        return bar

    def _build_status_bar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(40)
        bar.setStyleSheet("QFrame{background:#FFFFFF;border-top:1px solid #E2E8F0;}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 4, 18, 4)
        lay.setSpacing(10)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color:#10B981;font-size:10px;")
        lay.addWidget(self.status_dot)
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("Muted")
        lay.addWidget(self.status_label)
        lay.addStretch(1)
        self.progress_frame = QWidget()
        pl = QHBoxLayout(self.progress_frame)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(8)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("Muted")
        self.progress = QProgressBar()
        self.progress.setFixedWidth(210)
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "danger")
        self.cancel_btn.setFixedHeight(25)
        self.cancel_btn.clicked.connect(self._cancel)
        pl.addWidget(self.progress_label)
        pl.addWidget(self.progress)
        pl.addWidget(self.cancel_btn)
        lay.addWidget(self.progress_frame)
        self.progress_frame.setVisible(False)
        self.engine_label = QLabel("离线 · CPU")
        self.engine_label.setObjectName("Tiny")
        lay.addWidget(self.engine_label)
        return bar

    # ------------------------------------------------------------- settings
    def _load_settings_to_ui(self) -> None:
        quality = self.settings.get("quality", "标准")
        idx = self.quality_combo.findText(quality)
        self.quality_combo.setCurrentIndex(idx if idx >= 0 else 1)
        self.tables_check.setChecked(bool(self.settings.get("detect_tables", True)))
        self.deskew_check.setChecked(bool(self.settings.get("deskew", True)))

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec_() == QDialog.Accepted:
            self.settings = dlg.values()
            save_settings(self.settings)
            self.deskew_check.setChecked(bool(self.settings.get("deskew", True)))
            self._toast("设置已保存")

    def _check_models(self) -> None:
        required = [
            "ch_PP-OCRv5_det_mobile.onnx",
            "ch_PP-OCRv5_rec_mobile.onnx",
            "ppocrv5_dict.txt",
            "layout_cdla.onnx",
            "ch_ppstructure_mobile_v2_SLANet.onnx",
        ]
        missing = [n for n in required if not (Path(MODELS_DIR) / n).exists()]
        if missing:
            self.model_badge.setText("缺少 %d 个模型" % len(missing))
            self.model_badge.setObjectName("BadgeWarn")
            self.model_badge.setStyleSheet(
                "color:#B45309;background:#FFFBEB;border:1px solid #FDE68A;"
                "border-radius:10px;padding:4px 10px;font-size:11px;font-weight:600;"
            )
            self.model_badge.setToolTip(
                "请将模型放入 %s：\n%s" % (MODELS_DIR, "\n".join(missing))
            )
        else:
            self.model_badge.setText("模型就绪 · CPU")
            self.model_badge.setObjectName("BadgeReady")
            self.model_badge.setToolTip(str(MODELS_DIR))

    def _show_window_ready(self) -> None:
        self._reset_status()

    # --------------------------------------------------------------- actions
    def _choose_file(self) -> None:
        if self._busy:
            return
        start = self.settings.get("last_dir") or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "选择要识别的文档", start,
            "支持的文档 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.pdf);;"
            "图片 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;PDF (*.pdf);;所有文件 (*.*)",
        )
        if path:
            self.settings["last_dir"] = str(Path(path).parent)
            save_settings(self.settings)
            self.start_extraction(path)

    def _open_camera(self) -> None:
        if self._busy:
            return
        try:
            preferred = int(self.settings.get("camera_index", -1))
        except (TypeError, ValueError):
            preferred = -1
        dlg = CameraDialog(self, preferred_index=preferred)
        if dlg.exec_() == QDialog.Accepted and dlg.captured_path:
            if dlg.opened_index >= 0:
                self.settings["camera_index"] = dlg.opened_index
                save_settings(self.settings)
            self.start_extraction(dlg.captured_path)
        dlg.deleteLater()

    def _open_output_dir(self) -> None:
        path = Path(self.settings.get("output_dir", str(OUTPUT_DIR)))
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            path = Path.home()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ------------------------------------------------------------ extraction
    def start_extraction(self, path: str) -> None:
        if self._busy:
            return
        p = Path(path)
        if not p.exists():
            self._error("文件不存在", "找不到文件：\n%s" % path)
            return
        if p.suffix.lower() not in SUPPORTED:
            self._error("不支持的文件", "仅支持 JPG / PNG / BMP / TIFF / PDF 文件。")
            return
        self.input_path = str(p)
        try:
            size_mb = p.stat().st_size / 1024.0 / 1024.0
        except Exception:  # noqa: BLE001
            size_mb = 0
        if size_mb > 80:
            self._error("文件过大", "文件超过 80 MB，请先压缩或拆分后再识别。")
            return
        self._set_busy(True)
        self.stack.setCurrentIndex(1)
        self.processing_stage.setText("正在加载模型…")
        self.progress_frame.setVisible(True)
        self.progress.setValue(0)
        self.progress_label.setText("准备中")
        self.file_meta.setText("%s\n%.1f MB · 正在识别" % (p.name, size_mb))
        self.preview.clear()
        self.preview.set_placeholder("正在读取文档…")
        self.page_list.clear()
        self.page_list.setVisible(False)
        self.result_title.setText(p.stem)
        self.result_stats.setText("处理中…")
        self._status("正在识别：%s" % p.name, "#0F766E")

        quality = {"极速": "fast", "标准": "standard", "高清": "high"}.get(
            self.quality_combo.currentText(), "standard")
        options = ExtractOptions(
            quality=quality,
            detect_tables=self.tables_check.isChecked(),
            keep_header_footer=bool(self.settings.get("keep_header_footer", False)),
            deskew=self.deskew_check.isChecked(),
            ocr_threads=int(self.settings.get("threads", 0) or 0),
        )
        self.worker = ExtractWorker(str(p), options, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.succeeded.connect(self._on_success)
        self.worker.failed.connect(self._on_failed)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_progress(self, stage: str, pct: int, msg: str) -> None:
        self.progress.setValue(max(0, min(100, int(pct))))
        self.progress_label.setText(stage)
        self.processing_stage.setText(msg)
        self.status_label.setText(msg)
        self.progress_frame.setVisible(True)

    def _on_success(self, result: DocumentResult) -> None:
        self.document = result
        # The pipeline normally derives a title from the first page; keep the
        # file stem as a fallback for documents without a detected heading.
        if not result.title or result.title == "未命名文档":
            result.title = Path(result.source_path).stem or "识别结果"
        self._set_busy(False)
        self.progress_frame.setVisible(False)
        self.stack.setCurrentIndex(2)
        self.result_title.setText(result.title or "识别结果")
        self.result_title.setToolTip(result.source_path)
        self.result_stats.setText(
            "%d 页  ·  %d 个表格  ·  %d 字  ·  %.1f 秒" %
            (len(result.pages), result.total_tables, result.total_chars,
             result.elapsed)
        )
        self.result_view.setHtml(document_html(result))
        self._populate_tables()
        self._populate_pages()
        self._update_actions()
        if result.pages:
            page = result.pages[0]
            self.preview.set_image(page.image_path, page.blocks,
                                   self.boxes_check.isChecked())
            meta = "%s\n%d × %d px · 第 1 / %d 页" % (
                Path(result.source_path).name, page.width, page.height,
                len(result.pages))
            self.file_meta.setText(meta)
        self._status("识别完成，用时 %.1f 秒" % result.elapsed, "#10B981")
        self._toast("识别完成，可复制或导出")

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.progress_frame.setVisible(False)
        self.stack.setCurrentIndex(0 if self.document is None else 2)
        self._status("识别失败", "#DC2626")
        self._error("识别失败", message)

    def _on_cancelled(self) -> None:
        self._set_busy(False)
        self.progress_frame.setVisible(False)
        self.stack.setCurrentIndex(0 if self.document is None else 2)
        self._status("已取消", "#D97706")
        self._toast("已取消本次识别")

    def _on_worker_finished(self) -> None:
        self.worker = None
        self._update_actions()

    def _cancel(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("正在取消…")
            self._status("正在取消…", "#D97706")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.upload_btn.setEnabled(not busy)
        self.camera_btn.setEnabled(not busy)
        self.settings_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("取消")
        if not busy:
            self.progress_frame.setVisible(False)
        self._update_actions()

    def _update_actions(self) -> None:
        ready = self.document is not None and not self._busy
        for btn in (getattr(self, "word_btn", None),
                    getattr(self, "pdf_btn", None),
                    getattr(self, "excel_btn", None),
                    getattr(self, "copy_btn", None)):
            if btn is not None:
                btn.setEnabled(ready)

    # --------------------------------------------------------------- results
    def _populate_pages(self) -> None:
        self.page_list.clear()
        if not self.document:
            self.page_list.setVisible(False)
            return
        if len(self.document.pages) <= 1:
            self.page_list.setVisible(False)
            return
        for page in self.document.pages:
            pm = QPixmap(page.image_path)
            icon = QIcon()
            if not pm.isNull():
                icon = QIcon(pm.scaled(48, 64, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation))
            item = QListWidgetItem(icon, str(page.number))
            item.setTextAlignment(Qt.AlignHCenter)
            item.setToolTip("第 %d 页" % page.number)
            self.page_list.addItem(item)
        self.page_list.setVisible(True)
        self.page_list.setCurrentRow(0)

    def _on_page_changed(self, row: int) -> None:
        if not self.document or row < 0 or row >= len(self.document.pages):
            return
        page = self.document.pages[row]
        self.preview.set_image(page.image_path, page.blocks,
                               self.boxes_check.isChecked())
        self.file_meta.setText(
            "%s\n%d × %d px · 第 %d / %d 页" %
            (Path(self.document.source_path).name, page.width, page.height,
             row + 1, len(self.document.pages))
        )

    def _toggle_boxes(self, checked: bool) -> None:
        self.preview.set_boxes_visible(checked)

    def _populate_tables(self) -> None:
        self.table_combo.blockSignals(True)
        self.table_combo.clear()
        tables = self.document.tables if self.document else []
        for i, table in enumerate(tables, 1):
            self.table_combo.addItem("表格 %d  ·  %d 行 × %d 列" %
                                     (i, table.n_rows, table.n_cols), i - 1)
        self.table_combo.blockSignals(False)
        self.tabs.setTabText(1, "表格 (%d)" % len(tables))
        if tables:
            self.table_combo.setCurrentIndex(0)
            self._show_table(0)
        else:
            self.table_view.clear()
            self.table_view.setRowCount(0)
            self.table_view.setColumnCount(0)
            self.table_info.setText("未识别到表格")
        self._update_actions()

    def _show_table(self, index: int) -> None:
        if not self.document or index < 0:
            return
        tables = self.document.tables
        if index >= len(tables):
            return
        table = tables[index]
        rows, cols = table.n_rows, table.n_cols
        self.table_view.clear()
        self.table_view.setRowCount(rows)
        self.table_view.setColumnCount(cols)
        self.table_view.setHorizontalHeaderLabels(
            ["列 %d" % (c + 1) for c in range(cols)])
        self.table_view.setVerticalHeaderLabels(
            [str(r + 1) for r in range(rows)])
        for r in range(rows):
            for c in range(cols):
                try:
                    rs, cs = table.spans[r][c]
                except (IndexError, TypeError):
                    rs, cs = (1, 1)
                if rs == 0 and cs == 0:
                    continue
                item = QTableWidgetItem(table.grid[r][c] if c < len(table.grid[r]) else "")
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table_view.setItem(r, c, item)
                if rs > 1 or cs > 1:
                    self.table_view.setSpan(r, c, rs, cs)
        self.table_view.resizeRowsToContents()
        self.table_info.setText("%d 行 × %d 列" % (rows, cols))

    def _copy_all(self) -> None:
        if not self.document:
            return
        cursor = self.result_view.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n")
            self._clipboard(text, "已复制选中内容")
            return
        text = document_plain_text(self.document)
        self._clipboard(text, "已复制全文")

    def _copy_table(self) -> None:
        if not self.document:
            return
        idx = self.table_combo.currentIndex()
        tables = self.document.tables
        if idx < 0 or idx >= len(tables):
            return
        self._clipboard(tables[idx].to_tsv(), "已复制表格（制表符分隔，可粘贴到 Excel）")

    def _clipboard(self, text: str, message: str) -> None:
        QApplication.clipboard().setText(text or "")
        self._toast(message)

    # ---------------------------------------------------------------- export
    def _export(self, kind: str) -> None:
        if not self.document or self._busy:
            return
        out_dir = Path(self.settings.get("output_dir", str(OUTPUT_DIR)))
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            out_dir = Path.home()
        name = _safe_filename(self.document.title)
        ext = {"docx": ".docx", "pdf": ".pdf", "xlsx": ".xlsx"}[kind]
        label = {"docx": "Word 文档 (*.docx)", "pdf": "PDF 文件 (*.pdf)",
                 "xlsx": "Excel 表格 (*.xlsx)"}[kind]
        title = {"docx": "导出 Word", "pdf": "导出 PDF", "xlsx": "导出表格"}[kind]
        default = str(out_dir / (name + "_识别结果" + ext))
        path, _ = QFileDialog.getSaveFileName(self, title, default, label)
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if kind == "docx":
                result = export_docx(self.document, path)
            elif kind == "pdf":
                result = export_pdf(self.document, path)
            else:
                result = export_xlsx(self.document, path)
        except Exception as exc:  # noqa: BLE001
            log.exception("export failed")
            self._error("导出失败", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.settings["output_dir"] = str(Path(result).parent)
        save_settings(self.settings)
        self._status("已导出：%s" % Path(result).name, "#10B981")
        self._export_done(result)

    def _export_done(self, path: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("导出成功")
        box.setIcon(QMessageBox.Information)
        box.setText("文件已保存：")
        box.setInformativeText(path)
        open_file = box.addButton("打开文件", QMessageBox.AcceptRole)
        open_dir = box.addButton("打开文件夹", QMessageBox.ActionRole)
        box.addButton("完成", QMessageBox.RejectRole)
        box.exec_()
        clicked = box.clickedButton()
        if clicked == open_file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        elif clicked == open_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))

    # -------------------------------------------------------------- utilities
    def _status(self, text: str, color: str = "#10B981") -> None:
        self.status_dot.setStyleSheet("color:%s;font-size:10px;" % color)
        self.status_label.setText(text)
        self._status_timer.stop()

    def _reset_status(self) -> None:
        if self._busy:
            return
        self.status_dot.setStyleSheet("color:#10B981;font-size:10px;")
        if self.document:
            self.status_label.setText(
                "就绪 · 上次识别 %d 页 / %d 个表格" %
                (len(self.document.pages), self.document.total_tables))
        else:
            self.status_label.setText("就绪")

    def _toast(self, message: str) -> None:
        self._status(message, "#0F766E")
        self._status_timer.start(4200)

    def _error(self, title: str, message: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Warning)
        box.setText(title)
        box.setInformativeText(message)
        box.setDetailedText(message)
        box.exec_()

    # ------------------------------------------------------------- drag/drop
    def _drop_path(self, mime) -> Optional[str]:
        """Return the first supported local file path from a drag payload."""
        if mime is None or not mime.hasUrls():
            return None
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            try:
                candidate = Path(path)
            except Exception:  # noqa: BLE001
                continue
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED:
                return str(candidate)
        return None

    def _drag_hint(self, path: Optional[str]) -> None:
        if path:
            self._status("松开鼠标即可识别：%s" % Path(path).name, "#0F766E")
        elif not self._busy:
            self._reset_status()

    def dragEnterEvent(self, event) -> None:
        if self._busy:
            event.ignore()
            return
        path = self._drop_path(event.mimeData())
        if path:
            self._drag_path = path
            self._drag_hint(path)
            event.acceptProposedAction()
        else:
            self._drag_hint(None)
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self._busy and self._drop_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drag_path = None
        self._drag_hint(None)

    def dropEvent(self, event) -> None:
        path = self._drop_path(event.mimeData())
        self._drag_path = None
        self._drag_hint(None)
        if self._busy:
            event.ignore()
            return
        if path:
            self.start_extraction(path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def eventFilter(self, obj, event) -> bool:
        """Accept file drops over child widgets, not just the window margin.

        QTextBrowser, QGraphicsView and QLabel all cover the main window and
        would otherwise swallow Explorer drags.  An application-level filter
        makes the whole window a drop target.
        """
        etype = event.type()
        if etype not in (QEvent.DragEnter, QEvent.DragMove,
                         QEvent.DragLeave, QEvent.Drop):
            return QWidget.eventFilter(self, obj, event)
        if QApplication.activeModalWidget() is not None:
            return False
        target = obj if isinstance(obj, QWidget) else None
        if target is not None and target.window() is not self:
            return False
        if etype == QEvent.DragEnter:
            self.dragEnterEvent(event)
            return True
        if etype == QEvent.DragMove:
            self.dragMoveEvent(event)
            return True
        if etype == QEvent.DragLeave:
            self.dragLeaveEvent(event)
            return False
        self.dropEvent(event)
        return True

    # ---------------------------------------------------------------- close
    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            ans = QMessageBox.question(
                self, "正在识别",
                "文档仍在识别中，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ans != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.cancel()
            if not self.worker.wait(4000):
                QMessageBox.information(self, "请稍候", "正在结束识别任务，请稍后再关闭。")
                event.ignore()
                return
        self.settings["last_dir"] = self.settings.get("last_dir", str(Path.home()))
        self.settings["quality"] = self.quality_combo.currentText()
        self.settings["detect_tables"] = self.tables_check.isChecked()
        save_settings(self.settings)
        event.accept()
