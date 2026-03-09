; GestureFlow Installer - Inno Setup Script
; Builds a proper Windows installer with Start Menu shortcuts, uninstaller, etc.

#define MyAppName "GestureFlow"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Karthikeya"
#define MyAppURL "https://github.com/Karthikeya-B19/GestureFlow"

[Setup]
AppId={{B5A2F8E1-7C3D-4A9B-8E6F-1D2C3B4A5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=GestureFlow-Setup-v{#MyAppVersion}
SetupIconFile=..\assets\icons\app_icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (HCI + Canvas)"
Name: "hci"; Description: "GestureFlow HCI only (system control)"
Name: "canvas"; Description: "GestureFlow Canvas only (drawing)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "hci"; Description: "GestureFlow HCI — Gesture-based system control (cursor, scroll, volume, brightness, media, tab switch)"; Types: full hci custom
Name: "canvas"; Description: "GestureFlow Canvas — Gesture-controlled drawing canvas"; Types: full canvas custom

[Tasks]
Name: "desktopicon_hci"; Description: "Create a desktop shortcut for GestureFlow HCI"; Components: hci; GroupDescription: "Desktop shortcuts:"
Name: "desktopicon_canvas"; Description: "Create a desktop shortcut for GestureFlow Canvas"; Components: canvas; GroupDescription: "Desktop shortcuts:"

[Files]
; HCI App files
Source: "..\dist\GestureFlowHCI\*"; DestDir: "{app}\HCI"; Components: hci; Flags: ignoreversion recursesubdirs createallsubdirs

; Canvas App files
Source: "..\dist\GestureFlowCanvas\*"; DestDir: "{app}\Canvas"; Components: canvas; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\GestureFlow HCI"; Filename: "{app}\HCI\GestureFlowHCI.exe"; Components: hci; Comment: "Gesture-based system control"
Name: "{group}\GestureFlow Canvas"; Filename: "{app}\Canvas\GestureFlowCanvas.exe"; Components: canvas; Comment: "Gesture-controlled drawing canvas"
Name: "{group}\Uninstall GestureFlow"; Filename: "{uninstallexe}"

; Desktop
Name: "{autodesktop}\GestureFlow HCI"; Filename: "{app}\HCI\GestureFlowHCI.exe"; Tasks: desktopicon_hci; Comment: "Gesture-based system control"
Name: "{autodesktop}\GestureFlow Canvas"; Filename: "{app}\Canvas\GestureFlowCanvas.exe"; Tasks: desktopicon_canvas; Comment: "Gesture-controlled drawing canvas"

[Run]
Filename: "{app}\HCI\GestureFlowHCI.exe"; Description: "Launch GestureFlow HCI"; Flags: nowait postinstall skipifsilent; Components: hci
Filename: "{app}\Canvas\GestureFlowCanvas.exe"; Description: "Launch GestureFlow Canvas"; Flags: nowait postinstall skipifsilent unchecked; Components: canvas

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
