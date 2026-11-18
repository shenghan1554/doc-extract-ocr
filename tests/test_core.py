# -*- coding: utf-8 -*-
"""Fast unit tests for parsing, rendering and export. No OCR model needed."""
from __future__ import annotations

import json
import os
import unittest
import uuid
from pathlib import Path

from doc_extract.export import export_docx, export_pdf, export_xlsx
from doc_extract.models import Block, DocumentResult, PageResult, TableData
from doc_extract.render import document_html, document_plain_text, tables_plain_text
from doc_extract.table_utils import parse_table_html, table_to_html


HTML = """<html><body><table>
<tr><td rowspan="2">检测项目</td><td colspan="2">测试内容</td><td>结果</td></tr>
<tr><td>文字识别</td><td>表格识别</td><td>通过</td></tr>
<tr><td>PDF 提取</td><td colspan="3">双页扫描件逐页识别，输出 Word / PDF</td></tr>
</table></body></html>"""


def make_document() -> DocumentResult:
    table = parse_table_html(HTML)
    table.bbox = (80, 400, 1100, 700)
    page = PageResult(number=1, source="样例.png", width=1240, height=1754)
    page.add_text("设备验收报告", (80, 80, 400, 130), "title")
    page.add_text("本报告用于验证文档提取软件的文字、表格与 PDF 识别能力。", (80, 180, 1000, 210))
    page.add_table(table)
    page.add_text("三、结论", (80, 760, 300, 800), "heading")
    page.add_text("识别结果可直接复制，并导出为 Word、PDF 与 Excel 表格。", (80, 820, 1050, 850))
    return DocumentResult(title="设备验收报告", pages=[page], source_path="样例.png")


class TableTests(unittest.TestCase):
    def test_merged_cells(self) -> None:
        table = parse_table_html(HTML)
        self.assertEqual((table.n_rows, table.n_cols), (3, 4))
        self.assertEqual(table.grid[0][0], "检测项目")
        self.assertEqual(table.spans[0][0], (2, 1))
        self.assertEqual(table.spans[0][1], (1, 2))
        self.assertEqual(table.spans[1][0], (0, 0))
        self.assertEqual(table.spans[2][1], (1, 3))
        self.assertIn("双页扫描件", table.grid[2][1])

    def test_malformed_html_does_not_crash(self) -> None:
        table = parse_table_html("<table><tr><td>A<td>B</tr></table>")
        self.assertGreaterEqual(table.n_rows, 1)
        self.assertTrue(table.to_tsv())

    def test_html_render(self) -> None:
        html = table_to_html(parse_table_html(HTML))
        self.assertIn('rowspan="2"', html)
        self.assertIn('colspan="3"', html)

    def test_tsv(self) -> None:
        table = parse_table_html(HTML)
        self.assertEqual(table.to_tsv().splitlines()[0].split("\t")[0], "检测项目")


class RenderTests(unittest.TestCase):
    def test_html_preview(self) -> None:
        doc = make_document()
        html = document_html(doc)
        self.assertIn("设备验收报告", html)
        self.assertIn("<table", html)
        self.assertIn("检测项目", html)

    def test_plain_text(self) -> None:
        doc = make_document()
        text = document_plain_text(doc)
        self.assertIn("设备验收报告", text)
        self.assertIn("检测项目", text)
        self.assertIn("三、结论", text)

    def test_tables_copy(self) -> None:
        doc = make_document()
        text = tables_plain_text(doc)
        self.assertIn("表格 1", text)
        self.assertIn("双页扫描件", text)


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = make_document()
        self.tmpdir = Path(__file__).resolve().parents[1] / "outputs"
        self.tmpdir.mkdir(exist_ok=True)
        self.prefix = "test_%s_" % uuid.uuid4().hex[:8]

    def tearDown(self) -> None:
        for path in self.tmpdir.glob(self.prefix + "*"):
            try:
                path.unlink()
            except OSError:
                pass

    def test_docx(self) -> None:
        path = export_docx(self.doc, os.path.join(str(self.tmpdir), self.prefix + "out.docx"))
        self.assertTrue(os.path.getsize(path) > 10000)
        from docx import Document
        word = Document(path)
        text = "\n".join(p.text for p in word.paragraphs)
        self.assertIn("设备验收报告", text)
        self.assertGreaterEqual(len(word.tables), 1)

    def test_pdf(self) -> None:
        path = export_pdf(self.doc, os.path.join(str(self.tmpdir), self.prefix + "out.pdf"))
        self.assertTrue(os.path.getsize(path) > 10000)
        import fitz
        pdf = fitz.open(path)
        try:
            self.assertEqual(pdf.page_count, 1)
            self.assertIn("设备验收报告", pdf[0].get_text())
        finally:
            pdf.close()

    def test_xlsx(self) -> None:
        path = export_xlsx(self.doc, os.path.join(str(self.tmpdir), self.prefix + "out.xlsx"))
        self.assertTrue(os.path.getsize(path) > 4000)
        from openpyxl import load_workbook
        wb = load_workbook(path)
        try:
            self.assertIn("全文", wb.sheetnames)
            self.assertIn("表格1", wb.sheetnames)
            self.assertEqual(wb["表格1"]["A1"].value.startswith("表格 1"), True)
        finally:
            wb.close()


class ModelTests(unittest.TestCase):
    def test_models_present(self) -> None:
        from doc_extract.paths import MODELS_DIR
        required = [
            "ch_PP-OCRv5_det_mobile.onnx",
            "ch_PP-OCRv5_rec_mobile.onnx",
            "ppocrv5_dict.txt",
            "layout_cdla.onnx",
            "ch_ppstructure_mobile_v2_SLANet.onnx",
        ]
        missing = [n for n in required if not (MODELS_DIR / n).exists()]
        self.assertEqual(missing, [], "缺少模型：%s" % missing)


class DictTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        doc = make_document()
        data = json.loads(json.dumps(doc.to_dict(), ensure_ascii=False))
        clone = DocumentResult.from_dict(data)
        self.assertEqual(clone.title, doc.title)
        self.assertEqual(len(clone.pages), 1)
        self.assertEqual(clone.pages[0].blocks[2].table.spans[0][0], (2, 1))
        self.assertEqual(clone.plain_text, doc.plain_text)


if __name__ == "__main__":
    unittest.main()
