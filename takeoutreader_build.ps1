"""
takeoutreader_build.ps1 v3 — Build script for TakeoutReader v2.0.0
Nuitka only (PyInstaller dropped — no bootloader for Python 3.14)

Usage:
  powershell -ExecutionPolicy Bypass -File takeoutreader_build.ps1
"""

param(
    [switch]$Help
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

if ($Help) {
    Write-Host @"

  TakeoutReader Build Script v3
  =============================
  Builds TakeoutReader using Nuitka (compiled to C).
  Requires: Python 3.10+, MSVC Build Tools, Nuitka

  Usage:
    powershell -ExecutionPolicy Bypass -File takeoutreader_build.ps1
    powershell -ExecutionPolicy Bypass -File takeoutreader_build.ps1 -Help

"@
    exit 0
}

Write-Host ""
Write-Host ("=" * 60)
Write-Host "  TakeoutReader v2.0.0 - Nuitka Build"
Write-Host ("=" * 60)
Write-Host ""

# --- 1. Check Python ---
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            $pyMinor = [int]$Matches[1]
            if ($pyMinor -ge 10) {
                $pythonCmd = $cmd
                Write-Host "  [OK] $ver ($cmd)"
                break
            }
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Host "  [ERROR] Python 3.10+ not found."
    Write-Host "  Install Python from python.org (check 'Add to PATH')"
    Read-Host "  Press Enter to close"
    exit 1
}

# --- 2. Check source files ---
$guiFile = Join-Path $PSScriptRoot "takeoutreader_gui.py"
$pkgDir = Join-Path $PSScriptRoot "takeoutreader"
$iconFile = Join-Path $PSScriptRoot "takeoutreader.ico"
$logoFile = Join-Path $PSScriptRoot "takeoutreader_logo.png"

if (-not (Test-Path $guiFile)) {
    Write-Host "  [ERROR] takeoutreader_gui.py not found"
    Read-Host "  Press Enter to close"
    exit 1
}
if (-not (Test-Path $pkgDir)) {
    Write-Host "  [ERROR] takeoutreader/ package not found"
    Read-Host "  Press Enter to close"
    exit 1
}
Write-Host "  [OK] Source files found"

$hasIcon = Test-Path $iconFile
if ($hasIcon) { Write-Host "  [OK] Icon: takeoutreader.ico" }
$hasLogo = Test-Path $logoFile
if ($hasLogo) { Write-Host "  [OK] Logo: takeoutreader_logo.png" }

# --- 3. Install/check Nuitka ---
Write-Host ""
Write-Host "  Checking Nuitka..."
& $pythonCmd -m pip install nuitka --quiet 2>&1 | Out-Host

$nuitkaVer = & $pythonCmd -m nuitka --version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Nuitka $nuitkaVer"
} else {
    Write-Host "  [ERROR] Nuitka not installed correctly"
    Read-Host "  Press Enter to close"
    exit 1
}

if ($pyMinor -ge 14) {
    Write-Host ""
    Write-Host "  [NOTE] Python 3.$pyMinor detected."
    Write-Host "  If the build fails, try Python 3.12 or 3.13."
    Write-Host ""
}

Write-Host "  [INFO] Nuitka requires a C compiler (MSVC Build Tools)."
Write-Host "  -> https://visualstudio.microsoft.com/visual-cpp-build-tools/"
Write-Host ""
Write-Host "  Building... (5-15 minutes, be patient)"
Write-Host ""

# --- 4. Nuitka build ---
$nuitkaArgs = @(
    "-m", "nuitka"
    "--standalone"
    "--enable-plugin=tk-inter"
    "--include-package=takeoutreader"
    "--include-package=customtkinter"
    "--output-dir=build_nuitka"
    "--remove-output"
    "--assume-yes-for-downloads"
    "--company-name=TakeoutReader"
    "--product-name=TakeoutReader"
    "--product-version=2.0.0"
    "--file-description=TakeoutReader - Gmail Takeout to offline HTML archive"
    "--windows-console-mode=disable"
)

if ($hasIcon) {
    $nuitkaArgs += "--windows-icon-from-ico=`"$iconFile`""
}

$nuitkaArgs += "`"$guiFile`""

& $pythonCmd @nuitkaArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [ERROR] Nuitka build failed."
    Write-Host "  Check that MSVC Build Tools are installed."
    Read-Host "  Press Enter to close"
    exit 1
}

# --- 5. Assemble dist folder ---
$nuitkaDist = Join-Path $PSScriptRoot "build_nuitka\takeoutreader_gui.dist"
$distDir = Join-Path $PSScriptRoot "dist\TakeoutReader"

if (Test-Path $distDir) {
    Remove-Item $distDir -Recurse -Force
}
New-Item -Path (Join-Path $PSScriptRoot "dist") -ItemType Directory -Force | Out-Null
Move-Item $nuitkaDist $distDir -Force

# Rename binary
$binName = if (Test-Path "$distDir\takeoutreader_gui.exe") { "takeoutreader_gui.exe" } else { "takeoutreader_gui.bin" }
if (Test-Path "$distDir\$binName") {
    Rename-Item "$distDir\$binName" "TakeoutReader.exe" -Force
}

# Copy logo (file-based loader needs it next to the exe)
if ($hasLogo) {
    Copy-Item $logoFile $distDir -Force
    Write-Host "  [OK] Logo copied to dist"
}

# Copy icon
if ($hasIcon) {
    Copy-Item $iconFile $distDir -Force
}

$exePath = Join-Path $distDir "TakeoutReader.exe"

# --- 6. Summary ---
if (Test-Path $exePath) {
    $totalSize = [math]::Round((Get-ChildItem $distDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    $exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
    $fileCount = (Get-ChildItem $distDir -Recurse -File).Count

    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "  BUILD OK"
    Write-Host ("=" * 60)
    Write-Host "  Executable  : $exePath"
    Write-Host "  Binary      : $exeSize MB"
    Write-Host "  Folder      : $totalSize MB ($fileCount files)"
    Write-Host ""
    Write-Host "  Next steps:"
    Write-Host "  1. Test: double-click $exePath"
    Write-Host "  2. Installer: open TakeoutReader_Installer.iss in Inno Setup"
    Write-Host "  3. Compile: Ctrl+F9 in Inno Setup"
    Write-Host ("=" * 60)
} else {
    Write-Host "  [ERROR] TakeoutReader.exe not found after build"
}

Write-Host ""
Read-Host "  Press Enter to close"
