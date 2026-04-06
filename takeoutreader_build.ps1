# ============================================
# takeoutreader_build.ps1 v2
# Build TakeoutReader .exe -- 2 modes :
#   Mode A (defaut)  : PyInstaller --onedir  (rapide, 1-2 min)
#   Mode B (recommande) : Nuitka --standalone  (plus lent, 5-15 min, meilleur resultat)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File takeoutreader_build.ps1
#   powershell -ExecutionPolicy Bypass -File takeoutreader_build.ps1 -Nuitka
# ============================================

param(
    [switch]$Nuitka,
    [switch]$Help
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

if ($Help) {
    Write-Host @"

  TakeoutReader Build Script v2
  ========================
  Sans argument : build avec PyInstaller (rapide, ~1 min)
  -Nuitka       : build avec Nuitka (recommande, ~5-15 min)
                   + Startup plus rapide (3-5s vs 10-50s)
                   + Moins de faux positifs antivirus
                   + Code compile en C (non decompilable)
  -Help         : ce message

"@
    exit 0
}

Write-Host ""
Write-Host ("=" * 60)
Write-Host "  TakeoutReader - Build $(if ($Nuitka) {'Nuitka (compile C)'} else {'PyInstaller (bundle)'})"
Write-Host ("=" * 60)
Write-Host ""

# -----------------------------------------------
# 1. Verifier Python
# -----------------------------------------------
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
    Write-Host "  [ERREUR] Python 3.10+ introuvable."
    Write-Host "  Installez Python depuis python.org (cocher 'Add to PATH')"
    Read-Host "  Entree pour fermer"
    exit 1
}

# -----------------------------------------------
# 2. Verifier fichiers source
# -----------------------------------------------
$guiFile = Join-Path $PSScriptRoot "takeoutreader_gui.py"
$coreFile = Join-Path $PSScriptRoot "takeoutreader_core.py"
$iconFile = Join-Path $PSScriptRoot "takeoutreader.ico"

foreach ($f in @($guiFile, $coreFile)) {
    if (-not (Test-Path $f)) {
        Write-Host "  [ERREUR] $(Split-Path $f -Leaf) introuvable"
        Read-Host "  Entree pour fermer"
        exit 1
    }
}
Write-Host "  [OK] Fichiers source trouves"

$hasIcon = Test-Path $iconFile
if ($hasIcon) {
    Write-Host "  [OK] Icone : takeoutreader.ico"
} else {
    Write-Host "  [INFO] Pas d'icone (takeoutreader.ico) - build sans icone"
}

# -----------------------------------------------
# 3. Build
# -----------------------------------------------
if ($Nuitka) {
    # ===== MODE NUITKA =====
    Write-Host ""
    Write-Host "  Installation/verification de Nuitka..."
    & $pythonCmd -m pip install nuitka --quiet 2>&1 | Out-Host

    # Verifier que Nuitka fonctionne
    $nuitkaVer = & $pythonCmd -m nuitka --version 2>&1 | Select-Object -First 1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Nuitka $nuitkaVer"
    } else {
        Write-Host "  [ERREUR] Nuitka non installe correctement"
        Read-Host "  Entree pour fermer"
        exit 1
    }

    # Warning Python 3.14
    if ($pyMinor -ge 14) {
        Write-Host ""
        Write-Host "  [ATTENTION] Python 3.$pyMinor detecte."
        Write-Host "  Nuitka peut ne pas encore supporter cette version."
        Write-Host "  Si le build echoue, utilisez PyInstaller (sans -Nuitka)."
        Write-Host "  Ou installez Python 3.12/3.13 pour le build uniquement."
        Write-Host ""
    }

    # Verifier C compiler (Windows = MSVC via Visual Studio Build Tools)
    Write-Host "  [INFO] Nuitka necessite un compilateur C."
    Write-Host "  Si le build echoue, installez :"
    Write-Host "  -> Visual Studio Build Tools (gratuit)"
    Write-Host "  -> https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    Write-Host ""

    Write-Host "  Build Nuitka en cours... (5-15 minutes, soyez patient)"
    Write-Host ""

    $nuitkaArgs = @(
        "-m", "nuitka"
        "--standalone"
        "--enable-plugin=tk-inter"
        "--include-module=takeoutreader_core"
        "--output-dir=build_nuitka"
        "--remove-output"
        "--assume-yes-for-downloads"
        "--company-name=TakeoutReader"
        "--product-name=TakeoutReader"
        "--product-version=1.0.0"
        "--file-description=TakeoutReader - Gmail Archive Viewer"
    )

    if ($hasIcon) {
        $nuitkaArgs += "--windows-icon-from-ico=`"$iconFile`""
    }

    # --windows-console-mode=disable : pas de console en arriere-plan
    $nuitkaArgs += "--windows-console-mode=disable"
    $nuitkaArgs += "`"$guiFile`""

    & $pythonCmd @nuitkaArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  [ERREUR] Build Nuitka echoue."
        Write-Host "  Verifiez qu'un compilateur C est installe (MSVC Build Tools)"
        Read-Host "  Entree pour fermer"
        exit 1
    }

    # Renommer le dossier de sortie pour Inno Setup
    $nuitkaDist = Join-Path $PSScriptRoot "build_nuitka\takeoutreader_gui.dist"
    $distDir = Join-Path $PSScriptRoot "dist\TakeoutReader"

    if (Test-Path $distDir) {
        Remove-Item $distDir -Recurse -Force
    }
    New-Item -Path (Join-Path $PSScriptRoot "dist") -ItemType Directory -Force | Out-Null
    Move-Item $nuitkaDist $distDir -Force

    # Renommer le binaire
    $binName = if (Test-Path "$distDir\takeoutreader_gui.exe") { "takeoutreader_gui.exe" } else { "takeoutreader_gui.bin" }
    if (Test-Path "$distDir\$binName") {
        Rename-Item "$distDir\$binName" "TakeoutReader.exe" -Force
    }

    $exePath = Join-Path $distDir "TakeoutReader.exe"

} else {
    # ===== MODE PYINSTALLER (--onedir) =====
    Write-Host "  Verification de PyInstaller..."
    $hasPyInst = $false
    $pyiCheck = & $pythonCmd -m PyInstaller --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $hasPyInst = $true
        Write-Host "  [OK] PyInstaller installe"
    }

    if (-not $hasPyInst) {
        Write-Host "  Installation de PyInstaller..."
        & $pythonCmd -m pip install pyinstaller --quiet 2>&1 | Out-Host
        Write-Host "  [OK] PyInstaller installe"
    }

    Write-Host ""
    Write-Host "  Build PyInstaller en cours... (1-2 minutes)"
    Write-Host ""

    # --onedir (PAS --onefile) : startup 3-5s au lieu de 10-50s
    $pyiArgs = @(
        "-m", "PyInstaller"
        "--onedir"
        "--windowed"
        "--name", "TakeoutReader"
        "--add-data", "`"$coreFile;.`""
        "--clean"
        "--noconfirm"
    )
    if ($hasIcon) {
        $pyiArgs += "--icon=`"$iconFile`""
    }
    $pyiArgs += "`"$guiFile`""

    & $pythonCmd @pyiArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  [ERREUR] Build PyInstaller echoue."
        Read-Host "  Entree pour fermer"
        exit 1
    }

    $exePath = Join-Path $PSScriptRoot "dist\TakeoutReader\TakeoutReader.exe"
}

# -----------------------------------------------
# 4. Resultat
# -----------------------------------------------
if (Test-Path $exePath) {
    $distFolder = Split-Path $exePath -Parent
    $totalSize = [math]::Round((Get-ChildItem $distFolder -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    $exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
    $fileCount = (Get-ChildItem $distFolder -Recurse -File).Count

    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "  BUILD OK"
    Write-Host ("=" * 60)
    Write-Host "  Methode     : $(if ($Nuitka) {'Nuitka (compile C)'} else {'PyInstaller (bundle)'})"
    Write-Host "  Executable  : $exePath"
    Write-Host "  Binaire     : $exeSize Mo"
    Write-Host "  Dossier     : $totalSize Mo ($fileCount fichiers)"
    Write-Host ""
    Write-Host "  Prochaine etape :"
    Write-Host "  1. Tester : double-clic sur $exePath"
    Write-Host "  2. Installeur : ouvrir TakeoutReader_Installer.iss dans Inno Setup"
    Write-Host "  3. Compiler : Ctrl+F9 dans Inno Setup"
    Write-Host ("=" * 60)
} else {
    Write-Host "  [ERREUR] TakeoutReader.exe introuvable apres build"
}

Write-Host ""
Read-Host "  Entree pour fermer"
