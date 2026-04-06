# CONTRIBUTING — TakeoutReader Build Guide

## Architecture

```
TakeoutReader/
  takeoutreader_gui.py          <- GUI tkinter v2 (entry point)
  takeoutreader_core.py         <- V16 engine (ex SCRIPT_Mbox-to-HTML, rebrand TakeoutReader)
  takeoutreader_build.ps1       <- Build script (PyInstaller + Nuitka)
  TakeoutReader_Installer.iss   <- Inno Setup installer script
  LICENSE.txt               <- MIT license + privacy notice
  README.md                 <- User-facing GitHub README
  CONTRIBUTING.md           <- This file
  takeoutreader.ico             <- Icon (optional, 256x256)
```

## Prerequisites (build machine only)

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | python.org (check "Add to PATH") |
| PyInstaller | latest | auto-installed by build script |
| **or** Nuitka | latest | auto-installed by build script |
| Inno Setup | 6.x | https://jrsoftware.org/isdl.php (free) |

For Nuitka builds, you also need a C compiler:
- **Visual Studio Build Tools** (free): https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Select "Desktop development with C++" workload

**End users don't need any of this.** Everything is bundled in the installer.

## Step 1 — Prepare files

1. Create a folder `TakeoutReader/`
2. Copy all files from this repo
3. All files are ready — `takeoutreader_core.py` is already V16 (rebrand from SCRIPT_Mbox-to-HTML)

## Step 2 — Build the .exe

### Option A: Nuitka (recommended)

```powershell
cd C:\path\to\TakeoutReader
powershell -ExecutionPolicy Bypass -File takeoutreader_build.ps1 -Nuitka
```

**Why Nuitka:**
- Compiles Python to native C -> 3-5s startup (vs 10-50s with PyInstaller --onefile)
- Fewer antivirus false positives (no interpreter extraction at runtime)
- Non-decompilable binary (IP protection)
- Build time: 5-15 minutes (one-time cost)

Output: `dist\TakeoutReader\` folder with `TakeoutReader.exe` + dependencies.

### Option B: PyInstaller (faster build)

```powershell
cd C:\path\to\TakeoutReader
powershell -ExecutionPolicy Bypass -File takeoutreader_build.ps1
```

**Why PyInstaller:**
- Simple, no C compiler needed
- Build time: 1-2 minutes
- Uses --onedir mode (NOT --onefile) for fast startup

Output: `dist\TakeoutReader\` folder with `TakeoutReader.exe` + dependencies.

### Test the build

Before creating the installer:
1. Double-click `dist\TakeoutReader\TakeoutReader.exe`
2. Select a .mbox file or .eml folder
3. Run the conversion
4. Verify the HTML archive opens correctly

## Step 3 — Create the installer (Inno Setup)

1. Install Inno Setup from https://jrsoftware.org/isdl.php
2. Open `TakeoutReader_Installer.iss` in Inno Setup Compiler
3. Build > Compile (Ctrl+F9)
4. Output: `installer_output\TakeoutReader_Setup_1.0.0.exe`

The installer packages the entire `dist\TakeoutReader\` folder and provides:
- Language selection (French / English)
- License agreement screen (MIT + privacy)
- Install folder selection (no admin rights needed)
- Desktop + Start Menu shortcuts
- Clean uninstaller in Add/Remove Programs
- "Launch TakeoutReader" option after install

## Step 4 — Distribute

Upload `TakeoutReader_Setup_1.0.0.exe` to GitHub Releases:

```bash
git tag v1.0.0
git push origin v1.0.0
# Then upload the installer .exe to the GitHub Release
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Nuitka: "no C compiler" | MSVC not installed | Install Visual Studio Build Tools |
| PyInstaller: slow startup | Using --onefile | This script uses --onedir (fast) |
| Antivirus blocks .exe | False positive | Use Nuitka build, or add exception |
| ModuleNotFoundError | takeoutreader_core.py missing | Must be next to takeoutreader_gui.py |
| .exe starts, blank window | Import error | Run from CMD to see errors |
| Inno Setup: file not found | Build not done | Run build script first |

## Icon (optional)

1. Create a 256x256 PNG image
2. Convert to .ico (https://convertio.co/png-ico/)
3. Name it `takeoutreader.ico`, place in the TakeoutReader/ folder
4. Rebuild — the script auto-detects it

## Code signing (optional, ~$70/year)

A code signing certificate eliminates SmartScreen warnings entirely.
Cheapest option: Certum Open Source Code Signing certificate.
Apply at: https://shop.certum.eu/open-source-code-signing-certificate.html
