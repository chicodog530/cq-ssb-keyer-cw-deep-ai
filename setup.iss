[Setup]
AppName=CQ Voice Keyer
AppVersion=1.0
DefaultDirName={pf}\CQ Voice Keyer
DefaultGroupName=CQ Voice Keyer
OutputDir=installer_out
OutputBaseFilename=CQVoiceKeyer_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=UniversalRadio_AppIcon.ico
UninstallDisplayIcon={app}\CQ Voice Keyer.exe
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\CQ Voice Keyer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CQ Voice Keyer"; Filename: "{app}\CQ Voice Keyer.exe"
Name: "{commondesktop}\CQ Voice Keyer"; Filename: "{app}\CQ Voice Keyer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CQ Voice Keyer.exe"; Description: "Launch CQ Voice Keyer"; Flags: nowait postinstall skipifsilent
