# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 文档提取 (Windows 10/11, CPU)."""
from pathlib import Path

import PyQt5
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve()
DEPS = ROOT / ".deps"
QT_ROOT = Path(PyQt5.__file__).resolve().parent / "Qt5"

datas = [
    (str(ROOT / "models"), "models"),
    (str(ROOT / "assets"), "assets"),
]
binaries = []
hiddenimports = []

for package in ("rapidocr", "rapid_table", "rapid_layout",
                "omegaconf", "antlr4", "shapely", "pyclipper",
                "yaml", "tqdm", "colorlog", "requests", "chardet"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

# PyInstaller's Qt hook cannot resolve a non-ASCII install path via
# QLibraryInfo, so make sure the platform/image plugins are always present.
qt_plugins = QT_ROOT / "plugins"
allowed_plugin_dirs = {"platforms", "imageformats", "styles",
                       "iconengines", "accessibility", "platformthemes"}
if qt_plugins.exists():
    for plugin in qt_plugins.rglob("*"):
        if not plugin.is_file() or plugin.suffix.lower() not in (".dll", ".pyd"):
            continue
        rel = plugin.relative_to(qt_plugins)
        if rel.parts and rel.parts[0] not in allowed_plugin_dirs:
            continue
        datas.append((str(plugin),
                      str(Path("PyQt5") / "Qt5" / "plugins" / rel.parent)))

hiddenimports += [
    "rapidocr.inference_engine.onnxruntime",
    "rapid_table.table_structure.pp_structure",
    "rapid_layout.model_handler.pp",
    "fitz",
    "PIL._tkinter_finder",
]

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)] + ([str(DEPS)] if DEPS.exists() else []),
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas", "scipy", "torch",
              "torchvision", "paddle", "paddleocr", "IPython", "notebook"],
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
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
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
