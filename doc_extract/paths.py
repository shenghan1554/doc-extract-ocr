# -*- coding: utf-8 -*-
"""Filesystem locations and small persistence helpers."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


APP_ROOT = _app_root()


def _default_models_dir() -> Path:
    env = os.environ.get("DOC_EXTRACT_MODELS")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        # PyInstaller one-folder keeps data under _internal; one-file extracts
        # to _MEIPASS.  Also accept a models folder beside the EXE.
        candidates = []
        mei = getattr(sys, "_MEIPASS", "")
        if mei:
            candidates.append(Path(mei) / "models")
        candidates.append(APP_ROOT / "models")
        candidates.append(APP_ROOT / "_internal" / "models")
        for candidate in candidates:
            if candidate.exists():
                return candidate
    return APP_ROOT / "models"


MODELS_DIR = _default_models_dir()
WORK_DIR = Path(tempfile.gettempdir()) / "doc_extract_work"
SETTINGS_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "DocExtract"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"
try:
    OUTPUT_DIR = Path.home() / "Documents" / "文档提取"
except Exception:  # noqa: BLE001
    OUTPUT_DIR = Path.home() / "文档提取"
ASSETS_DIR = APP_ROOT / "assets"


def ensure_dirs() -> None:
    for path in (MODELS_DIR, WORK_DIR, SETTINGS_DIR, OUTPUT_DIR):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            pass


def load_settings() -> dict:
    try:
        with open(str(SETTINGS_PATH), "r", encoding="utf-8") as fp:
            data = json.load(fp)
            return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def save_settings(data: dict) -> None:
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        with open(str(tmp), "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        os.replace(str(tmp), str(SETTINGS_PATH))
    except Exception:  # noqa: BLE001
        pass


def asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", APP_ROOT))
    else:
        base = ASSETS_DIR
    return base / name
