@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 请先运行「安装依赖.bat」创建运行环境。
  pause
  exit /b 1
)
set "VPY=.venv\Scripts\python.exe"
echo [1/3] 检查 PyInstaller ...
"%VPY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
  "%VPY%" -m pip install "pyinstaller==6.22.3" --disable-pip-version-check
  if errorlevel 1 (
    echo 安装 PyInstaller 失败。
    pause
    exit /b 1
  )
)
echo [2/3] 生成图标 ...
"%VPY%" tools\make_icon.py
echo [3/3] 打包（约 3-8 分钟）...
"%VPY%" -m PyInstaller "文档提取.spec" --noconfirm --clean --distpath dist --workpath build
if errorlevel 1 (
  echo.
  echo 打包失败，请查看上方日志。
  pause
  exit /b 1
)
echo.
echo 打包完成：dist\文档提取\文档提取.exe
echo 整个 dist\文档提取 文件夹可以复制到其他 Windows 10/11 x64 电脑运行。
pause
