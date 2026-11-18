# -*- coding: utf-8 -*-
"""Background extraction worker."""
from __future__ import annotations

import logging
import threading
import traceback

from PyQt5.QtCore import QThread, pyqtSignal

from ..engine import DocumentExtractor, ExtractOptions, ExtractionCancelled

log = logging.getLogger(__name__)


class ExtractWorker(QThread):
    progress = pyqtSignal(str, int, str)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, input_path: str, options: ExtractOptions, parent=None) -> None:
        QThread.__init__(self, parent)
        self.input_path = input_path
        self.options = options
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            extractor = DocumentExtractor(options=self.options)
            result = extractor.extract(
                self.input_path,
                progress=lambda stage, pct, msg: self.progress.emit(stage, pct, msg),
                cancel=self.cancel_event,
            )
            self.succeeded.emit(result)
        except ExtractionCancelled:
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001
            log.error("extraction failed: %s\n%s", exc, traceback.format_exc())
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.cancel_event.set()
