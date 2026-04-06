# ============================================
# takeoutreader/__main__.py
# Point d'entree CLI : python -m takeoutreader
# ============================================

import os
import sys
import time
import shutil
import webbrowser

from takeoutreader.core.detection import find_mbox_auto, resolve_inputs, parse_args
from takeoutreader.core.parser import parse_multi_sources
from takeoutreader.core.renderer import generate_output
from takeoutreader.core.validator import validate_output


def main():
    test_limit, auto_open = parse_args()
    temp_dirs = []

    print()
    print("=" * 60)
    print("  TakeoutReader")
    print("  .mbox / dossier .eml -> HTML interactif standalone")
    print("  Multi-source + fusion + deduplication")
    print("  Zero dependance, zero serveur, offline a vie")
    print("=" * 60)

    # [0] Input -- auto-detection (retourne liste)
    raw_paths = find_mbox_auto()
    if not raw_paths:
        print("\n  [!] Aucun fichier selectionne. Abandon.")
        return

    # Resolve all inputs (.zip -> extract, .mbox/.eml dir -> direct)
    source_paths, temp_dirs = resolve_inputs(raw_paths)
    if not source_paths:
        print("\n  [!] Aucune source trouvee. Abandon.")
        return

    # Output : dossier dans le meme repertoire que le premier fichier/dossier source
    first_path = raw_paths[0]
    source_dir = os.path.dirname(os.path.abspath(first_path)) if os.path.isfile(first_path) else os.path.abspath(first_path)
    if os.path.isdir(first_path):
        source_dir = os.path.dirname(source_dir)  # Parent du dossier .eml
    output_dir = os.path.join(source_dir, "Gmail_Archive")

    try:
        t_start = time.time()

        # [1/2] Parse (multi-source avec dedup cross-fichiers)
        mails = parse_multi_sources(source_paths, test_limit=test_limit)

        if not mails:
            print("\n  [!] Aucun mail parse. Abandon.")
            return

        # [2/2] Generate output folder
        print()
        print("  [OUTPUT] Generation du dossier...", flush=True)
        t0 = time.time()
        total_size, index_path = generate_output(mails, output_dir)
        print(f"  [OUTPUT] Total: {total_size:.1f} Mo ({time.time()-t0:.1f}s)")

        # Creer INDEX_GMAIL.html a la racine (redirect vers le dossier)
        folder_name = os.path.basename(output_dir)
        actual_index = os.path.join(output_dir, "index.html")
        if os.path.isfile(actual_index):
            redirect_path = os.path.join(source_dir, "INDEX_GMAIL.html")
            redirect_html = ('<!DOCTYPE html><html><head><meta charset="UTF-8">'
                             f'<meta http-equiv="refresh" content="0;url={folder_name}/index.html">'
                             '<title>Gmail Archive</title></head><body>'
                             f'<p>Redirection... <a href="{folder_name}/index.html">Cliquer ici</a></p>'
                             '</body></html>')
            with open(redirect_path, "w", encoding="utf-8") as f:
                f.write(redirect_html)
            print(f"  [REDIRECT] {os.path.basename(redirect_path)} -> {folder_name}/index.html")
        else:
            print(f"  [!] index.html introuvable dans {output_dir} -- redirect non cree")
            redirect_path = ""

        # Validation Rebouclage
        v_pass, v_fail, v_warn = validate_output(output_dir, len(mails))

        total_body = sum(len(m.get("b", "")) for m in mails)
        elapsed = time.time() - t_start

        print()
        print("=" * 60)
        print("  BILAN FINAL")
        print("=" * 60)
        if len(source_paths) > 1:
            src_types = []
            dirs = sum(1 for p in source_paths if os.path.isdir(p))
            files = len(source_paths) - dirs
            if files:
                src_types.append(f"{files} .mbox")
            if dirs:
                src_types.append(f"{dirs} dossier(s) .eml")
            print(f"  Sources     : {' + '.join(src_types)} fusionnes")
        print(f"  Mails       : {len(mails):,}")
        print(f"  Labels      : {len(set(lb for m in mails for lb in m['labels']))}")
        print(f"  Avec PJ     : {sum(1 for m in mails if m['p'] > 0):,}")
        print(f"  Body total  : {total_body / (1024*1024):.1f} Mo")
        print(f"  Dossier     : {output_dir}")
        if redirect_path:
            print(f"  Raccourci   : {redirect_path}")
        print(f"  Taille      : {total_size:.1f} Mo")
        print(f"  Duree total : {elapsed:.0f}s ({elapsed / 60:.1f} min)")
        print()
        print(f"  -> Double-clic INDEX_GMAIL.html pour ouvrir")
        print(f"  -> Zero serveur, fonctionne offline a vie")
        print("=" * 60)

        # Ouverture auto
        if auto_open:
            open_path = redirect_path if redirect_path else index_path
            print()
            print(f"  Ouverture dans le navigateur...", flush=True)
            webbrowser.open(f"file:///{open_path.replace(os.sep, '/')}")

    finally:
        # Cleanup temp dirs (extraction ZIP)
        for temp_dir in temp_dirs:
            if temp_dir and os.path.isdir(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    print(f"  [ZIP] Temp nettoye : {temp_dir}")
                except Exception:
                    print(f"  [!] Impossible de supprimer {temp_dir}")


# ============================================
# ENTRY POINT
# ============================================

class _TeeWriter:
    """Ecrit dans la console ET dans un fichier"""
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
    # Log TOUTE la sortie console dans un fichier a cote du script
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
        print("\n  [!] Interrompu")
    except Exception as e:
        import traceback
        print(f"\n  [ERREUR FATALE] {e}")
        traceback.print_exc()

    if _log_f:
        try:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            _log_f.close()
            print(f"\n  [LOG] Execution complete loguee dans : {_log_path}")
        except Exception:
            pass

    print()
    input("  Entree pour fermer...")
