"""
CLI entry point: ``python -m takeoutreader``

Handles the full pipeline: detect sources -> parse -> generate HTML -> validate.
The GUI (gui/app.py) calls the same core functions but wraps them in a
CustomTkinter interface.
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import webbrowser
import logging

from takeoutreader.core.detection import find_mbox_auto, resolve_inputs, parse_args
from takeoutreader.core.parser import parse_multi_sources
from takeoutreader.core.renderer import generate_output
from takeoutreader.core.validator import validate_output

log = logging.getLogger(__name__)


def main() -> None:
    """Run the full conversion pipeline."""
    test_limit, auto_open = parse_args()
    temp_dirs: list[str] = []

    print()
    print("=" * 60)
    print("  TakeoutReader")
    print("  .mbox / .eml folder -> standalone offline HTML archive")
    print("  Multi-source + merge + deduplication")
    print("  Zero dependencies, zero server, works offline forever")
    print("=" * 60)

    # [0] Input detection
    raw_paths = find_mbox_auto()
    if not raw_paths:
        print("\n  [!] No file selected. Aborting.")
        return

    source_paths, temp_dirs = resolve_inputs(raw_paths)
    if not source_paths:
        print("\n  [!] No valid sources found. Aborting.")
        return

    # Output folder lives next to the first input file
    first_path = raw_paths[0]
    source_dir = (
        os.path.dirname(os.path.abspath(first_path))
        if os.path.isfile(first_path)
        else os.path.abspath(first_path)
    )
    if os.path.isdir(first_path):
        source_dir = os.path.dirname(source_dir)
    output_dir = os.path.join(source_dir, "Gmail_Archive")

    try:
        t_start = time.time()

        # [1/2] Parse all sources
        mails = parse_multi_sources(source_paths, test_limit=test_limit)

        if not mails:
            print("\n  [!] No mails parsed. Aborting.")
            return

        # [2/2] Generate output
        print()
        print("  [OUTPUT] Generating archive...", flush=True)
        t0 = time.time()
        total_size, index_path = generate_output(mails, output_dir)
        print(f"  [OUTPUT] Total: {total_size:.1f} MB ({time.time()-t0:.1f}s)")

        # Create INDEX_GMAIL.html redirect at the source root
        folder_name = os.path.basename(output_dir)
        actual_index = os.path.join(output_dir, "index.html")
        if os.path.isfile(actual_index):
            redirect_path = os.path.join(source_dir, "INDEX_GMAIL.html")
            redirect_html = (
                '<!DOCTYPE html><html><head><meta charset="UTF-8">'
                f'<meta http-equiv="refresh" content="0;url={folder_name}/index.html">'
                '<title>Gmail Archive</title></head><body>'
                f'<p>Redirecting... <a href="{folder_name}/index.html">Click here</a></p>'
                '</body></html>'
            )
            with open(redirect_path, "w", encoding="utf-8") as f:
                f.write(redirect_html)
            print(f"  [REDIRECT] {os.path.basename(redirect_path)} -> {folder_name}/index.html")
        else:
            print(f"  [!] index.html not found in {output_dir} -- redirect not created")
            redirect_path = ""

        # Validation
        v_pass, v_fail, v_warn = validate_output(output_dir, len(mails))

        total_body = sum(len(m.get("b", "")) for m in mails)
        elapsed = time.time() - t_start

        print()
        print("=" * 60)
        print("  FINAL SUMMARY")
        print("=" * 60)
        if len(source_paths) > 1:
            src_types = []
            dirs = sum(1 for p in source_paths if os.path.isdir(p))
            files = len(source_paths) - dirs
            if files:
                src_types.append(f"{files} .mbox")
            if dirs:
                src_types.append(f"{dirs} .eml folder(s)")
            print(f"  Sources     : {' + '.join(src_types)} merged")
        print(f"  Mails       : {len(mails):,}")
        print(f"  Labels      : {len(set(lb for m in mails for lb in m['labels']))}")
        print(f"  Attachments : {sum(1 for m in mails if m['p'] > 0):,}")
        print(f"  Body total  : {total_body / (1024*1024):.1f} MB")
        print(f"  Output      : {output_dir}")
        if redirect_path:
            print(f"  Shortcut    : {redirect_path}")
        print(f"  Size        : {total_size:.1f} MB")
        print(f"  Duration    : {elapsed:.0f}s ({elapsed / 60:.1f} min)")
        print()
        print(f"  -> Double-click INDEX_GMAIL.html to open")
        print(f"  -> Zero server, works offline forever")
        print("=" * 60)

        if auto_open:
            open_path = redirect_path if redirect_path else index_path
            print()
            print(f"  Opening in browser...", flush=True)
            webbrowser.open(f"file:///{open_path.replace(os.sep, '/')}")

    finally:
        # Clean up temp dirs from ZIP extraction
        for temp_dir in temp_dirs:
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    print(f"  [ZIP] Temp cleaned: {temp_dir}")
                except Exception:
                    print(f"  [!] Could not delete {temp_dir}")


class _TeeWriter:
    """Duplicates writes to both the console and a log file.

    Used to capture the full console output for debugging, without
    losing the real-time display. Not elegant, but it works on Windows
    where redirecting stdout breaks the progress display.
    """

    def __init__(self, original, log_file):
        self.original = original
        self.log_file = log_file

    def write(self, text):
        try:
            self.original.write(text)
        except Exception:
            pass
        try:
            self.log_file.write(text)
            self.log_file.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass
        try:
            self.log_file.flush()
        except Exception:
            pass


if __name__ == "__main__":
    # Tee all console output to a diagnostic log file
    _script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    _log_path = os.path.join(_script_dir, "DIAG_execution.log")

    try:
        _log_f = open(_log_path, "w", encoding="utf-8")
        sys.stdout = _TeeWriter(sys.__stdout__, _log_f)
        sys.stderr = _TeeWriter(sys.__stderr__, _log_f)
    except Exception:
        _log_f = None

    try:
        main()
    except KeyboardInterrupt:
        print("\n  [!] Interrupted")
    except Exception as e:
        import traceback
        print(f"\n  [FATAL ERROR] {e}")
        traceback.print_exc()

    if _log_f:
        try:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            _log_f.close()
            print(f"\n  [LOG] Full output saved to: {_log_path}")
        except Exception:
            pass

    print()
    input("  Press Enter to close...")
