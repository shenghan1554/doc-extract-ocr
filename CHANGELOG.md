# 更新记录

## 开源发布（2026-11-18）

- 源码以 **AGPL-3.0** 公开（原 LICENSE 写的是 GPLv3；因程序链接了 AGPLv3 的 PyMuPDF，整体许可更正为 AGPL-3.0）
- 5 个 ONNX 模型随仓库分发，clone 下来即可离线运行
- 预编译安装版 / 便携版移至 GitHub Releases，仓库只保留源码与模型

## v1.0.1（2026-11-18）

本版本与 v1.0.0 的差异：

### 摄像头

- 修复免驱 UVC 摄像头无法调用的问题
- 自动扫描摄像头索引 0–7
- 后端依次尝试 DirectShow → Media Foundation → 自动
- 同时尝试 720p MJPG 与 480p 两种 UVC 配置
- 打开摄像头后预热读取多帧，避免“已连接但无画面”
- 记住上次成功的摄像头序号，支持重新检测
- 摄像头不可用时给出占用/驱动/VC++ 的明确提示

### 拖拽上传

- 修复 PNG/JPG 等文件拖到窗口无反应的问题
- 改为应用级拖拽事件过滤器，窗口任意位置均可接收
- 支持 PNG、JPG/JPEG、BMP、TIFF、WebP、PDF
- 逐项测试通过

### Windows 7

- 新增 Win7 SP1 x64 安装版 `文档提取-1.0.1-Win7-Setup.exe`
- 使用 Python 3.8 + PyInstaller 5.13.2 构建
- 模型降为 ONNX IR 8，兼容 ONNX Runtime 1.14
- 修复 Win7 上 `onnxruntime_pybind11_state` DLL 加载失败：ORT 1.17 → 1.14.1，模型 IR 9 → IR 8
- 修复 RapidTable 向 ORT 1.14 传递 pathlib.Path 导致表格加载失败
- 安装程序检测并安装 VC++ 2015–2022 运行库
- 安装协议页改为 Unicode RTF，修复中文乱码
- 安装目录说明文件改为 UTF-8 BOM，Win7 记事本可正常显示
- 安装后 OCR、表格、三种导出均通过自检

### 作者与标识

- 软件作者：**盛晗**
- 写入 EXE 版本信息、安装包发布者、关于信息
- 写入 Word/PDF 导出元数据
- 界面标题显示版本号，便于与 v1.0.0 区分

## v1.0.0

- 首个版本
- PP-OCRv5 mobile + PP-Structure CPU 识别
- 拍照/上传、文字/表格/PDF 提取
- Word/PDF/Excel 导出与复制
