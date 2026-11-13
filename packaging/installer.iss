; alpha — Inno Setup 6 kurulum betiği
; Doğrudan değil, packaging\build.ps1 üzerinden derleyin (önce PyInstaller çıktısı ve version.iss gerekir).

#include "version.iss"
#define AppName "alpha"
#define AppExe "alpha.exe"

[Setup]
AppId={{F860D8FB-6391-4191-A455-E7B16CC98124}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Yiğit Özsoy
AppPublisherURL=https://github.com/yigitozsoy/alpha_dashboard
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\build\installer
OutputBaseFilename=alpha-setup-{#AppVersion}
SetupIconFile=..\alphaapp\assets\logo.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName} {#AppVersion}
LicenseFile=..\LICENSE
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Güncellemede açık alpha (ana pencere ya da masaüstü widget'ı) kapatılsın
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
turkish.KeepData=Verileriniz (%LOCALAPPDATA%\alpha) kaldırmada silinmez.
english.KeepData=Your data (%LOCALAPPDATA%\alpha) is kept when uninstalling.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\dist\alpha\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; eski sürümden kalan PyInstaller dosyaları karışmasın
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; "Windows ile başlat" uygulamanın içinden açılır; kaldırınca kaydı da gitsin
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "alpha"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
