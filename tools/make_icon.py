# -*- coding: utf-8 -*-
"""Generate assets/icon.png and assets/icon.ico from the app logo."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEPS = ROOT / ".deps"
if DEPS.exists() and str(DEPS) not in sys.path:
    sys.path.insert(0, str(DEPS))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH",
                      str(DEPS / "PyQt5" / "Qt5" / "plugins" / "platforms"))
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PyQt5.QtWidgets import QApplication  # noqa: E402
from PyQt5.QtCore import Qt  # noqa: E402

from doc_extract.ui.icons import logo_pixmap  # noqa: E402


def main() -> None:
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    png = assets / "icon.png"
    logo_pixmap(256).save(str(png), "PNG")
    # Qt's ICO writer only writes one size; Pillow creates a multi-resolution
    # Windows icon from the PNG.
    try:
        from PIL import Image
        image = Image.open(str(png)).convert("RGBA")
        image.save(str(assets / "icon.ico"),
                   sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                          (64, 64), (128, 128), (256, 256)])
        print("saved", png, assets / "icon.ico")
    except Exception as exc:  # noqa: BLE001
        print("PNG saved; ICO failed:", exc)
    app.quit()


if __name__ == "__main__":
    main()
