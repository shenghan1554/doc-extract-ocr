# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 5.13.2 spec for the Windows 7 / Python 3.8 build."""
from pathlib import Path

import PyQt5
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve()
if not (ROOT / "assets").exists():
    ROOT = ROOT.parent
QT_ROOT = Path(PyQt5.__file__).resolve().parent / "Qt5"

datas = [
    (str(ROOT / "models"), "models"),
    (str(ROOT / "assets"), "assets"),
]
binaries = []
hiddenimports = []

for package in ("rapidocr", "rapid_table", "rapid_layout",
                "omegaconf", "antlr4", "shapely", "pyclipper",
                "yaml", "tqdm", "colorlog", "requests", "chardet",
                "reportlab", "docx", "lxml", "openpyxl", "fitz", "cv2",
                "certifi"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

# Ensure Qt's platform/image plugins are present even when the build path is
# non-ASCII (QLibraryInfo cannot represent such paths on Windows).
qt_plugins = QT_ROOT / "plugins"
allowed = {"platforms", "imageformats", "styles", "iconengines",
           "accessibility", "platformthemes"}
if qt_plugins.exists():
    for plugin in qt_plugins.rglob("*"):
        if not plugin.is_file() or plugin.suffix.lower() != ".dll":
            continue
        rel = plugin.relative_to(qt_plugins)
        if rel.parts and rel.parts[0] not in allowed:
            continue
        datas.append((str(plugin),
                      str(Path("PyQt5") / "Qt5" / "plugins" / rel.parent)))

hiddenimports += [
    "rapidocr.inference_engine.onnxruntime",
    "rapid_table.table_structure.pp_structure",
    "rapid_layout",
    "fitz",
    "lxml._elementpath",
    "lxml.etree",
    "docx",
]

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas", "scipy", "torch",
              "torchvision", "paddle", "paddleocr", "IPython", "notebook",
              "tensorflow", "openvino"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="文档提取",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "icon.ico"),
    version=str(ROOT / "installer" / "version_info.txt"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="文档提取",
)

