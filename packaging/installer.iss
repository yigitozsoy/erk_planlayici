; erk — Inno Setup 6 kurulum betiği (tamga ailesi)
; Doğrudan değil, packaging\build.ps1 üzerinden derleyin (önce PyInstaller çıktısı ve version.iss gerekir).
; Yönetici izni istemez: varsayılan olarak %LOCALAPPDATA%\Programs\erk klasörüne kurulur.
; Kullanıcı verileri (Documents\erk, %LOCALAPPDATA%\erk) kaldırmada SİLİNMEZ.

#include "version.iss"
#define AppName "erk"
#define AppExe "erk.exe"
#define AppUserModelID "tamga.erk"

[Setup]
; AppId kurulu sürümle aynı kalmalı (yerinde güncelleme). DEĞİŞTİRME.
AppId={{F860D8FB-6391-4191-A455-E7B16CC98124}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Yiğit Özsoy
AppPublisherURL=https://github.com/yigitozsoy/erk_planlayici
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UsePreviousAppDir=no
UsePreviousGroup=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\build\installer
OutputBaseFilename=erk-setup-{#AppVersion}
SetupIconFile=..\erk\assets\logo.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName} {#AppVersion}
VersionInfoDescription={#AppName} kurulumu
VersionInfoProductName={#AppName}
VersionInfoVersion={#AppVersion}
; Lisans sayfası yok (gamma gibi); LICENSE.txt (tüm hakları saklıdır) kurulum klasörüne konur.
Compression=lzma2/ultra64
SolidCompression=yes
; Görünüm (Inno Setup 6.7+, gamma ile aynı): Windows 11 stili, Windows'un açık/koyu temasını izler, ayırıcı çizgi yok.
; Renkler erk'in temalarıyla aynı (koyu: siyah, açık: beyaz); görseller make_meta.py'de üretilir.
WizardStyle=modern dynamic windows11 hidebevels
WizardBackColor=#ffffff
WizardBackColorDynamicDark=#0f0f0f
WizardImageBackColor=#ffffff
WizardImageBackColorDynamicDark=#0f0f0f
WizardSmallImageBackColor=#ffffff
WizardSmallImageBackColorDynamicDark=#0f0f0f
WizardSmallImageFile={#WizSmall}
WizardSmallImageFileDynamicDark={#WizSmallDark}
WizardImageFile={#WizLarge}
WizardImageFileDynamicDark={#WizLargeDark}
; Güncellemede açık erk (ana pencere ya da masaüstü widget'ı) kapatılsın
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
turkish.KeepData=Kayıtlarınız (Belgeler\erk) kaldırmada silinmez.
english.KeepData=Your data (Documents\erk) is kept when uninstalling.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\dist\erk\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; eski sürümden kalan PyInstaller dosyaları karışmasın
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Registry]
; "Windows ile başlat" uygulamanın içinden açılır (HKCU Run → erk); kaldırınca kaydı da gitsin
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "erk"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
