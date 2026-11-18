# -*- coding: utf-8 -*-
"""Camera capture dialog.

UVC ("driver-free") cameras are opened through DirectShow first, then Media
Foundation, then OpenCV's automatic backend.  Opening an index successfully is
not enough: some cameras (especially UVC devices on Windows 7) need a few
frames of warm-up, so the dialog waits for a real frame before enabling the
capture button.
"""
from __future__ import annotations

import datetime as _dt
import time
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout,
                             QLabel, QPushButton, QShortcut, QSizePolicy,
                             QVBoxLayout)

from ..paths import WORK_DIR

DARK_QSS = r"""
QDialog { background: #0B1220; }
QLabel { color: #E2E8F0; }
QLabel#CamTitle { font-size: 17px; font-weight: 700; color: #FFFFFF; }
QLabel#CamHint { color: #94A3B8; font-size: 11px; }
QLabel#Video {
    background: #020617;
    border: 1px solid #1E293B;
    border-radius: 12px;
    color: #64748B;
}
QComboBox {
    background: #111C2E;
    color: #E2E8F0;
    border: 1px solid #26344A;
    border-radius: 7px;
    padding: 5px 9px;
}
QPushButton {
    background: #16233A;
    color: #E2E8F0;
    border: 1px solid #26344A;
    border-radius: 8px;
    padding: 9px 16px;
}
QPushButton:hover { background: #1E2E48; }
QPushButton#Capture {
    background: #0F766E;
    color: white;
    border: none;
    font-weight: 700;
    padding: 11px 26px;
}
QPushButton#Capture:hover { background: #0D9488; }
QPushButton#Capture:disabled { background: #334155; color: #94A3B8; }
"""

MAX_CAMERA_INDEX = 8


class CameraDialog(QDialog):
    def __init__(self, parent=None, preferred_index: int = -1) -> None:
        QDialog.__init__(self, parent)
        self.setWindowTitle("拍照识别")
        self.setStyleSheet(DARK_QSS)
        self.setMinimumSize(940, 680)
        self.resize(1000, 720)
        self.captured_path: Optional[str] = None
        self._cap = None
        self._frame = None
        self._cv2 = None
        self._fail_count = 0
        self._opened_index = -1
        self._preferred = preferred_index
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._build()
        self._space_shortcut = QShortcut(Qt.Key_Space, self)
        self._space_shortcut.activated.connect(self._capture)
        self._timer.start()
        self._auto_open()

    # ------------------------------------------------------------------ UI
    @property
    def opened_index(self) -> int:
        return self._opened_index

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(12)

        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        t = QLabel("拍照识别")
        t.setObjectName("CamTitle")
        hint = QLabel("免驱 USB 摄像头 · 将文档平放，保持光线均匀")
        hint.setObjectName("CamHint")
        titles.addWidget(t)
        titles.addWidget(hint)
        top.addLayout(titles)
        top.addStretch(1)
        self.device_combo = QComboBox()
        self.device_combo.addItem("自动检测摄像头", -1)
        for i in range(MAX_CAMERA_INDEX):
            self.device_combo.addItem("摄像头 %d" % (i + 1), i)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        top.addWidget(self.device_combo)
        refresh = QPushButton("重新检测")
        refresh.clicked.connect(self._rescan)
        top.addWidget(refresh)
        lay.addLayout(top)

        self.video = QLabel("正在检测免驱 USB 摄像头…")
        self.video.setObjectName("Video")
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(820, 480)
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.video, 1)

        bottom = QHBoxLayout()
        self.status = QLabel("正在尝试 DirectShow / Media Foundation 后端…")
        self.status.setObjectName("CamHint")
        bottom.addWidget(self.status)
        bottom.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        bottom.addWidget(cancel)
        self.capture_btn = QPushButton("拍照并识别")
        self.capture_btn.setObjectName("Capture")
        self.capture_btn.setEnabled(False)
        self.capture_btn.clicked.connect(self._capture)
        bottom.addWidget(self.capture_btn)
        lay.addLayout(bottom)

    # ------------------------------------------------------------- camera core
    def _load_cv2(self) -> bool:
        if self._cv2 is not None:
            return self._cv2 is not False
        try:
            import cv2
            self._cv2 = cv2
            return True
        except Exception:  # noqa: BLE001
            self._cv2 = False
            return False

    def _backends(self) -> List[Tuple[int, str]]:
        cv2 = self._cv2
        out = []
        for name, label in (("CAP_DSHOW", "DirectShow"),
                            ("CAP_MSMF", "Media Foundation"),
                            ("CAP_ANY", "自动")):
            value = getattr(cv2, name, None)
            if value is not None and all(value != item[0] for item in out):
                out.append((int(value), label))
        return out

    def _configure(self, cap, high: bool = True) -> None:
        cv2 = self._cv2
        # MJPG is the most compatible format for UVC cameras at 720p/1080p,
        # but some cheap devices only deliver frames at 640x480.  Try both.
        if high:
            try:
                cap.set(cv2.CAP_PROP_FOURCC,
                        cv2.VideoWriter_fourcc(*"MJPG"))
            except Exception:  # noqa: BLE001
                pass
        size = (1280, 720) if high else (640, 480)
        for prop, value in (
            (cv2.CAP_PROP_FRAME_WIDTH, size[0]),
            (cv2.CAP_PROP_FRAME_HEIGHT, size[1]),
            (cv2.CAP_PROP_FPS, 30),
            (cv2.CAP_PROP_BUFFERSIZE, 1),
        ):
            try:
                cap.set(prop, value)
            except Exception:  # noqa: BLE001
                pass

    def _try_index(self, index: int):
        """Try all backends and two UVC profiles for one index."""
        cv2 = self._cv2
        for backend, label in self._backends():
            for high in (True, False):
                cap = None
                try:
                    cap = cv2.VideoCapture(index, backend)
                except Exception:  # noqa: BLE001
                    cap = None
                if cap is None or not cap.isOpened():
                    if cap is not None:
                        try:
                            cap.release()
                        except Exception:  # noqa: BLE001
                            pass
                    break
                self._configure(cap, high=high)
                # UVC devices often return False for the first several reads.
                for _ in range(12):
                    try:
                        ok, frame = cap.read()
                    except Exception:  # noqa: BLE001
                        ok, frame = False, None
                    if ok and frame is not None and frame.size:
                        return cap, frame, label
                    time.sleep(0.06)
                try:
                    cap.release()
                except Exception:  # noqa: BLE001
                    pass
        return None, None, ""

    def _auto_open(self) -> None:
        self._release()
        self._frame = None
        self.capture_btn.setEnabled(False)
        self.video.clear()
        self.video.setText("正在检测免驱 USB 摄像头…\n首次打开可能需要 1–3 秒")
        self.status.setText("正在尝试 DirectShow / Media Foundation 后端…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._scan_and_open()
        finally:
            QApplication.restoreOverrideCursor()

    def _scan_and_open(self) -> None:
        if not self._load_cv2():
            self._show_unavailable("未安装摄像头组件（opencv-python）。")
            return
        order = list(range(MAX_CAMERA_INDEX))
        if self._preferred in order:
            order.remove(self._preferred)
            order.insert(0, self._preferred)
        QApplication.processEvents()
        for index in order:
            self.status.setText("正在检测摄像头 %d / %d…" % (index + 1, MAX_CAMERA_INDEX))
            QApplication.processEvents()
            cap, frame, backend = self._try_index(index)
            if cap is None:
                continue
            self._cap = cap
            self._frame = frame
            self._opened_index = index
            self._fail_count = 0
            self._select_combo(index)
            self._timer.start()
            self.capture_btn.setEnabled(True)
            self.status.setText(
                "摄像头 %d 已连接（%s）。点击「拍照并识别」或按空格键拍照。"
                % (index + 1, backend)
            )
            self.video.setStyleSheet("")
            self._show_frame(frame)
            return
        self._show_unavailable(
            "未检测到可用的免驱 USB 摄像头。\n\n"
            "已尝试 DirectShow / Media Foundation 后端，索引 1–%d。\n"
            "请检查：\n"
            "• USB 摄像头是否插好，设备管理器「图像设备」是否正常；\n"
            "• 摄像头是否被微信、钉钉、相机等程序占用；\n"
            "• Windows 7 请确认已安装 UVC 驱动和 VC++ 运行库。\n"
            "也可以改用「上传识别」。"
            % MAX_CAMERA_INDEX
        )

    def _select_combo(self, index: int) -> None:
        pos = index + 1
        if 0 <= pos < self.device_combo.count():
            self.device_combo.blockSignals(True)
            self.device_combo.setCurrentIndex(pos)
            self.device_combo.blockSignals(False)

    def _rescan(self) -> None:
        self.device_combo.blockSignals(True)
        self.device_combo.setCurrentIndex(0)
        self.device_combo.blockSignals(False)
        self._preferred = -1
        self._auto_open()

    def _on_device_changed(self, _index: int = -1) -> None:
        index = self.device_combo.currentData()
        if index is None:
            return
        index = int(index)
        if index < 0:
            self._preferred = -1
            self._auto_open()
            return
        self._preferred = index
        self._release()
        self._frame = None
        self.capture_btn.setEnabled(False)
        self.video.setText("正在打开摄像头 %d…" % (index + 1))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            cap, frame, backend = self._try_index(index)
        finally:
            QApplication.restoreOverrideCursor()
        if cap is None:
            self._show_unavailable(
                "无法打开摄像头 %d。\n"
                "它可能被其他程序占用，或不是可用的 UVC 设备。\n"
                "可点击「重新检测」扫描其他摄像头。\n"
                "也可以改用「上传识别」。" % (index + 1)
            )
            return
        self._cap = cap
        self._frame = frame
        self._opened_index = index
        self._fail_count = 0
        self._timer.start()
        self.capture_btn.setEnabled(True)
        self.video.setStyleSheet("")
        self.status.setText(
            "摄像头 %d 已连接（%s）。点击「拍照并识别」或按空格键拍照。"
            % (index + 1, backend)
        )
        self._show_frame(frame)

    def _show_unavailable(self, text: str) -> None:
        self._timer.stop()
        self._release()
        self._frame = None
        self.capture_btn.setEnabled(False)
        self.video.clear()
        self.video.setText(text)
        self.video.setStyleSheet(
            "background:#020617;color:#94A3B8;border:1px solid #1E293B;"
            "border-radius:12px;font-size:13px;padding:20px;"
        )
        self.status.setText("摄像头不可用，可改用「上传识别」。")

    def _release(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:  # noqa: BLE001
                pass
            self._cap = None
        self._opened_index = -1

    # --------------------------------------------------------------- live view
    def _show_frame(self, frame) -> None:
        rgb = frame[:, :, ::-1].copy()
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(image)
        target = self.video.size()
        self.video.setPixmap(pm.scaled(target, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation))

    def _tick(self) -> None:
        if self._cap is None:
            return
        try:
            ok, frame = self._cap.read()
        except Exception:  # noqa: BLE001
            ok, frame = False, None
        if not ok or frame is None or not frame.size:
            self._fail_count += 1
            if self._fail_count == 35:
                self.status.setText(
                    "摄像头已连接，但持续没有画面；可能被其他程序占用。"
                    "可点击「重新检测」或改用上传识别。"
                )
            return
        self._fail_count = 0
        self._frame = frame
        self._show_frame(frame)
        if not self.capture_btn.isEnabled():
            self.capture_btn.setEnabled(True)

    def _capture(self) -> None:
        if self._cap is None:
            return
        if self._frame is None:
            try:
                ok, frame = self._cap.read()
            except Exception:  # noqa: BLE001
                ok, frame = False, None
            if not ok or frame is None:
                self.status.setText("还没有画面，请稍等一秒再拍。")
                return
            self._frame = frame
        try:
            cv2 = self._cv2
            WORK_DIR.mkdir(parents=True, exist_ok=True)
            stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = Path(WORK_DIR) / ("capture_%s.png" % stamp)
            ok, encoded = cv2.imencode(".png", self._frame)
            if not ok:
                raise RuntimeError("照片编码失败")
            # ndarray.tofile handles non-ASCII Windows paths reliably.
            encoded.tofile(str(path))
            if not path.exists() or path.stat().st_size < 1024:
                raise RuntimeError("照片保存失败")
            self.captured_path = str(path)
            self.accept()
        except Exception as exc:  # noqa: BLE001
            self.status.setText("拍照失败：%s" % exc)

    # ------------------------------------------------------------------ close
    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._release()
        QDialog.closeEvent(self, event)

    def reject(self) -> None:
        self._timer.stop()
        self._release()
        QDialog.reject(self)
