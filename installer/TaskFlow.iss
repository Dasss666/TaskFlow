#define MyAppName "TaskFlow"
#define MyAppVersion "0.5.0"
#define MyAppPublisher "Dasss666"
#define MyAppExeName "TaskFlow.exe"

[Setup]
AppId={{C2B5B7A1-9C3D-4F17-9D18-8D2B1F9A8A70}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\TaskFlow
DefaultGroupName=TaskFlow
OutputDir=..\dist\installer
OutputBaseFilename=TaskFlow-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\TaskFlow"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TaskFlow"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch TaskFlow"; Flags: nowait postinstall skipifsilent
