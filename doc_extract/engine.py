# -*- coding: utf-8 -*-
"""Offline OCR pipeline: PP-OCRv5 mobile + PP-Structure (ONNX Runtime).

Models
------
* PP-OCRv5 mobile detection / recognition (PaddleOCR models exported to ONNX)
* PP-Structure layout model (CDLA) for page regions
* PP-Structure SLANet table structure model for editable tables

Everything runs on the CPU through ONNX Runtime, which keeps the application
usable on older Windows machines (including a Python 3.8 + ORT 1.17 build for
Windows 7).
"""
from __future__ import annotations

import math
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .models import BBox, Block, DocumentResult, PageResult, TableData
from .table_utils import table_to_html
from .paths import MODELS_DIR, WORK_DIR

ProgressFn = Callable[[str, int, str], None]


class ModelMissingError(RuntimeError):
    pass


class ExtractionCancelled(RuntimeError):
    pass


@dataclass
class ExtractOptions:
    quality: str = "standard"          # fast | standard | high
    detect_tables: bool = True
    keep_header_footer: bool = False
    deskew: bool = True
    max_pages: int = 100
    dpi: int = 180
    ocr_threads: int = 0


@dataclass
class OCRLine:
    text: str
    score: float
    box: np.ndarray                    # 4x2 float32
    bbox: BBox = (0, 0, 0, 0)

    def __post_init__(self) -> None:
        x1 = int(np.floor(self.box[:, 0].min()))
        y1 = int(np.floor(self.box[:, 1].min()))
        x2 = int(np.ceil(self.box[:, 0].max()))
        y2 = int(np.ceil(self.box[:, 1].max()))
        self.bbox = (x1, y1, x2, y2)

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def height(self) -> int:
        return max(1, self.bbox[3] - self.bbox[1])


@dataclass
class LayoutRegion:
    label: str
    bbox: BBox
    score: float = 1.0


@dataclass
class _PageWork:
    number: int
    source_name: str
    image_path: str
    image: np.ndarray
    width: int
    height: int


def _bbox_of_points(box: Sequence[Sequence[float]]) -> BBox:
    pts = np.asarray(box, dtype=np.float32).reshape(-1, 2)
    return (int(np.floor(pts[:, 0].min())), int(np.floor(pts[:, 1].min())),
            int(np.ceil(pts[:, 0].max())), int(np.ceil(pts[:, 1].max())))


def _intersection(a: BBox, b: BBox) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    return max(0, x2 - x1) * max(0, y2 - y1)


def _inside(point: Tuple[float, float], box: BBox, pad: int = 0) -> bool:
    return (box[0] - pad <= point[0] <= box[2] + pad and
            box[1] - pad <= point[1] <= box[3] + pad)


def _normalise_label(label: str) -> str:
    name = (label or "").strip().lower().replace("_", " ")
    if "table" in name:
        return "table_caption" if "caption" in name else "table"
    if "title" in name or "heading" in name:
        return "title"
    if "figure" in name or "image" in name or "chart" in name:
        return "figure_caption" if "caption" in name else "figure"
    if "header" in name:
        return "header"
    if "footer" in name:
        return "footer"
    if "reference" in name:
        return "reference"
    if "equation" in name or "formula" in name:
        return "equation"
    if "caption" in name:
        return "caption"
    return "text"


def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf"


def _join_text(a: str, b: str) -> str:
    if not a:
        return b
    if not b:
        return a
    if a.endswith("-"):
        return a + b
    if _is_cjk(a[-1]) or _is_cjk(b[0]):
        return a + b
    if a[-1].isalnum() and b[0].isalnum():
        return a + " " + b
    return a + b


class DocumentExtractor(object):
    """High-level extraction service, safe to use from a worker thread."""

    def __init__(self, models_dir: Optional[Path] = None,
                 options: Optional[ExtractOptions] = None) -> None:
        self.models_dir = Path(models_dir or MODELS_DIR)
        self.options = options or ExtractOptions()
        self.work_dir = Path(WORK_DIR)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._ocr = None
        self._layout = None
        self._layout_legacy = False
        self._table = None
        self._cv2 = None
        self._np = np
        self.warnings: List[str] = []
        self.engine_name = "PP-OCRv5 mobile · PP-Structure"

    # ------------------------------------------------------------------ models
    def _model(self, name: str) -> Path:
        path = self.models_dir / name
        if not path.exists() or path.stat().st_size < 1024:
            raise ModelMissingError(
                "缺少模型文件：%s\n请将模型放入 %s，或运行 tools/download_models.py。"
                % (name, self.models_dir)
            )
        return path

    def _cpu_threads(self) -> int:
        if self.options.ocr_threads > 0:
            return self.options.ocr_threads
        try:
            count = os.cpu_count() or 4
        except Exception:  # noqa: BLE001
            count = 4
        return max(1, min(8, int(count) - 1))

    def _load_engines(self) -> None:
        if self._ocr is not None:
            return
        det = self._model("ch_PP-OCRv5_det_mobile.onnx")
        rec = self._model("ch_PP-OCRv5_rec_mobile.onnx")
        keys = self.models_dir / "ppocrv5_dict.txt"
        try:
            import cv2  # noqa: F401
            from rapidocr import RapidOCR
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "OCR 运行库未安装：%s\n请先运行 安装依赖.bat。" % exc
            )
        params = {
            "Global.use_cls": False,
            "Global.log_level": "error",
            "Global.model_root_dir": str(self.models_dir),
            "Global.text_score": 0.42,
            "Det.model_path": str(det),
            "Det.limit_side_len": 960 if self.options.quality != "fast" else 736,
            "Det.limit_type": "min",
            "Det.box_thresh": 0.45,
            "Det.unclip_ratio": 1.55,
            "Rec.model_path": str(rec),
            "Rec.rec_keys_path": str(keys) if keys.exists() else None,
            "Rec.rec_batch_num": 6,
            "EngineConfig.onnxruntime.intra_op_num_threads": self._cpu_threads(),
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        }
        self._ocr = RapidOCR(params=params)

        if self.options.detect_tables:
            try:
                from rapid_layout import RapidLayout
                layout_path = self.models_dir / "layout_cdla.onnx"
                if layout_path.exists():
                    try:
                        # RapidLayout >= 1.x API
                        self._layout = RapidLayout(
                            model_dir_or_path=str(layout_path),
                            conf_thresh=0.42,
                            iou_thresh=0.5,
                            engine_cfg={"intra_op_num_threads": self._cpu_threads()},
                        )
                        self._layout_legacy = False
                    except TypeError:
                        try:
                            # RapidLayout 0.2.x (Python 3.8 / Windows 7 build)
                            self._layout = RapidLayout(
                                model_type="pp_layout_cdla",
                                model_path=str(layout_path),
                                conf_thres=0.42,
                                iou_thres=0.5,
                            )
                        except TypeError:
                            # RapidLayout 0.1.x ships its own layout_cdla.onnx
                            # and exposes only box_threshold.
                            self._layout = RapidLayout(
                                model_type="pp_layout_cdla",
                                box_threshold=0.42,
                            )
                        self._layout_legacy = True
            except Exception as exc:  # noqa: BLE001
                self.warnings.append("版面模型加载失败，已使用文字行版面：%s" % exc)
                self._layout = None
            try:
                # ONNX Runtime 1.14 (Windows 7 build) does not accept
                # pathlib.Path for InferenceSession; RapidTable passes Path.
                import rapid_table.inference_engine.onnxruntime.main as _rt_ort
                if not getattr(_rt_ort, "_doc_extract_path_patch", False):
                    _orig_session = _rt_ort.InferenceSession

                    def _session_compat(model_path, *args, **kwargs):
                        if isinstance(model_path, Path):
                            model_path = str(model_path)
                        return _orig_session(model_path, *args, **kwargs)

                    _rt_ort.InferenceSession = _session_compat
                    _rt_ort._doc_extract_path_patch = True
                from rapid_table import ModelType, RapidTable, RapidTableInput
                table_path = self.models_dir / "ch_ppstructure_mobile_v2_SLANet.onnx"
                if table_path.exists():
                    self._table = RapidTable(RapidTableInput(
                        model_type=ModelType.PPSTRUCTURE_ZH,
                        model_dir_or_path=str(table_path),
                        use_ocr=False,
                        engine_cfg={"intra_op_num_threads": self._cpu_threads()},
                    ))
            except Exception as exc:  # noqa: BLE001
                self.warnings.append("表格结构模型加载失败：%s" % exc)
                self._table = None

    # ------------------------------------------------------------------- input
    def _read_image(self, path: Path) -> np.ndarray:
        from PIL import Image, ImageOps
        img = Image.open(str(path))
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, "white")
            rgba = img.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
        # Limit huge phone/camera images to a CPU-friendly size.
        max_side = 2600
        if max(img.size) > max_side:
            scale = max_side / float(max(img.size))
            img = img.resize((max(1, int(img.width * scale)),
                              max(1, int(img.height * scale))), Image.LANCZOS)
        return np.asarray(img)[:, :, ::-1].copy()

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        if not self.options.deskew:
            return image
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(gray, 60, 160)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                minLineLength=max(100, image.shape[1] // 5),
                                maxLineGap=12)
        if lines is None:
            return image
        angles = []
        for item in lines[:300]:
            x1, y1, x2, y2 = item[0]
            if x2 == x1:
                continue
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if -8.0 < angle < 8.0:
                angles.append(angle)
        if not angles:
            return image
        angles.sort()
        angle = angles[len(angles) // 2]
        if abs(angle) < 0.35:
            return image
        h, w = image.shape[:2]
        matrix = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
        cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
        nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
        matrix[0, 2] += nw / 2.0 - w / 2.0
        matrix[1, 2] += nh / 2.0 - h / 2.0
        return cv2.warpAffine(image, matrix, (nw, nh),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255, 255, 255))

    def _load_pages(self, path: Path, progress: ProgressFn,
                    cancel: threading.Event) -> Tuple[List[_PageWork], str]:
        suffix = path.suffix.lower()
        pages: List[_PageWork] = []
        title = path.stem or "未命名文档"
        if suffix == ".pdf":
            try:
                import fitz
            except ImportError as exc:
                raise RuntimeError("PDF 支持库未安装：%s" % exc)
            try:
                pdf = fitz.open(str(path))
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("无法打开 PDF：%s" % exc)
            try:
                total = min(pdf.page_count, max(1, self.options.max_pages))
                if pdf.page_count > total:
                    self.warnings.append(
                        "PDF 共 %d 页，本次仅处理前 %d 页。" % (pdf.page_count, total))
                zoom = self.options.dpi / 72.0
                matrix = fitz.Matrix(zoom, zoom)
                for i in range(total):
                    if cancel.is_set():
                        raise ExtractionCancelled()
                    progress("解析 PDF", int(5 + 20 * i / max(total, 1)),
                             "正在渲染第 %d / %d 页…" % (i + 1, total))
                    page = pdf.load_page(i)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    img_path = self.work_dir / ("pdf_%d_%d.png" % (os.getpid(), i + 1))
                    pix.save(str(img_path))
                    image = self._read_image(img_path)
                    pages.append(_PageWork(
                        number=i + 1,
                        source_name="%s · 第%d页" % (title, i + 1),
                        image_path=str(img_path),
                        image=image, width=image.shape[1], height=image.shape[0]))
                if pdf.metadata and pdf.metadata.get("title"):
                    title = str(pdf.metadata.get("title")).strip() or title
            finally:
                pdf.close()
            return pages, title

        # Raster images: PNG/JPG/BMP/TIFF (multi-page TIFF supported).
        try:
            from PIL import Image, ImageOps, ImageSequence
            source = Image.open(str(path))
            frames = []
            for frame in ImageSequence.Iterator(source):
                frame = ImageOps.exif_transpose(frame).convert("RGB")
                frames.append(frame.copy())
                if len(frames) >= max(1, self.options.max_pages):
                    break
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("无法读取图片：%s" % exc)
        total = len(frames)
        for i, frame in enumerate(frames):
            if cancel.is_set():
                raise ExtractionCancelled()
            progress("读取图片", int(5 + 20 * (i + 1) / max(total, 1)),
                     "正在准备第 %d / %d 页…" % (i + 1, total))
            max_side = 2600
            if max(frame.size) > max_side:
                scale = max_side / float(max(frame.size))
                frame = frame.resize((max(1, int(frame.width * scale)),
                                      max(1, int(frame.height * scale))),
                                     Image.LANCZOS)
            image = np.asarray(frame)[:, :, ::-1].copy()
            img_path = self.work_dir / ("img_%d_%d.png" % (os.getpid(), i + 1))
            frame.save(str(img_path))
            pages.append(_PageWork(
                number=i + 1,
                source_name=path.name if total == 1 else "%s · 第%d页" % (title, i + 1),
                image_path=str(img_path), image=image,
                width=image.shape[1], height=image.shape[0]))
        return pages, title

    # --------------------------------------------------------------------- OCR
    def _ocr_image(self, image: np.ndarray) -> List[OCRLine]:
        result = self._ocr(image)
        boxes = getattr(result, "boxes", None)
        texts = getattr(result, "txts", None)
        scores = getattr(result, "scores", None)
        if boxes is None or texts is None:
            return []
        lines = []
        for box, text, score in zip(boxes, texts, scores):
            text = (text or "").strip()
            if not text:
                continue
            lines.append(OCRLine(text=text, score=float(score or 0.0),
                                 box=np.asarray(box, dtype=np.float32)))
        return lines

    def _layout_regions(self, image: np.ndarray) -> List[LayoutRegion]:
        if self._layout is None:
            return []
        try:
            result = self._layout(image)
        except Exception as exc:  # noqa: BLE001
            self.warnings.append("版面分析失败：%s" % exc)
            return []
        if self._layout_legacy:
            boxes, scores, names, _elapsed = result
        else:
            boxes = result.boxes
            scores = result.scores
            names = result.class_names
        regions = []
        boxes = [] if boxes is None else boxes
        names = [] if names is None else names
        scores = [] if scores is None else scores
        for box, label, score in zip(boxes, names, scores):
            bbox = _bbox_of_points(np.asarray(box).reshape(2, 2))
            bbox = (max(0, bbox[0]), max(0, bbox[1]),
                    min(image.shape[1], bbox[2]), min(image.shape[0], bbox[3]))
            if bbox[2] - bbox[0] < 8 or bbox[3] - bbox[1] < 8:
                continue
            regions.append(LayoutRegion(_normalise_label(str(label)), bbox,
                                        float(score or 1.0)))
        regions.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
        return regions

    def _find_tables(self, image: np.ndarray,
                     regions: List[LayoutRegion]) -> List[LayoutRegion]:
        tables = [r for r in regions if r.label == "table"]
        if tables or not self.options.detect_tables:
            return tables
        # If the layout model produced regions, trust its decision that this
        # page has no table; the morphology fallback is only for pages where
        # the layout model is unavailable/failed.
        if regions:
            return []
        # Conservative fallback for scans without a usable layout model.
        try:
            import cv2
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bw = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY, 25, -2)
            h, w = gray.shape[:2]
            hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, w // 40), 1))
            vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, h // 40)))
            horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk, iterations=1)
            vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk, iterations=1)
            grid = cv2.add(horiz, vert)
            grid = cv2.dilate(grid, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
            contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
            out = []
            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                area_ratio = (cw * ch) / float(w * h)
                if cw > w * 0.25 and ch > h * 0.05 and 0.004 < area_ratio < 0.85:
                    # Reject page borders.
                    if cw > w * 0.96 and ch > h * 0.96:
                        continue
                    out.append(LayoutRegion("table", (x, y, x + cw, y + ch)))
            out.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
            return out[:6]
        except Exception:  # noqa: BLE001
            return []

    def _table_from_region(self, image: np.ndarray, region: LayoutRegion,
                           lines: List[OCRLine]) -> Optional[TableData]:
        if self._table is None:
            return None
        import cv2
        h, w = image.shape[:2]
        x1, y1, x2, y2 = region.bbox
        pad = 6
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
        if x2 - x1 < 20 or y2 - y1 < 20:
            return None
        crop = image[y1:y2, x1:x2]
        # Keep only OCR boxes touching this table, in crop coordinates.
        crop_lines = []
        for line in lines:
            inter = _intersection(line.bbox, (x1, y1, x2, y2))
            area = max(1, (line.bbox[2] - line.bbox[0]) * (line.bbox[3] - line.bbox[1]))
            if inter / float(area) >= 0.35:
                crop_lines.append(line)
        if not crop_lines:
            self.warnings.append("表格区域未匹配到文字行。")
            return None
        try:
            results = self._table(crop)
        except Exception as exc:  # noqa: BLE001
            self.warnings.append("表格结构识别失败：%s" % exc)
            return self._fallback_table(crop_lines)
        logic = getattr(results, "logic_points", None)
        cell_boxes = getattr(results, "cell_bboxes", None)
        if not logic or not cell_boxes:
            self.warnings.append("表格结构模型未返回单元格。")
            return self._fallback_table(crop_lines)
        points = logic[0]
        boxes = cell_boxes[0]
        if points is None or len(points) == 0 or boxes is None or len(boxes) == 0:
            self.warnings.append("表格结构模型未返回有效单元格坐标。")
            return self._fallback_table(crop_lines)

        rows = int(max(p[1] for p in points)) + 1
        cols = int(max(p[3] for p in points)) + 1
        if rows < 1 or cols < 1 or rows > 200 or cols > 30:
            return None
        grid = [["" for _ in range(cols)] for _ in range(rows)]
        spans = [[(1, 1) for _ in range(cols)] for _ in range(rows)]
        occupied = [[False for _ in range(cols)] for _ in range(rows)]
        cells = []
        for p, cell_box in zip(points, boxes):
            r0, r1, c0, c1 = [int(v) for v in p]
            rs, cs = r1 - r0 + 1, c1 - c0 + 1
            if not (0 <= r0 < rows and 0 <= c0 < cols):
                continue
            for rr in range(r0, min(rows, r1 + 1)):
                for cc in range(c0, min(cols, c1 + 1)):
                    occupied[rr][cc] = True
                    if rr != r0 or cc != c0:
                        spans[rr][cc] = (0, 0)
            spans[r0][c0] = (rs, cs)
            poly = np.asarray(cell_box, dtype=np.float32).reshape(-1, 2)
            cb = _bbox_of_points(poly)
            cells.append((r0, c0, cb))
        # Map OCR lines to the table cell with the largest overlap.  OCR boxes
        # are in full-page coordinates; cell boxes are relative to the crop.
        cell_texts: Dict[Tuple[int, int], List[Tuple[float, float, str]]] = {}
        for line in crop_lines:
            rel_box = (line.bbox[0] - x1, line.bbox[1] - y1,
                       line.bbox[2] - x1, line.bbox[3] - y1)
            best = None
            best_overlap = 0.0
            for r0, c0, cb in cells:
                ov = _intersection(rel_box, cb)
                if ov > best_overlap:
                    best_overlap = ov
                    best = (r0, c0)
            area = max(1, (rel_box[2] - rel_box[0]) * (rel_box[3] - rel_box[1]))
            if best is None or best_overlap / float(area) < 0.18:
                continue
            cell_texts.setdefault(best, []).append(
                (line.bbox[1], line.bbox[0], line.text))
        for (r, c), items in cell_texts.items():
            items.sort(key=lambda it: (it[0], it[1]))
            # Lines on the same visual row are joined with a space.
            merged: List[str] = []
            last_y = None
            for top, _left, text in items:
                if last_y is not None and abs(top - last_y) < 10:
                    merged[-1] = _join_text(merged[-1], text)
                else:
                    merged.append(text)
                last_y = top
            grid[r][c] = "\n".join(merged)
        table = TableData(grid=grid, spans=spans, bbox=region.bbox,
                          confidence=region.score,
                          html=table_to_html(TableData(grid=grid, spans=spans)))
        if table.is_empty():
            self.warnings.append("表格结构已还原，但未匹配到单元格文字。")
            return self._fallback_table(crop_lines)
        return table

    def _fallback_table(self, lines: List[OCRLine]) -> Optional[TableData]:
        """Build a rough editable table from OCR lines when SLANet fails.

        This is deliberately simple (visual rows, gap-separated columns) but
        prevents a recognized table from silently disappearing.
        """
        if not lines:
            return None
        ordered = sorted(lines, key=lambda l: (l.bbox[1], l.bbox[0]))
        median_h = sorted(l.height for l in ordered)[len(ordered) // 2]
        rows: List[List[OCRLine]] = []
        for line in ordered:
            if rows and abs(line.center[1] - rows[-1][0].center[1]) <= max(8, median_h * 0.65):
                rows[-1].append(line)
            else:
                rows.append([line])
        out_rows: List[List[str]] = []
        for row in rows:
            row.sort(key=lambda l: l.bbox[0])
            cells: List[str] = []
            prev_right = None
            for line in row:
                if prev_right is not None and line.bbox[0] - prev_right > max(18, median_h * 1.1):
                    cells.append(line.text)
                elif cells:
                    cells[-1] = _join_text(cells[-1], line.text)
                else:
                    cells.append(line.text)
                prev_right = line.bbox[2]
            out_rows.append(cells)
        width = max(len(r) for r in out_rows)
        out_rows = [r + [""] * (width - len(r)) for r in out_rows]
        spans = [[(1, 1) for _ in range(width)] for _ in out_rows]
        return TableData(grid=out_rows, spans=spans,
                         bbox=rows[0][0].bbox if rows else None,
                         html=table_to_html(TableData(grid=out_rows, spans=spans)))

    # ----------------------------------------------------------- page building
    def _merge_region_text(self, lines: List[OCRLine]) -> str:
        if not lines:
            return ""
        lines = sorted(lines, key=lambda l: (l.bbox[1], l.bbox[0]))
        merged: List[str] = []
        last = None
        for line in lines:
            if last is not None:
                same_row = abs(line.center[1] - last.center[1]) < max(8, line.height * 0.55)
                gap = line.bbox[1] - last.bbox[3]
                if same_row:
                    merged[-1] = _join_text(merged[-1], line.text)
                elif gap < -max(10, line.height * 0.8):
                    # Overlapping boxes (common with layout regions) - keep it.
                    merged[-1] = _join_text(merged[-1], line.text)
                else:
                    merged.append(line.text)
            else:
                merged.append(line.text)
            last = line
        return "\n".join(merged).strip()

    def _free_paragraphs(self, lines: List[OCRLine]) -> List[Block]:
        if not lines:
            return []
        lines = sorted(lines, key=lambda l: (l.bbox[1], l.bbox[0]))
        median_h = sorted(l.height for l in lines)[len(lines) // 2]
        groups: List[List[OCRLine]] = []
        current: List[OCRLine] = []
        for line in lines:
            if not current:
                current = [line]
                continue
            prev = current[-1]
            gap = line.bbox[1] - prev.bbox[3]
            x_overlap = _intersection((line.bbox[0], 0, line.bbox[2], 1),
                                      (prev.bbox[0], 0, prev.bbox[2], 1))
            width = max(1, min(line.bbox[2] - line.bbox[0],
                               prev.bbox[2] - prev.bbox[0]))
            overlap_ratio = x_overlap / float(width)
            same_row = abs(line.center[1] - prev.center[1]) < median_h * 0.55
            if same_row:
                current.append(line)
                continue
            height_ok = max(line.height, prev.height) < median_h * 1.45
            if height_ok and gap <= max(10, median_h * 0.85) and overlap_ratio > 0.15:
                current.append(line)
            else:
                groups.append(current)
                current = [line]
        if current:
            groups.append(current)

        blocks: List[Block] = []
        for group in groups:
            text = self._merge_region_text(group)
            if not text:
                continue
            top = min(l.bbox[1] for l in group)
            left = min(l.bbox[0] for l in group)
            bottom = max(l.bbox[3] for l in group)
            right = max(l.bbox[2] for l in group)
            max_h = max(l.height for l in group)
            kind = "text"
            if max_h > median_h * 1.32 and len(text) <= 60:
                kind = "title" if max_h > median_h * 1.6 else "heading"
            elif len(text) <= 28 and re_heading(text):
                kind = "heading"
            blocks.append(Block(kind=kind, text=text,
                                bbox=(left, top, right, bottom),
                                confidence=float(np.mean([l.score for l in group]))))
        return blocks

    def _build_page(self, page: _PageWork, lines: List[OCRLine],
                    regions: List[LayoutRegion], progress: ProgressFn,
                    cancel: threading.Event) -> PageResult:
        result = PageResult(number=page.number, source=page.source_name,
                            image_path=page.image_path, width=page.width,
                            height=page.height, engine=self.engine_name)
        tables = self._find_tables(page.image, regions)
        table_used = [False] * len(lines)
        table_blocks: List[Block] = []
        for t_idx, table_region in enumerate(tables):
            if cancel.is_set():
                raise ExtractionCancelled()
            progress("识别表格", 55 + int(25 * t_idx / max(1, len(tables))),
                     "正在还原第 %d 页表格结构…" % page.number)
            table = self._table_from_region(page.image, table_region, lines)
            if table is None:
                continue
            table_blocks.append(Block(kind="table", text=table.to_text(),
                                      bbox=table_region.bbox, table=table,
                                      confidence=table_region.score))
            for i, line in enumerate(lines):
                inter = _intersection(line.bbox, table_region.bbox)
                area = max(1, (line.bbox[2] - line.bbox[0]) *
                           (line.bbox[3] - line.bbox[1]))
                if inter / float(area) > 0.5:
                    table_used[i] = True

        # Table captions should stay next to their table.
        caption_blocks: List[Block] = []
        for region in regions:
            if region.label == "table_caption":
                selected = [l for i, l in enumerate(lines)
                            if not table_used[i] and _inside(l.center, region.bbox)]
                text = self._merge_region_text(selected)
                if text:
                    for i, line in enumerate(lines):
                        if not table_used[i] and _inside(line.center, region.bbox):
                            table_used[i] = True
                    caption_blocks.append(Block(kind="caption", text=text,
                                                bbox=region.bbox))

        # Assign the remaining OCR lines to layout text regions.
        assigned_regions: List[Tuple[LayoutRegion, List[OCRLine]]] = []
        used = [False] * len(lines)
        for region in regions:
            if region.label in ("table", "figure", "table_caption", "figure_caption"):
                continue
            chosen = []
            for i, line in enumerate(lines):
                if table_used[i] or used[i]:
                    continue
                if _inside(line.center, region.bbox, pad=4):
                    # Avoid stealing lines from a nested/overlapping region.
                    chosen.append(i)
            if chosen:
                for i in chosen:
                    used[i] = True
                assigned_regions.append(
                    (region, [lines[i] for i in chosen]))

        blocks: List[Block] = []
        for region, group in assigned_regions:
            if region.label in ("header", "footer") and not self.options.keep_header_footer:
                continue
            if region.label == "figure":
                continue
            text = self._merge_region_text(group)
            if not text:
                continue
            if region.label == "title":
                kind = "title"
            elif region.label == "caption":
                kind = "caption"
            elif region.label in ("header", "footer"):
                kind = "text"
            else:
                max_h = max(l.height for l in group)
                median_h = sorted(l.height for l in lines)[len(lines) // 2] if lines else max_h
                kind = "heading" if max_h > median_h * 1.28 and len(text) <= 60 else "text"
            conf = float(np.mean([l.score for l in group]))
            blocks.append(Block(kind=kind, text=text, bbox=region.bbox,
                                confidence=conf))

        leftovers = [lines[i] for i in range(len(lines))
                     if not used[i] and not table_used[i] and
                     not getattr(lines[i], "_skip", False)]
        blocks.extend(self._free_paragraphs(leftovers))
        blocks.extend(table_blocks)
        blocks.extend(caption_blocks)
        # De-duplicate identical text at the same position (layout + leftovers).
        unique = []
        seen = set()
        for b in blocks:
            key = (b.kind, (b.text or "")[:80], b.bbox)
            if key in seen:
                continue
            seen.add(key)
            unique.append(b)
        unique.sort(key=lambda b: (b.bbox[1] if b.bbox else 0,
                                   b.bbox[0] if b.bbox else 0))
        result.blocks = unique
        if not result.blocks:
            result.warnings.append("第 %d 页未识别到文字。" % page.number)
        return result

    # ------------------------------------------------------------------- public
    def extract(self, input_path: str, progress: Optional[ProgressFn] = None,
                cancel: Optional[threading.Event] = None) -> DocumentResult:
        progress = progress or (lambda stage, pct, msg: None)
        cancel = cancel or threading.Event()
        started = time.time()
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(str(path))
        progress("加载模型", 1, "正在加载 PP-OCRv5 mobile 与 PP-Structure…")
        self._load_engines()
        progress("读取文件", 4, "正在读取文件…")
        pages, title = self._load_pages(path, progress, cancel)
        result = DocumentResult(title=title, source_path=str(path),
                                engine=self.engine_name)
        total = len(pages)
        for idx, page in enumerate(pages):
            if cancel.is_set():
                raise ExtractionCancelled()
            page_start = time.time()
            progress("识别文字", int(25 + 65 * idx / max(1, total)),
                     "正在识别第 %d / %d 页文字…" % (idx + 1, total))
            image = self._deskew(page.image)
            if image.shape[1] != page.width or image.shape[0] != page.height:
                page.image = image
                page.width, page.height = image.shape[1], image.shape[0]
                try:
                    from PIL import Image
                    Image.fromarray(image[:, :, ::-1]).save(page.image_path)
                except Exception:  # noqa: BLE001
                    pass
            lines = self._ocr_image(image)
            progress("分析版面", int(25 + 65 * idx / max(1, total) + 2),
                     "正在分析第 %d 页版面…" % (idx + 1))
            regions = self._layout_regions(image)
            page_result = self._build_page(page, lines, regions, progress, cancel)
            page_result.elapsed = time.time() - page_start
            result.pages.append(page_result)
            progress("识别文字", int(25 + 65 * (idx + 1) / max(1, total)),
                     "第 %d / %d 页完成，共 %d 行文字。" %
                     (idx + 1, total, len(lines)))
        result.elapsed = time.time() - started
        # A large title on the first page is a better document title than a
        # camera timestamp or a generic file stem.
        if result.pages:
            for block in result.pages[0].blocks:
                if block.kind == "title" and block.text.strip() and len(block.text) <= 50:
                    result.title = block.text.strip()
                    # The title is rendered separately by the preview and the
                    # exporters; keep it out of the body to avoid duplication.
                    if block is result.pages[0].blocks[0]:
                        result.pages[0].blocks = result.pages[0].blocks[1:]
                    break
        if self.warnings:
            for page in result.pages:
                page.warnings.extend(self.warnings)
            self.warnings.clear()
        progress("完成", 100, "识别完成，用时 %.1f 秒。" % result.elapsed)
        return result


def re_heading(text: str) -> bool:
    """Cheap heading detector used only when no layout heading is available."""
    import re
    t = text.strip()
    if not t or len(t) > 40:
        return False
    patterns = [
        r"^[一二三四五六七八九十百]+[、.．]",
        r"^（[一二三四五六七八九十]+）",
        r"^\d+(\.\d+){0,2}[、.．\s]",
        r"^第[一二三四五六七八九十百\d]+[章节篇部分]",
        r"^[（(]\d+[）)]",
    ]
    return any(re.match(p, t) for p in patterns)
