@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 文档提取 - Windows 7 兼容环境安装

echo ============================================
echo   文档提取 - Windows 7 兼容环境
echo   需要 Python 3.8.10 x64
echo ============================================
echo.

py -3.8 --version >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Python 3.8。
  echo.
  echo Windows 7 最高只能使用 Python 3.8.10。请先安装：
  echo   python-3.8.10-amd64.exe
  echo 安装时勾选 "Add Python 3.8 to PATH"。
  echo.
  echo 如已安装但未注册 py 启动器，可把下面的 py -3.8 改为完整 python.exe 路径。
  pause
  exit /b 1
)

if not exist ".venv38\Scripts\python.exe" (
  echo [1/4] 创建 Python 3.8 虚拟环境 .venv38 ...
  py -3.8 -m venv .venv38
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败。
    pause
    exit /b 1
  )
)

set "VPY=.venv38\Scripts\python.exe"

echo [2/4] 升级 pip ...
"%VPY%" -m pip install --upgrade "pip<25" --disable-pip-version-check

echo [3/4] 安装 Win7 兼容依赖 ...
"%VPY%" -m pip install -r requirements-win7.txt --disable-pip-version-check
if errorlevel 1 (
  echo.
  echo [错误] 安装失败。建议使用国内镜像重试：
  echo   .venv38\Scripts\python.exe -m pip install -r requirements-win7.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  pause
  exit /b 1
)

echo [3.2/4] 安装表格结构库（跳过其 ORT>1.17 的元数据约束）...
"%VPY%" -m pip install --no-deps "rapid-table==3.0.2" --disable-pip-version-check -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
if errorlevel 1 (
  echo [错误] rapid-table 安装失败。
  pause
  exit /b 1
)

echo [3.5/4] 修补 RapidLayout 的 Python 3.8 注解兼容性 ...
"%VPY%" tools\patch_win7_deps.py
if errorlevel 1 (
  echo [警告] RapidLayout 补丁未成功，版面分析可能不可用。
)

echo [4/4] 校验离线模型 ...
"%VPY%" tools\download_models.py --check
if errorlevel 1 (
  "%VPY%" tools\download_models.py
  if errorlevel 1 (
    echo [错误] 模型下载失败。
    pause
    exit /b 1
  )
)

echo.
echo 安装完成。双击「启动文档提取-Win7.bat」。
echo 如果程序启动时报缺少 api-ms-win-core DLL，请阅读 README 的 Win7 章节。
pause
