# -*- coding: utf-8 -*-
"""环境自检：Python / 平台 / 依赖 / 模型 / CPU 推理后端。"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def line(name, value):
    print("%-22s %s" % (name, value))


def main() -> int:
    print("=" * 58)
    print(" 文档提取 · 环境自检")
    print("=" * 58)
    line("操作系统", platform.platform())
    line("Python", sys.version.replace("\n", " "))
    line("位数", platform.architecture()[0])
    line("CPU 核心", os.cpu_count())
    line("项目目录", ROOT)

    print("\n[依赖]")
    optional = []
    for name, module in [
        ("PyQt5", "PyQt5"), ("cv2", "cv2"), ("numpy", "numpy"),
        ("onnxruntime", "onnxruntime"), ("rapidocr", "rapidocr"),
        ("rapid_table", "rapid_table"), ("rapid_layout", "rapid_layout"),
        ("fitz", "fitz"), ("docx", "docx"), ("openpyxl", "openpyxl"),
        ("reportlab", "reportlab"),
    ]:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "")
            print("  [ok] %-14s %s" % (name, version))
        except Exception as exc:  # noqa: BLE001
            optional.append(name)
            print("  [--] %-14s %s" % (name, exc))

    print("\n[模型]")
    try:
        from doc_extract.paths import MODELS_DIR
        line("模型目录", MODELS_DIR)
        required = [
            "ch_PP-OCRv5_det_mobile.onnx",
            "ch_PP-OCRv5_rec_mobile.onnx",
            "ppocrv5_dict.txt",
            "layout_cdla.onnx",
            "ch_ppstructure_mobile_v2_SLANet.onnx",
        ]
        for name in required:
            path = MODELS_DIR / name
            print("  [%s] %-40s %.1f MB" %
                  ("ok" if path.exists() else "--", name,
                   path.stat().st_size / 1e6 if path.exists() else 0))
    except Exception as exc:  # noqa: BLE001
        print("  模型检查失败：", exc)
        return 1

    print("\n[推理]")
    try:
        import onnxruntime as ort
        line("ONNX Runtime", ort.__version__)
        line("Providers", ", ".join(ort.get_available_providers()))
    except Exception as exc:  # noqa: BLE001
        print("  ONNX Runtime 不可用：", exc)

    if optional:
        print("\n可选/缺失组件：%s" % ", ".join(optional))
        print("请运行 安装依赖.bat 或 安装依赖-Win7.bat。")
        return 1
    print("\n环境检查通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
