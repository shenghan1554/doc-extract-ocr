# 离线模型目录

本目录包含「文档提取」运行所需的 5 个 ONNX 模型/字符集文件。**不要重命名**，程序按文件名加载。

| 文件 | 用途 | SHA256 |
|---|---|---|
| `ch_PP-OCRv5_det_mobile.onnx` | PP-OCRv5 mobile 文本检测 | `df9029acca09cf62d86f987b25ab1e5aa6aec9dad7fad7a45f7baf6bb42fe4b4` |
| `ch_PP-OCRv5_rec_mobile.onnx` | PP-OCRv5 mobile 文本识别 | `7d5a05a77cc32d7409d7a1fec71d6501d2a154a02298a0d2a860aa1b703a7cc2` |
| `ppocrv5_dict.txt` | PP-OCRv5 中文字符集（18383 行） | `d1979e9f794c464c0d2e0b70a7fe14dd978e9dc644c0e71f14158cdf8342af1b` |
| `layout_cdla.onnx` | PP-Structure CDLA 版面分析 | `25b1f27ec56aa932a48f30cbd6293c358a156280f4b20b0a973bab210c39f62c` |
| `ch_ppstructure_mobile_v2_SLANet.onnx` | PP-Structure 表格结构 SLANet | `ddfc6c97ee4db2a5e9de4de8b6a14508a39d42d228503219fdfebfac364885e3` |

## 校验

```bat
.venv\Scripts\python.exe tools\download_models.py --check
```

## 重新下载

```bat
.venv\Scripts\python.exe tools\download_models.py
```

## 许可

模型来自 PaddlePaddle/PaddleOCR 公开模型及其 ONNX 导出，遵循 Apache License 2.0。详见项目根目录 `第三方许可说明.md`。

## 注意

- 全部推理在 CPU 上通过 ONNX Runtime 完成，不需要 PaddlePaddle 或 CUDA。
- 不要放入来源不明的 `.onnx` 文件；ONNX 模型可能包含可执行的自定义算子。
- 若模型文件损坏，程序会提示缺少模型或加载失败，请用校验脚本重新下载。


> 注：检测/识别模型已从上游 ONNX IR 10 降为 IR 8，以兼容 Windows 7 使用的 ONNX Runtime 1.14；算子集仍为 opset 14，模型计算逻辑未改。

