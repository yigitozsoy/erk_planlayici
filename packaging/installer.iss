; erk — Inno Setup 6 kurulum betiği (tamga ailesi; uygulamanın eski adı alpha)
; Doğrudan değil, packaging\build.ps1 üzerinden derleyin (önce PyInstaller çıktısı ve version.iss gerekir).
; Yönetici izni istemez: varsayılan olarak %LOCALAPPDATA%\Programs\erk klasörüne kurulur.
; Kullanıcı verileri (Documents\erk, %LOCALAPPDATA%\erk) kaldırmada SİLİNMEZ; eski Documents\alpha /
; %LOCALAPPDATA%\alpha klasörlerini erk ilk açılışta kendisi yeniden adlandırır (erk\config.py), kurulum onlara dokunmaz.
;
; alpha'dan yükseltme: AppId aynı (alpha'nın kurulumu yerinde güncellenir, Programlar listesinde tek kayıt kalır)
; ama klasör yeni (UsePreviousAppDir=no → {autopf}\erk). Kurulumdan önce açık alpha.exe kapatılır, kurulum bitince
; eski klasördeki alpha dosyaları silinir; eski kısayollar, App Paths ve "Windows ile başlat" (Run) değeri kaldırılır
; (Run açıksa erk adıyla yeniden yazılır).

#include "version.iss"
#define AppName "erk"
#define AppExe "erk.exe"
#define AppUserModelID "tamga.erk"
#define OldName "alpha"
#define OldExe "alpha.exe"
#define AppGuid "{F860D8FB-6391-4191-A455-E7B16CC98124}"

[Setup]
; AppId alpha ile aynı: yükseltme. DEĞİŞTİRME.
AppId={{F860D8FB-6391-4191-A455-E7B16CC98124}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Yiğit Özsoy
AppPublisherURL=https://github.com/yigitozsoy/erk_planlayici
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
; alpha'nın klasörü / Başlat grubu yeniden kullanılmasın
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
; Güncellemede açık erk (ana pencere ya da masaüstü widget'ı) kapatılsın; eski klasördeki alpha.exe'yi [Code] kapatır
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
; alpha'nın kısayolları: Başlat grubu "alpha" (uygulama + kaldır kısayolu, Türkçe / İngilizce adla) ve masaüstü
Type: files; Name: "{autoprograms}\{#OldName}\{#OldName}.lnk"
Type: files; Name: "{autoprograms}\{#OldName}\{#OldName} programını kaldır.lnk"
Type: files; Name: "{autoprograms}\{#OldName}\Uninstall {#OldName}.lnk"
Type: dirifempty; Name: "{autoprograms}\{#OldName}"
Type: files; Name: "{autoprograms}\{#OldName}.lnk"
Type: files; Name: "{autodesktop}\{#OldName}.lnk"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Registry]
; "Windows ile başlat" uygulamanın içinden açılır (HKCU Run → erk); kaldırınca kaydı da gitsin
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "erk"; Flags: uninsdeletevalue dontcreatekey
; alpha'nın eski kayıtları (Run değeri [Code]'da erk'e çevrilir): App Paths, "Birlikte aç" listesindeki Applications\alpha.exe
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#OldExe}"; Flags: deletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#OldExe}"; Flags: deletekey

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  OldAppDir: String;   // alpha'nın kurulu olduğu klasör (yükseltmede; yoksa boş)

// Önceki kurulumun klasörü (aynı AppId'nin kaldırma kaydından): alpha'dan yükseltmede eski klasör
function PreviousAppDir(): String;
var
  Key: String;
begin
  Result := '';
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppGuid}_is1';
  if not RegQueryStringValue(HKA, Key, 'Inno Setup: App Path', Result) then
    if not RegQueryStringValue(HKCU, Key, 'Inno Setup: App Path', Result) then
      if not RegQueryStringValue(HKLM, Key, 'Inno Setup: App Path', Result) then
        Result := '';
end;

function InitializeSetup(): Boolean;
begin
  OldAppDir := PreviousAppDir();
  Result := True;
end;

function HasOldApp(): Boolean;
begin
  Result := (OldAppDir <> '') and FileExists(AddBackslash(OldAppDir) + '{#OldExe}');
end;

function IsOldDirToClean(): Boolean;
begin
  Result := HasOldApp() and
            (CompareText(RemoveBackslashUnlessRoot(OldAppDir), RemoveBackslashUnlessRoot(ExpandConstant('{app}'))) <> 0);
end;

// Açık alpha'yı kapat: önce nazikçe (WM_CLOSE; kayıtlar 400 ms içinde zaten diske yazılmış olur), 3 sn sonra zorla
// (masaüstü widget'ı açıksa pencere kapanınca uygulama yaşamaya devam eder).
procedure QuitOldApp();
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM {#OldExe}', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Sleep(3000);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM {#OldExe} /F', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if HasOldApp() then
    QuitOldApp();
  Result := '';
end;

// alpha'nın eski kurulum klasörünü kaldırır. Varsayılan adlı klasör ("alpha") tümüyle silinir; kullanıcı başka bir
// klasör seçtiyse yalnızca kurulumun koyduğu dosyalar silinir, klasör boşsa kaldırılır (başka dosyalara dokunulmaz).
procedure CleanOldAppDir();
var
  D: String;
begin
  if not IsOldDirToClean() then Exit;
  D := RemoveBackslashUnlessRoot(OldAppDir);
  if CompareText(ExtractFileName(D), '{#OldName}') = 0 then
    DelTree(D, True, True, True)
  else
  begin
    DeleteFile(D + '\{#OldExe}');
    DeleteFile(D + '\LICENSE.txt');
    DeleteFile(D + '\unins000.exe');
    DeleteFile(D + '\unins000.dat');
    DeleteFile(D + '\unins000.msg');
    DelTree(D + '\_internal', True, True, True);
    RemoveDir(D);
  end;
end;

// "Windows ile başlat" alpha adıyla açıksa erk'e çevir (komut uygulamanın yazdığıyla aynı: --widget)
procedure MoveAutostart();
var
  Run, Old: String;
begin
  Run := 'Software\Microsoft\Windows\CurrentVersion\Run';
  if RegQueryStringValue(HKCU, Run, '{#OldName}', Old) then
  begin
    RegWriteStringValue(HKCU, Run, '{#AppName}', '"' + ExpandConstant('{app}\{#AppExe}') + '" --widget');
    RegDeleteValue(HKCU, Run, '{#OldName}');
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MoveAutostart();
    CleanOldAppDir();
  end;
end;
