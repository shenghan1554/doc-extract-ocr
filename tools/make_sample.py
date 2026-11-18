# -*- coding: utf-8 -*-
"""Synthetic end-to-end sample generator (development / acceptance test)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size, index=0)


def make_page() -> Image.Image:
    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 16], fill="#0f766e")
    d.text((90, 70), "设备验收报告", font=font(46, True), fill="#111827")
    d.text((90, 138), "Document Extraction · Acceptance Report", font=font(18), fill="#64748b")
    d.line([90, 185, W - 90, 185], fill="#cbd5e1", width=2)

    lines = [
        "一、项目概况",
        "本报告用于验证文档提取软件的文字、表格与 PDF 识别能力。",
        "系统采用 PP-OCRv5 mobile 检测与识别模型，模型在 CPU 上运行，",
        "并使用 PP-Structure 完成版面分析与表格结构还原。",
        "",
        "二、主要指标",
    ]
    y = 220
    for line in lines:
        if line.startswith("一、") or line.startswith("二、"):
            d.text((90, y), line, font=font(27, True), fill="#0f766e")
            y += 52
        else:
            d.text((90, y), line, font=font(21), fill="#1e293b")
            y += 42

    # Table
    y += 18
    x0, x1 = 90, W - 90
    col_w = [220, 300, 220, 300]
    xs = [x0]
    for w in col_w:
        xs.append(xs[-1] + w)
    row_h = 64
    rows = [
        ["检测项目", "测试内容", "结果", "备注"],
        ["文字识别", "中文、数字、英文混排", "通过", "置信度 ≥ 95%"],
        ["表格识别", "合并单元格与多行文本", "通过", "导出可编辑表格"],
        ["PDF 提取", "双页扫描件逐页识别", "通过", "输出 Word / PDF"],
    ]
    for r, row in enumerate(rows):
        top = y + r * row_h
        d.rectangle([x0, top, xs[-1], top + row_h], fill="#eaf2f8" if r == 0 else "#ffffff")
        for c in range(4):
            d.rectangle([xs[c], top, xs[c + 1], top + row_h], outline="#94a3b8", width=2)
            d.text((xs[c] + 14, top + 18), row[c], font=font(19, r == 0), fill="#0f172a")
    y += len(rows) * row_h + 40

    d.text((90, y), "三、结论", font=font(27, True), fill="#0f766e")
    y += 50
    d.text((90, y), "软件界面操作顺畅，拍照与上传两种方式均可完成识别，", font=font(21), fill="#1e293b")
    y += 38
    d.text((90, y), "识别结果可直接复制，并导出为 Word、PDF 与 Excel 表格。", font=font(21), fill="#1e293b")

    d.line([90, H - 120, W - 90, H - 120], fill="#e2e8f0", width=2)
    d.text((90, H - 92), "文档提取 · 内部验收样例", font=font(16), fill="#94a3b8")
    d.text((W - 250, H - 92), "第 1 页 / 共 1 页", font=font(16), fill="#94a3b8")
    return img


def main() -> None:
    OUT.mkdir(exist_ok=True)
    img = make_page()
    img.save(OUT / "样例文档.png", dpi=(150, 150))
    img.save(OUT / "样例文档.pdf", "PDF", resolution=150.0)
    # A slightly skewed phone-photo style sample for preprocessing tests.
    rotated = img.rotate(-1.2, resample=Image.BICUBIC, expand=False, fillcolor="white")
    rotated.save(OUT / "样例拍照.png")
    print("saved", OUT)


if __name__ == "__main__":
    main()
