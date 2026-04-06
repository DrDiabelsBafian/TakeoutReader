# ============================================
# takeoutreader/core/detection.py
# Auto-detection des sources (.mbox, .eml, .zip)
# + extraction ZIP + parsing arguments CLI
# ============================================

import os
import sys
import time
import zipfile
import tempfile


def find_mbox_auto():
    """Auto-detecte les .mbox / dossiers .eml dans le dossier du script.
    Priorite : arguments CLI > .mbox > dossier .eml > .zip > file picker.
    Retourne une LISTE de chemins (fichiers .mbox/.zip ou dossiers contenant .eml)."""

    # LOG -- ecrit un fichier de diagnostic a cote du script
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        print(msg)

    def flush_log():
        try:
            log_path = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                "DIAG_detection.log"
            )
        except Exception:
            log_path = os.path.join(os.getcwd(), "DIAG_detection.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines))
            print(f"  [LOG] Diagnostic ecrit dans : {log_path}")
        except Exception as e:
            print(f"  [LOG] Impossible d'ecrire le log : {e}")

    log(f"  === DIAGNOSTIC AUTO-DETECTION ===")
    log(f"  Python        : {sys.version}")
    log(f"  sys.argv[0]   : {sys.argv[0]}")
    log(f"  sys.argv      : {sys.argv}")
    log(f"  os.getcwd()   : {os.getcwd()}")

    try:
        script_abs = os.path.abspath(sys.argv[0])
        log(f"  Script abs    : {script_abs}")
    except Exception as e:
        log(f"  Script abs    : ERREUR {e}")

    # 1) Arguments CLI ? (fichiers ET dossiers acceptes)
    cli_paths = [arg for arg in sys.argv[1:]
                 if not arg.startswith("--") and (os.path.isfile(arg) or os.path.isdir(arg))]
    if cli_paths:
        log(f"  CLI args trouves : {cli_paths}")
        flush_log()
        return cli_paths
    log(f"  CLI args : aucun fichier/dossier valide")

    # 2) Scanner le dossier du script
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    log(f"  Scan du dossier : {script_dir}")
    log(f"  Dossier existe  : {os.path.isdir(script_dir)}")

    mbox_files = []
    zip_files = []
    eml_dirs = []

    try:
        entries = os.listdir(script_dir)
        log(f"  Contenu ({len(entries)} entrees) :")
        for fn in entries:
            fp = os.path.join(script_dir, fn)
            is_file = os.path.isfile(fp)
            is_dir = os.path.isdir(fp)
            ext = os.path.splitext(fn)[1].lower() if is_file else ""
            size = os.path.getsize(fp) if is_file else 0
            log(f"    {'F' if is_file else 'D'} {fn:50s} {ext:8s} {size:>12,}")

            if is_file:
                if ext == ".mbox":
                    mbox_files.append(fp)
                elif ext == ".zip":
                    zip_files.append(fp)
            elif is_dir:
                # Verifie si le dossier contient des .eml (os.walk, max 3 niveaux)
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
                    log(f"      [!] PermissionError: {e}")
                except Exception as e:
                    log(f"      [!] Erreur scan: {e}")

                if has_eml:
                    eml_dirs.append(fp)
                    log(f"      -> EML detecte (ex: {eml_sample})")
                else:
                    log(f"      -> Pas de .eml (3 niveaux)")
    except Exception as e:
        log(f"  [ERREUR] Listdir echoue : {e}")

    log(f"  Resultats : {len(mbox_files)} .mbox, {len(eml_dirs)} dossiers EML, {len(zip_files)} .zip")

    # .mbox trouves -> TOUS
    if mbox_files:
        mbox_files.sort(key=os.path.getsize, reverse=True)
        for f in mbox_files:
            size_go = os.path.getsize(f) / (1024**3)
            log(f"  Selectionne : {os.path.basename(f)} ({size_go:.2f} Go)")
        flush_log()
        return mbox_files

    # Dossiers .eml -> TOUS
    if eml_dirs:
        for d in eml_dirs:
            eml_count = sum(1 for _, _, fns in os.walk(d) for fn in fns if fn.lower().endswith(".eml"))
            log(f"  Selectionne dossier EML : {os.path.basename(d)}/ ({eml_count:,} .eml)")
        flush_log()
        return eml_dirs

    # .zip -> TOUS
    if zip_files:
        zip_files.sort(key=os.path.getsize, reverse=True)
        for f in zip_files:
            size_go = os.path.getsize(f) / (1024**3)
            log(f"  Selectionne ZIP : {os.path.basename(f)} ({size_go:.2f} Go)")
        flush_log()
        return zip_files

    # 3) Rien trouve -> file picker
    log("  RIEN TROUVE -> ouverture file picker")
    flush_log()

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        paths = filedialog.askopenfilenames(
            title="Choisis tes fichiers .mbox ou .zip Takeout",
            filetypes=[
                ("Fichiers mail", "*.mbox"),
                ("Archives ZIP", "*.zip"),
                ("Tous", "*.*"),
            ]
        )
        root.destroy()
        if paths:
            return list(paths)
    except Exception:
        pass

    return []


def find_mbox_in_zip(zip_path):
    """Cherche les .mbox dans un .zip Takeout, les extrait dans un dossier temp.
    Retourne (liste_mbox_paths, temp_dir) ou ([], None)."""

    if not zipfile.is_zipfile(zip_path):
        print(f"  [!] {zip_path} n'est pas un ZIP valide.")
        return [], None

    print("  [ZIP] Analyse du contenu...", flush=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        mbox_files = [n for n in zf.namelist() if n.lower().endswith('.mbox')]
        if not mbox_files:
            print("  [!] Aucun .mbox trouve dans le ZIP.")
            return [], None

        # Trier par taille decroissante
        mbox_files.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)

        temp_dir = tempfile.mkdtemp(prefix="mbox2html_")
        extracted = []
        for mf in mbox_files:
            size_go = zf.getinfo(mf).file_size / (1024**3)
            print(f"  [ZIP] Trouve : {mf} ({size_go:.2f} Go)")
            t0 = time.time()
            zf.extract(mf, temp_dir)
            print(f"  [ZIP] Extrait ({time.time()-t0:.0f}s)")
            extracted.append(os.path.join(temp_dir, mf))

        print(f"  [ZIP] {len(extracted)} .mbox extraits au total")
        return extracted, temp_dir


def resolve_inputs(paths):
    """Resout une liste de chemins (.mbox/.zip/dossier .eml) en sources pretes.
    Retourne (source_paths, temp_dirs_to_cleanup).
    source_paths peut contenir des fichiers .mbox ET des dossiers .eml."""

    source_paths = []
    temp_dirs = []

    for path in paths:
        if os.path.isdir(path):
            # Dossier .eml -> passer directement
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
            print(f"  [!] Type de fichier non reconnu : {ext}")

    return source_paths, temp_dirs


def parse_args():
    """Parse les arguments CLI simples (pas argparse, zero dep)"""
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
