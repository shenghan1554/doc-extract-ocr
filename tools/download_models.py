# -*- coding: utf-8 -*-
"""Download the offline PP-OCRv5 / PP-Structure ONNX model pack.

Usage:
    python tools/download_models.py [--check] [--dir models]

The models are the same public PaddleOCR models used by RapidOCR and
RapidTable, exported to ONNX.  Downloading them once makes the desktop app
fully offline.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "ch_PP-OCRv5_det_mobile.onnx": {
        "url": "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/"
               "v3.10.0/onnx/PP-OCRv5/det/ch_PP-OCRv5_det_mobile.onnx",
        # Upstream is ONNX IR 10; Windows 7 build uses ORT 1.17 (max IR 9).
        "source_sha256": "4d97c44a20d30a81aad087d6a396b08f786c4635742afc391f6621f5c6ae78ae",
        "sha256": "df9029acca09cf62d86f987b25ab1e5aa6aec9dad7fad7a45f7baf6bb42fe4b4",
        "ir8": True,
        "size": 5_100_000,
    },
    "ch_PP-OCRv5_rec_mobile.onnx": {
        "url": "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/"
               "v3.10.0/onnx/PP-OCRv5/rec/ch_PP-OCRv5_rec_mobile.onnx",
        "source_sha256": "5825fc7ebf84ae7a412be049820b4d86d77620f204a041697b0494669b1742c5",
        "sha256": "7d5a05a77cc32d7409d7a1fec71d6501d2a154a02298a0d2a860aa1b703a7cc2",
        "ir8": True,
        "size": 16_600_000,
    },
    "ppocrv5_dict.txt": {
        "url": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/"
               "ppocr/utils/dict/ppocrv5_dict.txt",
        "sha256": "d1979e9f794c464c0d2e0b70a7fe14dd978e9dc644c0e71f14158cdf8342af1b",
        "size": 74_000,
    },
    "layout_cdla.onnx": {
        "url": "https://www.modelscope.cn/models/RapidAI/RapidLayout/resolve/"
               "v1.2.0/onnx/pp_layout/layout_cdla.onnx",
        "sha256": "25b1f27ec56aa932a48f30cbd6293c358a156280f4b20b0a973bab210c39f62c",
        "size": 7_400_000,
    },
    "ch_ppstructure_mobile_v2_SLANet.onnx": {
        "url": "https://www.modelscope.cn/models/RapidAI/RapidTable/resolve/"
               "v2.0.0/ch_ppstructure_mobile_v2_SLANet.onnx",
        "sha256": "ddfc6c97ee4db2a5e9de4de8b6a14508a39d42d228503219fdfebfac364885e3",
        "size": 7_800_000,
    },
}
HEADERS = {"User-Agent": "DocExtract/1.0 (+offline OCR)"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fp:
        while True:
            chunk = fp.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def fix_ir8(path: Path) -> None:
    """Lower ONNX IR version for ONNX Runtime 1.14 (Windows 7)."""
    try:
        import onnx
    except ImportError:
        raise RuntimeError(
            "需要 onnx 包来把模型 IR 版本降到 9。请先安装 requirements-win7.txt。")
    model = onnx.load(str(path), load_external_data=False)
    if model.ir_version > 8:
        model.ir_version = 8
        onnx.save(model, str(path))


def check(models_dir: Path, quiet: bool = False) -> bool:
    ok = True
    for name, meta in FILES.items():
        path = models_dir / name
        if not path.exists():
            print("[missing] %s" % name)
            ok = False
            continue
        if path.stat().st_size < 1000:
            print("[bad]     %s" % name)
            ok = False
            continue
        digest = sha256(path)
        if digest.lower() == meta["sha256"]:
            if not quiet:
                print("[ok]      %s (%.1f MB)" % (name, path.stat().st_size / 1e6))
            continue
        if meta.get("ir8") and digest.lower() == meta.get("source_sha256"):
            try:
                fix_ir8(path)
                digest = sha256(path)
                if digest.lower() == meta["sha256"]:
                    if not quiet:
                        print("[fixed]   %s (ONNX IR 8)" % name)
                    continue
            except Exception as exc:  # noqa: BLE001
                print("[ir8]     %s: %s" % (name, exc))
                ok = False
                continue
        print("[hash]    %s\n          expected %s\n          actual   %s" %
              (name, meta["sha256"], digest))
        ok = False
    return ok


def download(name: str, meta: dict, models_dir: Path) -> None:
    dest = models_dir / name
    if dest.exists():
        digest = sha256(dest)
        if digest.lower() == meta["sha256"]:
            print("[cached]  %s" % name)
            return
        if meta.get("ir8") and digest.lower() == meta.get("source_sha256"):
            fix_ir8(dest)
            if sha256(dest).lower() == meta["sha256"]:
                print("[cached]  %s (IR 8)" % name)
                return
    tmp = dest.with_suffix(dest.suffix + ".part")
    url = meta["url"]
    for attempt in range(4):
        try:
            print("[get]     %s" % name, flush=True)
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp, \
                    open(str(tmp), "wb") as fp:
                total = int(resp.headers.get("content-length") or 0)
                done = 0
                last = time.time()
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    fp.write(chunk)
                    done += len(chunk)
                    if time.time() - last > 1.0:
                        pct = (" %.0f%%" % (done * 100.0 / total)) if total else ""
                        print("          %.1f MB%s" % (done / 1e6, pct), flush=True)
                        last = time.time()
            if tmp.stat().st_size < 1000:
                raise RuntimeError("empty file")
            actual = sha256(tmp)
            if actual.lower() not in (meta["sha256"], meta.get("source_sha256")):
                raise RuntimeError("SHA256 mismatch: %s" % actual)
            if meta.get("ir8") and actual.lower() == meta.get("source_sha256"):
                fix_ir8(tmp)
                actual = sha256(tmp)
                if actual.lower() != meta["sha256"]:
                    raise RuntimeError("IR8 fix failed: %s" % actual)
            os.replace(str(tmp), str(dest))
            print("[saved]   %s (%.1f MB)" % (name, dest.stat().st_size / 1e6))
            return
        except Exception as exc:  # noqa: BLE001
            print("          retry %d/4: %s" % (attempt + 1, exc))
            try:
                tmp.unlink()
            except OSError:
                pass
            time.sleep(2 + attempt)
    raise SystemExit("Download failed: %s\nPlease download it manually from:\n%s" %
                     (name, url))


def main() -> int:
    parser = argparse.ArgumentParser(description="下载文档提取离线模型")
    parser.add_argument("--check", action="store_true", help="只校验，不下载")
    parser.add_argument("--dir", default=str(ROOT / "models"),
                        help="模型目录，默认 ./models")
    args = parser.parse_args()
    models_dir = Path(args.dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    if args.check:
        return 0 if check(models_dir) else 1
    print("模型将保存到：%s" % models_dir)
    for name, meta in FILES.items():
        download(name, meta, models_dir)
    return 0 if check(models_dir) else 1


if __name__ == "__main__":
    sys.exit(main())
