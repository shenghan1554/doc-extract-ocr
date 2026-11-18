; Inno Setup 6.2.2 script for the Windows 7 / 8 / 10 / 11 x64 installer.
; Compile with:
;   "D:\InnoSetup\ISCC.exe" installer\win7_setup.iss

#define MyAppName "文档提取"
#define MyAppVersion "1.0.1"
#define MyAppExeName "文档提取.exe"
#ifndef MyAppSource
#define MyAppSource "..\dist\文档提取"
#endif

[Setup]
AppId={{5A7E2E2A-7C1D-4C90-9E2A-6D8F3B7A1C42}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=盛晗
AppPublisherURL=https://example.invalid/doc-extract
AppCopyright=Copyright (C) 2026 盛晗
AppComments=PP-OCRv5 mobile / PP-Structure offline OCR on CPU
DefaultDirName={pf}\DocExtract
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=文档提取-1.0.1-Win7-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.0.1.0
VersionInfoDescription={#MyAppName} Setup
VersionInfoCompany=盛晗
VersionInfoCopyright=Copyright (C) 2026 盛晗
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
LicenseFile=license.rtf

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#MyAppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "docs\README.txt"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion
Source: "docs\CHANGELOG.txt"; DestDir: "{app}"; DestName: "CHANGELOG.txt"; Flags: ignoreversion
Source: "docs\使用说明.txt"; DestDir: "{app}"; DestName: "使用说明.txt"; Flags: ignoreversion
Source: "docs\第三方许可说明.txt"; DestDir: "{app}"; DestName: "第三方许可说明.txt"; Flags: ignoreversion
Source: "docs\LICENSE.txt"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Microsoft Visual C++ 2015-2022 Redistributable..."; Flags: waituntilterminated; Check: NeedsVCRedist
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsVCRedist: Boolean;
var
  Installed: Cardinal;
begin
  Result := True;
  if RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) then
  begin
    if Installed = 1 then
      Result := False;
  end;
end;
