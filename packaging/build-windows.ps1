# Builds the Windows app and its Setup wizard:
#   dist\Pixel Slides\Pixel Slides.exe            (the app, one folder)
#   dist\installer\PixelSlides-Setup-<ver>.exe    (the install wizard)
#
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1
# Needs Python 3.11+ and Inno Setup 6 (winget install JRSoftware.InnoSetup).
# Uses "python -m pip" throughout, never pip.exe, so Smart App Control is happy.
param([string]$Version = "0.4.0")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv-build")) { python -m venv .venv-build }
$py = ".venv-build\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements-desktop.txt pyinstaller pillow
if ($LASTEXITCODE) { throw "pip install failed" }

& $py packaging\make_icons.py
& $py -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\pixel-slides.spec
if ($LASTEXITCODE) { throw "PyInstaller failed" }

$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
foreach ($candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                         "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
    if (-not $iscc -and (Test-Path $candidate)) { $iscc = $candidate }
}
if (-not $iscc) {
    Write-Warning "Inno Setup not found. The app is built in dist\Pixel Slides. For the wizard: winget install JRSoftware.InnoSetup, then run this again."
    exit 0
}
& $iscc "/DAppVersion=$Version" packaging\pixel-slides.iss
if ($LASTEXITCODE) { throw "Inno Setup failed" }
Write-Host "Done: dist\installer\PixelSlides-Setup-$Version.exe"
