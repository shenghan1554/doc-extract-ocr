# -*- coding: utf-8 -*-
"""Apply a small Python 3.8 compatibility patch to RapidLayout.

RapidLayout 0.1.x/0.2.x advertise Python 3.6+ but use PEP 585 annotations such
as ``tuple[int, int, int]`` at class-definition time, which fails on Python 3.8.
Adding ``from __future__ import annotations`` makes those annotations lazy and
keeps the package usable on the Windows 7 compatibility stack.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def patch() -> int:
    spec = importlib.util.find_spec("rapid_layout")
    if spec is None or not spec.submodule_search_locations:
        print("rapid_layout 未安装，跳过。")
        return 1
    root = Path(list(spec.submodule_search_locations)[0])
    patched = 0
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if text.lstrip().startswith("from __future__ import annotations"):
            continue
        path.write_text("from __future__ import annotations\n" + text,
                        encoding="utf-8")
        patched += 1
    print("已修补 rapid_layout：%d 个文件 (%s)" % (patched, root))
    # RapidTable 3.0.2 passes pathlib.Path to onnxruntime.InferenceSession,
    # which is not accepted by ONNX Runtime 1.14 (Windows 7 build).
    table_spec = importlib.util.find_spec("rapid_table")
    if table_spec and table_spec.submodule_search_locations:
        table_root = Path(list(table_spec.submodule_search_locations)[0])
        table_main = table_root / "inference_engine" / "onnxruntime" / "main.py"
        if table_main.exists():
            source = table_main.read_text(encoding="utf-8")
            if "str(model_path)," not in source and "            model_path,\n            sess_options=sess_opt," in source:
                source = source.replace(
                    "            model_path,\n            sess_options=sess_opt,",
                    "            str(model_path),\n            sess_options=sess_opt,")
                table_main.write_text(source, encoding="utf-8")
                print("已修补 rapid_table 的 Path 兼容性。")
    try:
        import rapid_layout  # noqa: F401
        print("rapid_layout 导入正常。")
        return 0
    except Exception as exc:  # noqa: BLE001
        print("rapid_layout 导入失败：%s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(patch())
