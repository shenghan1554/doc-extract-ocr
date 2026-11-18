# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller hook that repairs Qt paths on non-ASCII Windows install folders.

QLibraryInfo returns '?' for non-ASCII paths, so PyInstaller's stock Qt hooks
cannot find PyQt5/Qt5/plugins.  Derive every location from the actual PyQt5
package directory instead.
"""
from pathlib import Path

import PyQt5
from PyInstaller.utils.hooks.qt import get_qt_library_info

info = get_qt_library_info("PyQt5")
qt_root = Path(PyQt5.__file__).resolve().parent / "Qt5"
locations = {
    "PrefixPath": qt_root,
    "BinariesPath": qt_root / "bin",
    "LibrariesPath": qt_root / "lib",
    "LibraryExecutablesPath": qt_root / "bin",
    "PluginsPath": qt_root / "plugins",
    "TranslationsPath": qt_root / "translations",
    "DataPath": qt_root,
    "SettingsPath": qt_root,
    "ImportsPath": qt_root / "imports",
    "QmlPath": qt_root / "qml",
    "ArchDataPath": qt_root,
}
for key, value in locations.items():
    if value.exists():
        info.location[key] = str(value)

hiddenimports, binaries, datas = info.collect_module("PyQt5.QtWidgets")
