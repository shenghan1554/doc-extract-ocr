# 文档提取 · doc-extract-ocr

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.1-green.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Windows%207%2F10%2F11%20x64-lightgrey.svg)](#5-windows-7-兼容版)
[![Python](https://img.shields.io/badge/Python-3.8%E2%80%933.12-blue.svg)](#32-从源码运行)

> Windows 桌面端离线文档识别软件  
> **PP-OCRv5 mobile + PP-Structure · ONNX Runtime CPU · 拍照/上传 · Word/PDF/Excel**
>
> 作者：盛晗
>
> 更新记录：[CHANGELOG.md](CHANGELOG.md)

> **本仓库是完整源码，含全部 5 个 ONNX 模型**，clone 下来即可离线运行；不想装环境的直接用 [Releases](https://github.com/shenghan1554/doc-extract-ocr/releases) 里的安装版/便携版。

![主界面](docs/screenshot-result.png)

## 1. 软件简介

「文档提取」是一款完全离线运行的 Windows 桌面软件。它把手机拍摄、扫描件或 PDF 中的文字、版面和表格提取为可编辑内容，并可直接导出 Word、PDF、Excel，或从界面中选中复制。

- **识别引擎**：PP-OCRv5 mobile 文字检测/识别 + PP-Structure 版面分析 + SLANet 表格结构还原
- **推理方式**：ONNX Runtime，纯 CPU，无 GPU/CUDA 依赖，不需要联网
- **输入方式**：电脑摄像头拍照、上传图片（JPG/PNG/BMP/TIFF/WebP）、上传 PDF（逐页识别）
- **输出方式**：Word（含合并单元格）、PDF（文字可选中）、Excel（表格可编辑）、一键复制全文/表格
- **界面**：中文三栏式桌面界面，支持拖拽、页面预览、版面框、表格预览和快捷键

## 2. 功能清单

| 功能 | 说明 |
|---|---|
| 拍照识别 | 调用 USB/内置摄像头，实时预览，拍照后立即识别 |
| 上传识别 | 图片、扫描件、PDF；支持拖拽到窗口 |
| 文字识别 | 中文、英文、数字混排；保留段落和阅读顺序 |
| 表格识别 | PP-Structure 表格结构，支持合并单元格、多行单元格 |
| PDF 提取 | 逐页渲染后识别，支持多页 PDF |
| 直接复制 | 结果区可直接选中复制；「复制全文」一键复制，表格可按 TSV 复制粘贴到 Excel |
| 导出 Word | 标题、段落、表格、合并单元格；可直接编辑 |
| 导出 PDF | 嵌入中文字体，文字可选中、可搜索 |
| 导出表格 | Excel 工作簿，含「全文」和「表格N」工作表 |
| 页面预览 | 显示原图及标题/表格/正文版面框，可开关 |
| 离线运行 | 模型在本机 CPU 运行，文件不上传服务器 |

## 3. 快速开始

### 3.1 已打包版本（推荐给最终用户）

到 [Releases](https://github.com/shenghan1554/doc-extract-ocr/releases) 下载：

```text
文档提取-1.0.1-Win7-Setup.exe            # 安装版，Win7 SP1 / 10 / 11
文档提取-1.0.1-Win7-10-11-Portable.zip   # 便携版，解压即用
```

安装版会安装到 `C:\Program Files\DocExtract`，创建开始菜单/桌面快捷方式，并在缺少 VC++ 运行库时尝试安装。便携版解压后双击 `文档提取\文档提取.exe`，整个 `文档提取` 文件夹需要一起保留，不能只复制 EXE。

两版均使用 **Python 3.8 + PyInstaller 5.13.2** 构建，已把 OCR 模型降为 ONNX IR 8，以兼容 Windows 7 的 ONNX Runtime 1.14；同一构建也可在 Windows 10/11 x64 运行。

发布包细节与 SHA256 见每个 Release 的说明。仓库本身不含预编译二进制，只有源码与模型。

### 3.2 从源码运行

**环境要求：** Windows 10/11 x64、Python 3.10–3.12、约 1.5 GB 磁盘空间。

1. 双击 `安装依赖.bat`。脚本会创建 `.venv`、安装依赖并校验/下载模型。
2. 双击 `启动文档提取.bat`。
3. 首次识别需要加载模型，约多等 1–3 秒。

也可以手动执行：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe tools\download_models.py
.venv\Scripts\python.exe app.py
```

### 3.3 使用步骤

1. 点击右上角 **「上传识别」**，选择图片/PDF；或点击 **「拍照识别」**。
2. 在左侧选择清晰度、是否识别表格、是否自动纠偏。
3. 等待识别完成。右侧显示排版化识别结果。
4. 直接选中文字复制，或点 **「复制全文」**。
5. 点底部 **Word / PDF / 表格** 导出；「表格」页可预览并复制单个表格。

### 3.4 快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+O` | 上传文件 |
| `Ctrl+P` | 拍照识别 |
| `Ctrl+S` | 导出 Word |
| `Ctrl+Shift+S` | 导出 PDF |
| `Ctrl+C` | 复制选中的文字（结果区原生支持） |
| `Ctrl+滚轮` | 预览区缩放 |

## 4. 识别原理与模型

```
输入图片/PDF
   │
   ├─ PDF 逐页渲染（PyMuPDF）
   ├─ EXIF 纠正 / 自动纠偏 / 尺寸限制
   │
   ├─ PP-OCRv5 mobile det + rec（ONNX Runtime CPU）
   │       └─ 全页文字行、坐标、置信度
   │
   ├─ PP-Structure 版面模型（CDLA：标题/正文/表格/页眉页脚…）
   │       └─ 按版面区域聚合段落，恢复阅读顺序
   │
   └─ PP-Structure SLANet 表格结构（PPSTRUCTURE_ZH）
           └─ 单元格坐标 + rowspan/colspan + 文字匹配
   │
   └─ 结构化结果 → 预览 / 复制 / Word / PDF / Excel
```

模型文件位于 `models/`，合计约 37 MB：

| 文件 | 用途 | 大小 |
|---|---|---|
| `ch_PP-OCRv5_det_mobile.onnx` | PP-OCRv5 mobile 文本检测 | 4.8 MB |
| `ch_PP-OCRv5_rec_mobile.onnx` | PP-OCRv5 mobile 文本识别 | 16.6 MB |
| `ppocrv5_dict.txt` | PP-OCRv5 中文字符集 | 74 KB |
| `layout_cdla.onnx` | PP-Structure CDLA 版面分析 | 7.4 MB |
| `ch_ppstructure_mobile_v2_SLANet.onnx` | PP-Structure 表格结构 | 7.8 MB |

校验/重新下载：

```bat
.venv\Scripts\python.exe tools\download_models.py --check
.venv\Scripts\python.exe tools\download_models.py
```

模型来源：PaddleOCR 官方 PP-OCRv5 / PP-Structure 模型，经 RapidOCR、RapidLayout、RapidTable 提供的 ONNX 转换版本分发。模型 SHA256 记录在 `tools/download_models.py` 和 `models/README.md` 中。

## 5. Windows 7 兼容版

软件采用 **Python 3.8 + PyQt5 5.15 + ONNX Runtime 1.14 CPU** 的兼容技术栈，不依赖 PaddlePaddle，因此可以在 Windows 7 SP1 x64 上部署。

**只需要安装使用：** 直接运行 `release\文档提取-1.0.1-Win7-Setup.exe`。安装程序会检测/安装 VC++ 2015–2022 运行库，创建开始菜单和桌面快捷方式。以下内容是源码部署与自行构建步骤。

由于 Windows 7 已停止支持，需要满足以下前提：

### 5.1 系统前提

- Windows 7 **SP1 64 位**（不支持 32 位）
- CPU 支持 **AVX** 指令集（2011 年后的 Intel/AMD 桌面 CPU 基本都支持；可用 CPU-Z 查看）
- 已安装 SHA-2 支持补丁：`KB4474419`、`KB4490628`
- 已安装 Universal C Runtime：`KB2999226`
- 已安装 **Microsoft Visual C++ 2015–2022 Redistributable (x64)**
- 内存建议 4 GB 以上；磁盘预留 1.5 GB

### 5.2 安装步骤

1. 安装 **Python 3.8.10 x64**（Windows 7 支持的最高 Python 版本），安装时勾选 `Add Python 3.8 to PATH`。
2. 把整个软件文件夹复制到 **纯英文路径**，例如 `D:\DocExtract`；不要在 `Program Files` 或中文路径下运行。
3. 双击 `安装依赖-Win7.bat`。脚本使用 `requirements-win7.txt` 创建 `.venv38` 并下载模型。
4. 双击 `启动文档提取-Win7.bat`。

如果启动时报缺少 `api-ms-win-core-libraryloader-l1-2-0.dll` 等 DLL，这是部分 Win7 + ONNX Runtime 环境缺少 API 集导致的。可安装上述系统补丁，或从可信来源补充这 3 个 DLL 到 `C:\Windows\System32`（仅在确认系统版本和来源可信时操作）：

```text
api-ms-win-core-libraryloader-l1-2-0.dll
api-ms-win-core-processtopology-obsolete-l1-1-0.dll
API-MS-Win-Eventing-Provider-L1-1-0.dll
```

### 5.3 构建 Win7 EXE

在 Windows 7 虚拟机/实体机的 Python 3.8 环境中：

```bat
安装依赖-Win7.bat
.venv38\Scripts\python.exe -m pip install pyinstaller==5.13.2
.venv38\Scripts\python.exe -m PyInstaller 文档提取.spec --noconfirm --clean
```

`打包EXE-Win7.bat` 已封装上述步骤。**必须用 Python 3.8 构建 Win7 版**；用 Python 3.10+ 构建的 EXE 无法在 Win7 上启动。

> 说明：本项目在 Windows 11 + Python 3.12 上完成了 PP-OCRv5/PP-Structure 全流程、三种导出和界面实测；Win7 兼容栈（Python 3.8 + ORT 1.14 + PyQt5 5.15）已按上述依赖实现，但当前开发机没有 Windows 7 真机/虚拟机，因此 Win7 未做真机验收。首次部署建议先在目标机运行一张样例图确认 CPU/AVX/VC++ 环境。

## 6. 项目结构

```text
doc-extract-ocr/
├─ app.py                        # 入口（高 DPI、Qt 插件路径、日志、异常捕获）
├─ doc_extract/
│  ├─ engine.py                  # 识别流水线（OCR/版面/表格/PDF/纠偏）
│  ├─ models.py                  # 文档、页面、块、表格数据结构
│  ├─ table_utils.py             # 容错 HTML 表格解析、合并单元格、TSV
│  ├─ render.py                  # 结果 HTML / 纯文本 / 复制文本
│  ├─ paths.py                   # 模型、输出、设置、临时目录
│  ├─ export/
│  │  ├─ docx_exporter.py        # Word
│  │  ├─ pdf_exporter.py         # PDF（中文字体嵌入）
│  │  └─ xlsx_exporter.py        # Excel
│  └─ ui/
│     ├─ main_window.py          # 主窗口
│     ├─ camera.py               # 摄像头拍照
│     ├─ preview.py              # 图片 + 版面框预览
│     ├─ worker.py               # 后台识别线程
│     ├─ icons.py / theme.py     # 图标与样式
│     └─ __init__.py
├─ models/                       # 5 个离线 ONNX 模型
├─ assets/                       # 图标
├─ sample/                       # 样例图片 / PDF
├─ tests/                        # 单元测试
├─ tools/                        # 下载模型、样例、图标、打包辅助脚本
├─ requirements.txt              # Win10/11
├─ requirements-win7.txt         # Win7 / Python 3.8
├─ 安装依赖.bat / 启动文档提取.bat
├─ installer/                    # Win7 安装包（Inno Setup）与构建配置
├─ 安装依赖-Win7.bat / 启动文档提取-Win7.bat
├─ 打包EXE.bat / 打包EXE-Win7.bat
├─ 文档提取.spec                 # PyInstaller 配置
└─ hooks/                        # Qt 中文路径修复钩子
```

## 7. 已构建产物与验证

| 产物 | 说明 |
|---|---|
| Release：`文档提取-1.0.1-Win7-Setup.exe` | Win7 SP1 / 10 / 11 x64 安装版，含 VC++ 运行库检测安装 |
| Release：`文档提取-1.0.1-Win7-10-11-Portable.zip` | 同版本便携版，解压即用 |
| 本仓库 | 完整源码 + 5 个 ONNX 模型 + 文档 + 构建脚本 |
| `models/README.md` | 5 个模型的 SHA256 校验值 |
| `docs/示例输出/` | 真实识别结果导出的 Word/PDF/Excel 样例 |

打包后的 EXE 已执行以下验证：

- `文档提取.exe --smoke-test`：GUI 启动、Qt 插件、模型状态正常；
- `文档提取.exe --self-test sample\样例文档.png`：Python 3.8 运行时下离线 OCR 全流程，识别 1 页、1 个表格、352 字，三种格式导出成功；
- 安装包静默安装后再次执行 self-test，结果一致；
- 拖拽 PNG/JPG/JPEG/BMP/TIFF/PDF 到窗口已逐项测试；摄像头后端已用真实 UVC 设备测试。

## 8. 开发、测试与打包

### 8.1 单元测试

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

覆盖：合并单元格解析、异常 HTML、HTML/纯文本渲染、Word/PDF/Excel 导出、模型完整性、JSON 序列化。

### 8.2 端到端测试

```bat
.venv\Scripts\python.exe tools\run_sample.py
```

会识别 `sample/样例文档.png`、生成三种输出到 `outputs/sample_result/`。样例包含标题、段落、表格和页脚。`sample/合并表格样例.png` 可验证合并单元格；`sample/两页样例.pdf` 可验证多页 PDF。`docs/示例输出/` 中已放置一份由真实识别结果导出的 Word/PDF/Excel，可直接查看效果。

### 8.3 打包

```bat
打包EXE.bat
```

输出 `dist\文档提取\文档提取.exe`（onedir，整个文件夹分发）。PyInstaller 会把 Python 运行时、Qt、ONNX Runtime、模型全部打包，目标机无需安装 Python。

Win7 使用 `打包EXE-Win7.bat`。

打安装包用 `installer\打包安装包-Win7.bat`，需要 Inno Setup 6，以及 `installer\vc_redist.x64.exe`
（微软 VC++ 运行库，25 MB，不随仓库分发；脚本发现缺失会自动下载，也可手动放到 `installer\` 下）。

### 8.4 性能参考

在 4 核 CPU、Windows 11 的测试机上（CPU 模式）：

| 场景 | 耗时 |
|---|---|
| 单页 A4 图片（文字+表格） | 约 5–8 秒 |
| 两页 PDF | 约 10–15 秒 |
| 首次加载模型 | 额外 1–3 秒 |

清晰度「标准」在速度与准确率间平衡；小字文档可选「高清」，耗时更长；「极速」适合快速预览。

## 9. 常见问题

**Q：提示缺少模型？**  
运行 `tools\download_models.py`，或确认 `models/` 下 5 个文件齐全且大小正确。

**Q：摄像头没有画面？**  
软件会自动尝试 DirectShow、Media Foundation，并兼容 720p/480p 两种 UVC 配置。请检查：摄像头是否被微信/钉钉占用；设备管理器是否有黄色感叹号；Win7 是否安装 UVC 驱动/VC++ 运行库。可点「重新检测」或换一个摄像头序号；仍不可用时可上传照片。

**Q：拖入 PNG/JPG 没反应？**  
软件支持把 PNG、JPG/JPEG、BMP、TIFF、WebP、PDF 拖到窗口任意位置。若仍无反应，请确认文件后缀正确、文件未被其他程序独占；也可以点「上传识别」选择文件。

**Q：PDF 识别很慢？**  
PDF 会逐页渲染并识别；100 页为上限。建议先拆分或只提取需要的页。

**Q：表格识别不完整？**  
表格模型对无边框、严重倾斜、超宽表格效果有限。拍照时保持表格完整、光线均匀；可先用图片裁剪工具裁出表格再识别。

**Q：导出的 PDF 中文字体不对？**  
导出会优先使用系统 `simsun.ttc` / `simhei.ttf` / `msyh.ttc`，Windows 7 及以上默认自带。若精简系统缺少字体，会退回 PDF 内置 CID 字体。

**Q：Win7 提示 onnxruntime_pybind11_state 找不到指定的程序？**  
v1.0.1 安装版已内置 **ONNX Runtime 1.14.1**（模型为 ONNX IR 8），这是为 Win7 选定的兼容版本。请不要把旧版 v1.0.0 的 `_internal\onnxruntime` 复制到新版目录，也不要手动升级到 ORT 1.17+（1.17 依赖 Win8+ 的 PathCch 等 API）。建议卸载旧版后全新安装 v1.0.1。

**Q：安装协议页/说明文件乱码？**  
v1.0.1 安装包的协议页改为 Unicode RTF；安装目录中的说明文件为带 BOM 的 UTF-8，Win7 记事本可正常打开。请使用 v1.0.1 安装包，不要用旧版文件覆盖。

**Q：程序路径有中文可以吗？**  
运行时已做 Qt 中文路径修复，但仍建议安装/解压到纯英文路径，尤其是 Win7。

**Q：会上传文件吗？**  
不会。所有识别、渲染和导出都在本机完成，程序不发起文件上传请求。

## 10. 已知限制

- 手写体、艺术字、低分辨率/严重模糊图片的准确率有限。
- 竖排、多栏复杂排版按版面模型结果排序，必要时请人工校对。
- 表格线缺失时，SLANet 可能将相邻单元格合并或拆分错误。
- PDF 内的矢量图/公式/印章目前不做专门结构化，只作为图片区域跳过。
- 结果区为只读预览，复制或导出后再编辑；软件不做自动保存工程文件，请及时导出。

## 11. 许可与第三方组件

**Copyright (C) 2026 盛晗。本项目以 [GNU Affero General Public License v3.0](LICENSE)（AGPL-3.0）发布。**

选择 AGPL-3.0 而不是更宽松协议的原因：本项目在进程内链接了 **PyMuPDF**（AGPLv3 / 商业双许可）
与 **PyQt5**（GPLv3 / 商业双许可）。按这两个上游许可的要求，对外分发（或作为网络服务提供）本软件时，
必须提供完整对应源码；不能闭源分发，除非向 Riverbank Computing 与 Artifex 购买商业授权。

| 组件 | 许可 | 用途 |
|---|---|---|
| PyQt5 / Qt 5 | GPLv3 / 商业双许可 | 桌面界面 |
| PyMuPDF | AGPLv3 / 商业双许可 | PDF 逐页渲染 |
| PaddleOCR PP-OCRv5 / PP-Structure 模型 | Apache-2.0 | 检测 / 识别 / 版面 / 表格模型 |
| RapidOCR、RapidLayout、RapidTable | Apache-2.0 | OCR 前后处理与 ONNX 封装 |
| ONNX Runtime | MIT | CPU 推理 |
| ReportLab / python-docx / openpyxl | BSD / MIT / MIT | 导出 |
| OpenCV、NumPy、Pillow、Shapely、pyclipper | Apache-2.0 / BSD / HPND / BSD / MIT | 图像与几何处理 |

完整清单与说明见 [第三方许可说明.md](第三方许可说明.md)。该说明不构成法律意见；企业内使用时
请由法务/合规确认具体义务。

## 12. 参与贡献

- 提交问题请附：Windows 版本、Python 版本、报错日志（`outputs/` 或控制台输出）、复现步骤。
- 提交代码前请先跑 `python -m unittest discover -s tests -v`，并确认没有把 `dist/`、`release/`、
  `.venv/`、`outputs/` 或 `installer/vc_redist.x64.exe` 混进提交。
- 本项目不接受任何绕过 DRM、破解商业模型授权或分发来源不明 ONNX 模型的贡献。

---

**软件名称：** 文档提取（doc-extract-ocr）  
**作者：** 盛晗  
**版本：** 1.0.1  
**技术栈：** Python / PyQt5 / ONNX Runtime / PP-OCRv5 mobile / PP-Structure / PyMuPDF / python-docx / ReportLab / openpyxl


