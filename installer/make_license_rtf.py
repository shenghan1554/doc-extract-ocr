# -*- coding: utf-8 -*-
"""Build a Unicode-safe RTF license page for the Inno Setup installer."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rtf_escape(text: str) -> str:
    out = []
    for ch in text.replace("\r\n", "\n").replace("\r", "\n"):
        if ch == "\n":
            out.append("\\par\n")
        elif ch in "\\{}":
            out.append("\\" + ch)
        elif ord(ch) < 128:
            out.append(ch)
        else:
            value = ord(ch)
            if value > 0xFFFF:
                # Encode a non-BMP character as a UTF-16 surrogate pair.
                value -= 0x10000
                high = 0xD800 + (value >> 10)
                low = 0xDC00 + (value & 0x3FF)
                for unit in (high, low):
                    signed = unit - 0x10000 if unit > 0x7FFF else unit
                    out.append("\\u%d?" % signed)
            else:
                signed = value - 0x10000 if value > 0x7FFF else value
                out.append("\\u%d?" % signed)
    return "".join(out)


def main() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    body = (
        "文档提取 v1.0.1\r\n"
        "作者/发行者：盛晗\r\n\r\n"
        "技术协议与许可条款\r\n\r\n"
        "安装或使用本软件前，请阅读以下条款。\r\n\r\n"
        + license_text
        + "\r\n\r\n第三方组件与模型许可见安装目录中的"
          "“第三方许可说明.txt”和“README.md”。\r\n"
    )
    rtf = (
        r"{\rtf1\ansi\ansicpg936\deff0"
        r"{\fonttbl{\f0\fnil\fcharset134 SimSun;}}"
        r"\viewkind4\uc1\pard\f0\fs20 "
        + rtf_escape(body)
        + r"\par}"
    )
    (ROOT / "installer" / "license.rtf").write_text(rtf, encoding="ascii",
                                                     errors="ignore")
    print("wrote", ROOT / "installer" / "license.rtf")


if __name__ == "__main__":
    main()
