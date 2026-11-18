# 贡献指南

感谢你愿意改进「文档提取」。这是一个完全离线运行的 Windows 桌面 OCR 工具，
技术栈为 Python + PyQt5 + ONNX Runtime，代码量不大、结构清晰。

## 行为准则

参与本项目即表示你同意保持友善、就事论事的交流方式。

## 环境搭建

| 依赖 | 版本 | 说明 |
|---|---|---|
| Windows | 10 / 11 x64（Win7 见 README §5） | 摄像头与 GUI 依赖 Win32 |
| Python | 3.10–3.12（Win7 构建用 3.8） | |
| 磁盘 | 约 1.5 GB | 依赖 + 模型 + 虚拟环境 |

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe tools\download_models.py --check   :: 校验模型
.venv\Scripts\python.exe app.py
```

## 改哪里

```
app.py                  入口：高 DPI、Qt 插件路径、日志、异常捕获
doc_extract/engine.py   识别流水线（OCR / 版面 / 表格 / PDF / 纠偏）
doc_extract/models.py   文档、页面、块、表格数据结构
doc_extract/table_utils.py  容错 HTML 表格解析、合并单元格、TSV
doc_extract/render.py   结果 HTML / 纯文本 / 复制文本
doc_extract/export/     Word / PDF / Excel 导出
doc_extract/ui/         主窗口、摄像头、预览、后台线程、主题
tests/                  不需要模型与 GUI 的快速单元测试
tools/                  模型下载、样例生成、图标、打包辅助
installer/              Inno Setup 安装包脚本（Win7）
```

约定：

1. **识别流水线与 UI 分离**：`engine.py` 不 import PyQt5，`ui/` 不直接做推理。
2. **导出器保持无状态**：`export/*.py` 只接受 `DocumentResult` 返回字节/路径，便于测试。
3. **新增依赖要谨慎**：本项目强调离线与 CPU only，不要引入需要 GPU、联网或大体积运行时的新依赖；
   新增依赖必须写进 `requirements.txt` 与 `第三方许可说明.md`。
4. **模型文件不要替换**：`models/` 下的 SHA256 由 CI 固定校验；确需升级模型请同时更新
   `models/README.md`、`tools/download_models.py` 与 CI 中的校验值。
5. **界面文案用中文**，与现有风格保持一致。

## 测试

```bat
:: 单元测试（不需要模型，秒级）
.venv\Scripts\python.exe -m unittest discover -s tests -v

:: 端到端（需要模型，会生成导出样例）
.venv\Scripts\python.exe tools\run_sample.py
```

提交前请确认：

- [ ] `python -m unittest discover -s tests -v` 通过
- [ ] 没有提交 `dist/`、`release/`、`.venv/`、`outputs/`、`installer/vc_redist.x64.exe`
- [ ] 没有提交个人路径、密钥或含敏感信息的文档
- [ ] 没有引入 DRM 绕过或来源不明的 ONNX 模型

## 提交规范

采用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

```
feat(engine): 支持竖排文本行排序
fix(export): 修复合并单元格在 Word 中的边框丢失
perf(engine): 复用 OCR 会话，减少模型重复加载
docs: 补充 Win7 缺少 DLL 的排查步骤
```

## Pull Request

1. 从 `main` 切分支：`feat/xxx`、`fix/xxx`、`docs/xxx`。
2. 一个 PR 只做一件事；描述里写清动机、做法与验证方式。
3. 涉及识别效果变化时，请附上修改前后的对比截图与样例输出。
4. 涉及许可证的新依赖，会在 review 时重点确认。

## 许可

本项目以 **AGPL-3.0** 发布（见 [LICENSE](LICENSE)）。提交贡献即表示你同意以同一许可授权你的代码，
并确认你有权这样做。若你在公司内使用，请遵守 AGPL 的源码提供义务。