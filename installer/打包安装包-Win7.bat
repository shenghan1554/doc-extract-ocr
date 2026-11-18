@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

set "APP=%~dp0..\dist\文档提取"
if not exist "%APP%\文档提取.exe" (
  echo 未找到 %APP%\文档提取.exe
  echo 请先运行「打包EXE-Win7.bat」生成 Win7 程序目录。
  pause
  exit /b 1
)

rem vc_redist.x64.exe 是微软运行库，体积 25MB，不随仓库分发；缺失时自动下载
if not exist "%~dp0vc_redist.x64.exe" (
  echo 缺少 vc_redist.x64.exe，尝试下载 Microsoft Visual C++ 2015-2022 x64 运行库...
  where curl >nul 2>nul
  if not errorlevel 1 (
    curl -L --fail -o "%~dp0vc_redist.x64.exe" "https://aka.ms/vs/17/release/vc_redist.x64.exe"
  ) else (
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '%~dp0vc_redist.x64.exe'"
  )
  if not exist "%~dp0vc_redist.x64.exe" (
    echo 下载失败。请手动下载后放到 %~dp0 ：
    echo   https://aka.ms/vs/17/release/vc_redist.x64.exe
    pause
    exit /b 1
  )
)

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "D:\InnoSetup\ISCC.exe" set "ISCC=D:\InnoSetup\ISCC.exe"
if not defined ISCC (
  echo 未找到 Inno Setup 6 的 ISCC.exe。
  echo 请安装 Inno Setup 6.2.2，或修改本脚本中的 ISCC 路径。
  pause
  exit /b 1
)

"%ISCC%" /DMyAppSource="%APP%" "%~dp0win7_setup.iss"
if errorlevel 1 (
  echo 安装包编译失败。
  pause
  exit /b 1
)
echo 安装包已生成到 release 目录。
pause
