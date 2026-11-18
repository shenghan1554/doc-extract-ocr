@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv38\Scripts\python.exe" (
  echo 请先双击「安装依赖-Win7.bat」。
  pause
  exit /b 1
)
".venv38\Scripts\python.exe" app.py
if errorlevel 1 pause
