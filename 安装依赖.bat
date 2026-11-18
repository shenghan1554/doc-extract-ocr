@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 文档提取 - 安装运行环境

echo ============================================
echo   文档提取 - 安装运行环境
echo   PP-OCRv5 mobile / PP-Structure / CPU
echo ============================================
echo.

set "PYTHON=python"
%PYTHON% --version >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Python。请先安装 Python 3.10-3.12 64 位，
  echo        安装时勾选 "Add Python to PATH"。
  echo        下载：https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

for /f "delims=" %%v in ('%PYTHON% -c "import sys;print(sys.version_info[0],sys.version_info[1])"') do set "PYVER=%%v"
echo 使用 Python %PYVER%

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] 创建虚拟环境 .venv ...
  %PYTHON% -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败。
    pause
    exit /b 1
  )
)

set "VPY=.venv\Scripts\python.exe"
echo [2/4] 升级 pip ...
"%VPY%" -m pip install --upgrade pip --disable-pip-version-check

echo [3/4] 安装识别依赖，首次约需下载 200 MB ...
"%VPY%" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 (
  echo.
  echo [错误] 依赖安装失败。请检查网络，或使用国内镜像：
  echo        .venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  pause
  exit /b 1
)

echo [4/4] 校验离线模型 ...
"%VPY%" tools\download_models.py --check
if errorlevel 1 (
  echo 模型不完整，开始下载 ...
  "%VPY%" tools\download_models.py
  if errorlevel 1 (
    echo [错误] 模型下载失败，请查看上方提示。
    pause
    exit /b 1
  )
)

echo.
echo 安装完成。双击「启动文档提取.bat」即可使用。
pause
