; Inno Setup script: the classic Windows install wizard for Pixel Slides.
; Build the app first (packaging\build-windows.ps1 does both), then:
;   iscc packaging\pixel-slides.iss      -> dist\installer\PixelSlides-Setup-<version>.exe
;
; Installs per user (no admin prompt) into %LOCALAPPDATA%\Programs\Pixel Slides.
; Decks live in Documents\Pixel Slides and are kept on uninstall.

#define AppName "Pixel Slides"
#ifndef AppVersion
  #define AppVersion "0.4.0"
#endif

[Setup]
AppId={{6B1E3A52-4C1D-4E59-9C1B-50F1A6D2E8C3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=TCsM
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
InfoAfterFile=after-install.txt
OutputDir=..\dist\installer
OutputBaseFilename=PixelSlides-Setup-{#AppVersion}
SetupIconFile=icons\pixel-slides.ico
UninstallDisplayIcon={app}\Pixel Slides.exe
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Pixel Slides\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Pixel Slides.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Pixel Slides.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Pixel Slides.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
