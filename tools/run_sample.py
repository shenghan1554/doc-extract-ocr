# -*- coding: utf-8 -*-
"""Run the full OCR pipeline on the bundled sample and export all formats."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doc_extract.engine import DocumentExtractor, ExtractOptions  # noqa: E402
from doc_extract.export import export_docx, export_pdf, export_xlsx  # noqa: E402


def main() -> int:
    image = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sample" / "样例文档.png"
    out_dir = ROOT / "outputs" / "sample_result"
    out_dir.mkdir(parents=True, exist_ok=True)
    extractor = DocumentExtractor(options=ExtractOptions())
    result = extractor.extract(
        str(image),
        progress=lambda stage, pct, msg: print("[%3d%%] %s %s" % (pct, stage, msg)),
    )
    print("标题：%s" % result.title)
    print("页数：%d  表格：%d  字数：%d  用时：%.1f 秒" %
          (len(result.pages), result.total_tables, result.total_chars, result.elapsed))
    for path in (export_docx(result, str(out_dir / "sample.docx")),
                 export_pdf(result, str(out_dir / "sample.pdf")),
                 export_xlsx(result, str(out_dir / "sample.xlsx"))):
        print("已导出：%s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
