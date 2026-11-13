<#
alpha — derleme betiği
  1) Bağımlılıkları kurar (isteğe bağlı)
  2) Sürüm bilgisini üretir (alphaapp/__init__.py → __version__)
  3) PyInstaller ile build\dist\alpha\alpha.exe
  4) Taşınabilir zip ve Inno Setup ile kurulum dosyası (build\installer)

Kullanım (proje kökünden):
  powershell -ExecutionPolicy Bypass -File packaging\build.ps1 [-InstallDeps] [-SkipInstaller] [-Python python]
#>
param(
    [switch]$InstallDeps,
    [switch]$SkipInstaller,
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

if ($InstallDeps) {
    Step "Bağımlılıklar kuruluyor"
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r requirements.txt pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "pip install başarısız" }
}

# açık alpha.exe dosyaları kilitler; derlemeden önce düzgünce kapat (veriler kaydedilsin), olmazsa dur
$running = @(Get-Process alpha -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$Root\build\dist\*" })
foreach ($p in $running) { & taskkill.exe /PID $p.Id | Out-Null }
foreach ($p in $running) {
    if (-not $p.WaitForExit(8000)) { throw "alpha hâlâ açık; kapatıp tekrar deneyin" }
}

Step "Sürüm bilgisi üretiliyor"
$Version = (& $Python packaging\make_meta.py).Trim()
if ($LASTEXITCODE -ne 0) { throw "make_meta.py başarısız" }
Write-Host "Sürüm: $Version"

Step "PyInstaller"
$Dist = Join-Path $Root "build\dist"
& $Python -m PyInstaller packaging\alpha.spec --noconfirm --clean --distpath $Dist --workpath (Join-Path $Root "build\work")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller başarısız" }
$App = Join-Path $Dist "alpha"
Copy-Item LICENSE (Join-Path $App "LICENSE.txt") -Force

Step "Taşınabilir zip"
$Out = Join-Path $Root "build\installer"
New-Item -ItemType Directory -Force $Out | Out-Null
$Zip = Join-Path $Out "alpha-portable-$Version.zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path $App -DestinationPath $Zip -CompressionLevel Optimal
Write-Host $Zip

if (-not $SkipInstaller) {
    Step "Inno Setup ile kurulum dosyası"
    $Iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
    if (-not $Iscc) {
        foreach ($c in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                         "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
            if (Test-Path $c) { $Iscc = $c; break }
        }
    }
    if (-not $Iscc) {
        Write-Warning "Inno Setup 6 bulunamadı; kurulum dosyası atlandı. Kurmak için:  winget install JRSoftware.InnoSetup"
    } else {
        & $Iscc /Q packaging\installer.iss
        if ($LASTEXITCODE -ne 0) { throw "ISCC başarısız" }
    }
}

Step "Bitti"
Get-ChildItem $Out | Format-Table Name, @{n = "MB"; e = { [math]::Round($_.Length / 1MB, 1) } }
