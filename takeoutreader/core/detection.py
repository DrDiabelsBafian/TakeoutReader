"""
Auto-detection of input sources (.mbox, .eml folders, .zip archives).

The detection logic is intentionally forgiving: drop your Takeout export
next to the executable and it figures out what to do. Priority order:
CLI args > .mbox files > .eml folders > .zip archives > file picker dialog.
"""

from __future__ import annotations

import os
import sys
import time
import logging
import zipfile
import tempfile

log = logging.getLogger(__name__)


def find_mbox_auto() -> list[str]:
    """Auto-detect mail sources in the script directory.

    Scans for .mbox files, .eml folders, and .zip archives near the
    executable. Falls back to a tkinter file picker if nothing is found.

    Returns:
        List of file/folder paths to process, or empty list if cancelled.
    """
    # Diagnostic log written next to the executable — helps debug
    # "it found nothing" reports from users on weird Windows setups.
    diag_lines: list[str] = []

    def diag(msg: str) -> None:
        diag_lines.append(msg)
        print(msg)

    def flush_diag() -> None:
        try:
            diag_path = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                "DIAG_detection.log"
            )
        except Exception:
            diag_path = os.path.join(os.getcwd(), "DIAG_detection.log")
        try:
            with open(diag_path, "w", encoding="utf-8") as f:
                f.write("\n".join(diag_lines))
            print(f"  [LOG] Detection diagnostics: {diag_path}")
        except Exception as e:
            log.warning("Could not write detection log: %s", e)

    diag(f"  === DETECTION DIAGNOSTICS ===")
    diag(f"  Python        : {sys.version}")
    diag(f"  sys.argv[0]   : {sys.argv[0]}")
    diag(f"  sys.argv      : {sys.argv}")
    diag(f"  os.getcwd()   : {os.getcwd()}")

    try:
        script_abs = os.path.abspath(sys.argv[0])
        diag(f"  Script abs    : {script_abs}")
    except Exception as e:
        diag(f"  Script abs    : ERROR {e}")

    # 1) CLI arguments? (files AND folders accepted)
    cli_paths = [
        arg for arg in sys.argv[1:]
        if not arg.startswith("--") and (os.path.isfile(arg) or os.path.isdir(arg))
    ]
    if cli_paths:
        diag(f"  CLI args found: {cli_paths}")
        flush_diag()
        return cli_paths
    diag("  CLI args: no valid file/folder")

    # 2) Scan the directory where the script/exe lives
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    diag(f"  Scanning: {script_dir}")
    diag(f"  Exists:   {os.path.isdir(script_dir)}")

    mbox_files: list[str] = []
    zip_files: list[str] = []
    eml_dirs: list[str] = []

    try:
        entries = os.listdir(script_dir)
        diag(f"  Contents ({len(entries)} entries):")
        for fn in entries:
            fp = os.path.join(script_dir, fn)
            is_file = os.path.isfile(fp)
            is_dir = os.path.isdir(fp)
            ext = os.path.splitext(fn)[1].lower() if is_file else ""
            size = os.path.getsize(fp) if is_file else 0
            diag(f"    {'F' if is_file else 'D'} {fn:50s} {ext:8s} {size:>12,}")

            if is_file:
                if ext == ".mbox":
                    mbox_files.append(fp)
                elif ext == ".zip":
                    zip_files.append(fp)
            elif is_dir:
                # Walk up to 3 levels deep looking for .eml files
                has_eml = False
                eml_sample = ""
                try:
                    for dp, dirs, fnames in os.walk(fp):
                        depth = dp.replace(fp, "").count(os.sep)
                        if depth > 2:
                            dirs.clear()
                            continue
                        for fname in fnames:
                            if fname.lower().endswith(".eml"):
                                has_eml = True
                                eml_sample = os.path.relpath(os.path.join(dp, fname), fp)
                                break
                        if has_eml:
                            break
                except PermissionError as e:
                    diag(f"      [!] PermissionError: {e}")
                except Exception as e:
                    diag(f"      [!] Scan error: {e}")

                if has_eml:
                    eml_dirs.append(fp)
                    diag(f"      -> EML detected (e.g. {eml_sample})")
                else:
                    diag(f"      -> No .eml found (3 levels)")
    except Exception as e:
        diag(f"  [ERROR] listdir failed: {e}")

    diag(f"  Results: {len(mbox_files)} .mbox, {len(eml_dirs)} EML dirs, {len(zip_files)} .zip")

    # Pick the best source type available
    if mbox_files:
        mbox_files.sort(key=os.path.getsize, reverse=True)
        for f in mbox_files:
            size_gb = os.path.getsize(f) / (1024**3)
            diag(f"  Selected: {os.path.basename(f)} ({size_gb:.2f} GB)")
        flush_diag()
        return mbox_files

    if eml_dirs:
        for d in eml_dirs:
            eml_count = sum(1 for _, _, fns in os.walk(d) for fn in fns if fn.lower().endswith(".eml"))
            diag(f"  Selected EML dir: {os.path.basename(d)}/ ({eml_count:,} .eml)")
        flush_diag()
        return eml_dirs

    if zip_files:
        zip_files.sort(key=os.path.getsize, reverse=True)
        for f in zip_files:
            size_gb = os.path.getsize(f) / (1024**3)
            diag(f"  Selected ZIP: {os.path.basename(f)} ({size_gb:.2f} GB)")
        flush_diag()
        return zip_files

    # 3) Nothing found — open a file picker as last resort
    diag("  NOTHING FOUND -> opening file picker")
    flush_diag()

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        paths = filedialog.askopenfilenames(
            title="Select your .mbox or .zip Takeout export",
            filetypes=[
                ("Mail files", "*.mbox"),
                ("ZIP archives", "*.zip"),
                ("All files", "*.*"),
            ]
        )
        root.destroy()
        if paths:
            return list(paths)
    except Exception:
        pass

    return []


def find_mbox_in_zip(zip_path: str) -> tuple[list[str], str | None]:
    """Extract .mbox files from a Takeout .zip archive.

    Args:
        zip_path: Path to the .zip file.

    Returns:
        Tuple of (list of extracted .mbox paths, temp directory to clean up).
        Returns ([], None) if the zip contains no .mbox files.
    """
    if not zipfile.is_zipfile(zip_path):
        print(f"  [!] {zip_path} is not a valid ZIP file.")
        return [], None

    print("  [ZIP] Scanning archive contents...", flush=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        mbox_entries = [n for n in zf.namelist() if n.lower().endswith('.mbox')]
        if not mbox_entries:
            print("  [!] No .mbox files found inside the ZIP.")
            return [], None

        mbox_entries.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)

        # FIXME: prefix should be "takeoutreader_" but changing it would break
        # any user scripts that grep for the old name in temp dirs
        temp_dir = tempfile.mkdtemp(prefix="mbox2html_")
        extracted = []
        for mf in mbox_entries:
            size_gb = zf.getinfo(mf).file_size / (1024**3)
            print(f"  [ZIP] Found: {mf} ({size_gb:.2f} GB)")
            t0 = time.time()
            zf.extract(mf, temp_dir)
            print(f"  [ZIP] Extracted ({time.time()-t0:.0f}s)")
            extracted.append(os.path.join(temp_dir, mf))

        print(f"  [ZIP] {len(extracted)} .mbox file(s) extracted")
        return extracted, temp_dir


def resolve_inputs(paths: list[str]) -> tuple[list[str], list[str]]:
    """Resolve a list of paths into ready-to-parse sources.

    Handles .mbox files (pass through), .zip files (extract), and
    .eml directories (pass through). Everything else is skipped with a warning.

    Returns:
        Tuple of (source_paths, temp_dirs_to_cleanup).
    """
    source_paths: list[str] = []
    temp_dirs: list[str] = []

    for path in paths:
        if os.path.isdir(path):
            source_paths.append(path)
            continue

        ext = os.path.splitext(path)[1].lower()

        if ext == ".zip":
            extracted, temp_dir = find_mbox_in_zip(path)
            source_paths.extend(extracted)
            if temp_dir:
                temp_dirs.append(temp_dir)
        elif ext == ".mbox" or os.path.isfile(path):
            source_paths.append(path)
        else:
            print(f"  [!] Unrecognized file type: {ext}")

    return source_paths, temp_dirs


def parse_args() -> tuple[int, bool]:
    """Parse CLI arguments (hand-rolled, no argparse — zero dependencies).

    Supported flags:
        --test N    Process only the first N emails (for development)
        --no-open   Don't auto-open the result in a browser

    Returns:
        Tuple of (test_limit, auto_open).
    """
    test_limit = 0
    auto_open = True

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--test" and i + 1 < len(args):
            try:
                test_limit = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "--no-open":
            auto_open = False
            i += 1
        else:
            i += 1

    return test_limit, auto_open
