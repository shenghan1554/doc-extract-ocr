# -*- coding: utf-8 -*-
"""文档提取 entry point."""
from __future__ import annotations

import io
import logging
import os
import sys
import tempfile
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

# PyInstaller's windowed bootloader leaves sys.stdout/stderr as None.  Some
# third-party OCR helpers (tqdm inside RapidTable) call .write() on them and
# would otherwise fail the whole table step.  Give them a harmless sink.
_STDIO_KEEP = []
for _name in ("stdout", "stderr"):
    if getattr(sys, _name, None) is None:
        try:
            _stream = open(os.devnull, "w", encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            _stream = io.StringIO()
        setattr(sys, _name, _stream)
        _STDIO_KEEP.append(_stream)
if getattr(sys, "stdin", None) is None:
    try:
        sys.stdin = open(os.devnull, "r", encoding="utf-8", errors="replace")
        _STDIO_KEEP.append(sys.stdin)
    except Exception:  # noqa: BLE001
        sys.stdin = io.StringIO("")

# Development builds keep dependencies in .deps so the source tree remains
# portable.  Installed builds simply don't have this folder.
_ROOT = Path(__file__).resolve().parent
_DEPS = _ROOT / ".deps"
if _DEPS.exists() and str(_DEPS) not in sys.path:
    sys.path.insert(0, str(_DEPS))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMessageBox

from doc_extract import APP_NAME, __version__
from doc_extract.paths import SETTINGS_DIR, ensure_dirs
from doc_extract.ui.icons import app_icon
from doc_extract.ui.main_window import MainWindow
from doc_extract.ui.theme import APP_QSS

log = logging.getLogger(__name__)


def setup_logging() -> None:
    ensure_dirs()
    log_dir = SETTINGS_DIR / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            str(log_dir / "app.log"), maxBytes=2 * 1024 * 1024, backupCount=3,
            encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(handler)
    except Exception:  # noqa: BLE001
        pass


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log.error("uncaught exception:\n%s", text)
    try:
        box = QMessageBox()
        box.setWindowTitle("程序遇到问题")
        box.setIcon(QMessageBox.Critical)
        box.setText("程序遇到未处理的错误，但已记录日志。")
        box.setInformativeText(str(exc_value))
        box.setDetailedText(text)
        box.exec_()
    except Exception:  # noqa: BLE001
        pass


def _self_test(path: str) -> int:
    """Headless OCR/export check used by the packaged-build verification."""
    from doc_extract.engine import DocumentExtractor, ExtractOptions
    from doc_extract.export import export_docx, export_pdf, export_xlsx

    out_dir = Path(tempfile.gettempdir()) / "doc_extract_self_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = DocumentExtractor(options=ExtractOptions()).extract(
        path, progress=lambda stage, pct, msg: print("[%3d%%] %s %s" % (pct, stage, msg)))
    export_docx(result, str(out_dir / "self_test.docx"))
    export_pdf(result, str(out_dir / "self_test.pdf"))
    export_xlsx(result, str(out_dir / "self_test.xlsx"))
    report = {
        "ok": True, "title": result.title, "pages": len(result.pages),
        "tables": result.total_tables, "chars": result.total_chars,
        "elapsed": round(result.elapsed, 2), "output": str(out_dir),
        "warnings": [w for page in result.pages for w in page.warnings],
    }
    (out_dir / "report.json").write_text(
        __import__("json").dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(__import__("json").dumps(report, ensure_ascii=False))
    return 0


def main() -> int:
    setup_logging()
    if "--self-test" in sys.argv:
        idx = sys.argv.index("--self-test")
        if idx + 1 >= len(sys.argv):
            print("usage: 文档提取.exe --self-test <image-or-pdf>")
            return 2
        try:
            return _self_test(sys.argv[idx + 1])
        except Exception:  # noqa: BLE001
            log.error("self-test failed:\n%s", traceback.format_exc())
            print(traceback.format_exc())
            return 1
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "DocExtract.PPOCRv5.1")
        except Exception:  # noqa: BLE001
            pass
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # Derive Qt locations from the package directory rather than
    # QLibraryInfo: on Windows, QLibraryInfo returns "?" for non-ASCII paths,
    # which breaks plugin discovery when the app lives under a Chinese folder.
    try:
        import PyQt5
        qt_root = Path(PyQt5.__file__).resolve().parent / "Qt5"
        plugin_dir = qt_root / "plugins"
        bin_dir = qt_root / "bin"
        if plugin_dir.exists():
            QApplication.addLibraryPath(str(plugin_dir))
            platforms = plugin_dir / "platforms"
            if platforms.exists() and not os.environ.get(
                    "QT_QPA_PLATFORM_PLUGIN_PATH"):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
            os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_dir))
        if bin_dir.exists() and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(bin_dir))
    except Exception:  # noqa: BLE001
        pass
    if os.name == "nt" and Path(r"C:\Windows\Fonts").exists():
        os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName("%s v%s" % (APP_NAME, __version__))
    app.setOrganizationName("盛晗")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    # Fusion is consistent on Windows 7 and 10/11 and works well with QSS.
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(APP_QSS)
    sys.excepthook = _excepthook

    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        # Used by the packaging check; no effect in normal use.
        from PyQt5.QtCore import QTimer
        target = os.environ.get("DOC_EXTRACT_SMOKE")
        if target:
            def _shot() -> None:
                window.grab().save(target)
                app.quit()
            QTimer.singleShot(1800, _shot)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
