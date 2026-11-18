@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv38\Scripts\python.exe" (
  echo 请先运行「安装依赖-Win7.bat」。
  pause
  exit /b 1
)
set "VPY=.venv38\Scripts\python.exe"
echo [1/3] 检查 PyInstaller（Win7 使用 5.13.2）...
"%VPY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
  "%VPY%" -m pip install "pyinstaller==5.13.2" --disable-pip-version-check
  if errorlevel 1 (
    echo 安装失败。
    pause
    exit /b 1
  )
)
echo [2/3] 生成图标 ...
"%VPY%" tools\make_icon.py
echo [3/3] 打包 ...
"%VPY%" -m PyInstaller "文档提取.spec" --noconfirm --clean --distpath dist-win7 --workpath build-win7
if errorlevel 1 (
  echo 打包失败。
  pause
  exit /b 1
)
echo.
echo 打包完成：dist\文档提取\文档提取.exe
echo 该 EXE 由 Python 3.8 构建，面向 Windows 7 SP1 x64。
pause
