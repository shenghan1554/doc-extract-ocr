@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" app.py
  exit /b 0
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
  if errorlevel 1 pause
  exit /b 0
)

python --version >nul 2>nul
if errorlevel 1 (
  echo 未找到运行环境，请先双击「安装依赖.bat」。
  pause
  exit /b 1
)
python app.py
if errorlevel 1 pause
