# ============================================
# takeoutreader_core.py (ex SCRIPT_Mbox-to-HTML)
# Pipeline complet : .mbox / .eml folder -> dossier HTML interactif
# Cross-platform : Windows + Mac + Linux
# Python 3.14 - Zero dependance externe
# ============================================
# V16 -- Branding TakeoutReader:
#   + Renommage Mbox-to-HTML -> TakeoutReader partout
#   + Footer HTML, banniere console, titres
#   + Compatible GUI wrapper takeoutreader_gui.py
# V15 -- PJ extractibles + cliquables:
#   + Extrait les PJ sur disque dans Gmail_Archive/pj/
#   + PJ cliquables dans l'interface (ouvre le fichier)
#   + Nommage unique par index mail: pj/00042/fichier.pdf
#   + Supporte eml et mbox comme source de PJ
#   + Barre de progression extraction PJ
# V14 — Support dossier .eml:
#   + Accepte un dossier contenant des .eml (MAILS_EXTRAITS etc.)
#   + Auto-detecte .mbox OU dossier .eml dans le repertoire
#   + parse_eml_folder() — meme dedup/labels/threading que parse_mbox
#   + Compatible multi-source : .mbox + dossier .eml en meme temps
# V13 — Multi-mbox + fusion:
#   + Accepte plusieurs .mbox dans le meme dossier
#   + Deduplication cross-fichiers par Message-ID
#   + Fusion labels si meme mail dans 2 exports
#   + CLI: arguments multiples ou dossier avec N .mbox
#   + ZIP: extrait tous les .mbox du ZIP
#   + Bilan par source (mails/doublons par fichier)
# V12 — Refonte esthétique:
#   + Dark: palette violet (#B388FF accent, tons mauves)
#   + Light: palette rose (#E91E63 accent, tons rosés)
#   + Icones Unicode (recherche, filtres, boutons, header)
#   + Animations: fade-in page, hover lift, smooth transitions
#   + Micro-interactions: focus glow, active pulse
# V11 — UI polish:
#   + Dark: meilleur contraste (t3 #666→#888, t2 #AAA→#B8B8B8)
#   + Dark: backgrounds mieux separes (#0A→#0D, #11→#16)
#   + Light: affiné (ombres, espacement)
#   + Scrollbar custom, transitions, shadows panel
# V10 — Threading Gmail natif:
#   + X-GM-THRID (header Takeout) = tid principal
#   + Fallback References/In-Reply-To si absent
#   + Threads identiques a Gmail
# V9 — Auto-validation (protocole Rebouclage):
#   + validate_output() apres generation
#   + MUST_EXIST / MUST_NOT_EXIST invariants
#   + Check structurel (braces, script tags, JSON)
#   + Rapport PASS/FAIL dans la console
# V8 — Fix catego + filtre Spam/Sent/Trash + perf
# V7 — Selection + Export + Masquer
# V6 — Stats modal, INDEX_GMAIL.html redirect
# V5 — Threads (conversations Gmail-style)
# V4 — Archi split (index.html + mails.js + bodies.js)
# V3 — Smart categories + Command palette + Dashboard
# V2 — Avatars + Snippets + Filtres + Dark/Light
# V1 — Core:
#   + Auto-detecte le .mbox ou .zip dans son dossier (zero config)
#   + Accepte aussi .mbox en argument CLI
#   + Fallback file picker tkinter si rien trouve
#   + Parse .mbox en memoire (mailbox.mbox + policy.default)
#   + Dedoublonnage par Message-ID (Gmail duplique par label)
#   + Extraction X-Gmail-Labels → multi-labels
#   + Body text (plain > html nettoye, 3000 chars max)
#   + Liste PJ avec tailles (sans extraction disque)
#   + Progression avec ETA
#   + Split-panel HTML: liste gauche / lecteur droite
#   + Navigation clavier (j/k, /, Esc reset ALL filters)
#   + Recherche multi-mots AND + filtre corps
#   + Filtre label (multi-labels) + filtre PJ
#   + Pagination 100/page
#   + JSON dans <script type=json> (bulletproof)
#   + ensure_ascii + escape < → \u003C
#   + Ouverture auto du HTML a la fin
#   + CLI: --test N pour limiter, --no-open pour skip ouverture
# ============================================

import mailbox
import os
import sys
import time
import json
import re
import html as html_mod
import zipfile
import webbrowser
import tempfile
import shutil
from email import policy
from email.parser import BytesParser
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime
from collections import Counter

# ============================================
# CONFIGURATION
# ============================================
BODY_MAX_CHARS = 0            # 0 = pas de troncature body (bodies.js separe)
SNIPPET_CHARS = 150           # Snippet dans la liste + mails.js
MIN_PJ_SIZE = 1024            # Ignore PJ < 1 Ko (pixels tracking)


# ============================================
# INPUT : AUTO-DETECTION + ZIP
# ============================================

def find_mbox_auto():
    """Auto-detecte les .mbox / dossiers .eml dans le dossier du script.
    Priorite : arguments CLI > .mbox > dossier .eml > .zip > file picker.
    Retourne une LISTE de chemins (fichiers .mbox/.zip ou dossiers contenant .eml)."""

    # LOG — ecrit un fichier de diagnostic a cote du script
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
                    log(f"      → EML detecte (ex: {eml_sample})")
                else:
                    log(f"      → Pas de .eml (3 niveaux)")
    except Exception as e:
        log(f"  [ERREUR] Listdir echoue : {e}")

    log(f"  Resultats : {len(mbox_files)} .mbox, {len(eml_dirs)} dossiers EML, {len(zip_files)} .zip")

    # .mbox trouves → TOUS
    if mbox_files:
        mbox_files.sort(key=os.path.getsize, reverse=True)
        for f in mbox_files:
            size_go = os.path.getsize(f) / (1024**3)
            log(f"  Selectionne : {os.path.basename(f)} ({size_go:.2f} Go)")
        flush_log()
        return mbox_files

    # Dossiers .eml → TOUS
    if eml_dirs:
        for d in eml_dirs:
            eml_count = sum(1 for _, _, fns in os.walk(d) for fn in fns if fn.lower().endswith(".eml"))
            log(f"  Selectionne dossier EML : {os.path.basename(d)}/ ({eml_count:,} .eml)")
        flush_log()
        return eml_dirs

    # .zip → TOUS
    if zip_files:
        zip_files.sort(key=os.path.getsize, reverse=True)
        for f in zip_files:
            size_go = os.path.getsize(f) / (1024**3)
            log(f"  Selectionne ZIP : {os.path.basename(f)} ({size_go:.2f} Go)")
        flush_log()
        return zip_files

    # 3) Rien trouve → file picker
    log("  RIEN TROUVE → ouverture file picker")
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
            # Dossier .eml → passer directement
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


# ============================================
# CLI ARGS
# ============================================

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


# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def decode_hdr(raw):
    """Decode un header MIME (UTF-8, ISO-8859, etc.)"""
    if raw is None:
        return ""
    try:
        parts = decode_header(raw)
        out = []
        for data, charset in parts:
            if isinstance(data, bytes):
                out.append(data.decode(charset or "utf-8", errors="replace"))
            else:
                out.append(str(data))
        return "".join(out)
    except Exception:
        return str(raw)


def sanitize_text(s):
    """Supprime les caracteres de controle qui cassent JSON/JS"""
    if not s:
        return s
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)


def get_date(msg):
    """Extrait la date, retourne (sortable, display) ou fallback"""
    for hdr in ("Date", "Received"):
        raw = msg.get(hdr, "")
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            loc = datetime.fromtimestamp(dt.timestamp())
            return loc.strftime("%Y-%m-%d %H:%M:%S"), loc.strftime("%d/%m/%Y %H:%M")
        except Exception:
            m = re.search(r'\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}', raw)
            if m:
                try:
                    from email.utils import parsedate
                    p = parsedate(m.group(0))
                    if p:
                        loc = datetime.fromtimestamp(time.mktime(p))
                        return loc.strftime("%Y-%m-%d %H:%M:%S"), loc.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass
    return "0000-00-00", ""


# ============================================
# EXTRACTION BODY
# ============================================

def extract_body_text(msg):
    """Extrait le corps texte (plain prioritaire, sinon html nettoye)"""
    text = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if part.get_filename():
                continue
            if ct == "text/plain" and "attachment" not in disp and not text:
                try:
                    c = part.get_content()
                    text = c if isinstance(c, str) else c.decode("utf-8", errors="replace")
                except Exception:
                    pass
            elif ct == "text/html" and "attachment" not in disp and not html_body:
                try:
                    c = part.get_content()
                    html_body = c if isinstance(c, str) else c.decode("utf-8", errors="replace")
                except Exception:
                    pass
    else:
        try:
            c = msg.get_content()
            if isinstance(c, bytes):
                c = c.decode("utf-8", errors="replace")
            if msg.get_content_type() == "text/html":
                html_body = c
            else:
                text = c
        except Exception:
            pass

    if text:
        return text[:50000]  # Safety cap 50K (newsletters geantes)
    if html_body:
        clean = re.sub(r'<style[^>]*>.*?</style>', '', html_body, flags=re.S | re.I)
        clean = re.sub(r'<script[^>]*>.*?</script>', '', clean, flags=re.S | re.I)
        clean = re.sub(r'<!--.*?-->', '', clean, flags=re.S)
        clean = re.sub(r'<br\s*/?\s*>', '\n', clean, flags=re.I)
        clean = re.sub(r'</p>', '\n\n', clean, flags=re.I)
        clean = re.sub(r'</div>', '\n', clean, flags=re.I)
        clean = re.sub(r'</tr>', '\n', clean, flags=re.I)
        clean = re.sub(r'</td>', ' | ', clean, flags=re.I)
        clean = re.sub(r'<[^>]+>', '', clean)
        clean = html_mod.unescape(clean)
        clean = re.sub(r'[ \t]+', ' ', clean)
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        return clean.strip()[:50000]
    return ""


# ============================================
# EXTRACTION PJ (listing seulement)
# ============================================

SKIP_MIME = {"text/plain", "text/html", "multipart/alternative", "multipart/mixed",
             "multipart/related", "multipart/signed", "multipart/report",
             "message/delivery-status", "message/rfc822"}

EXT_MAP = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "application/pdf": ".pdf",
    "application/zip": ".zip", "application/x-zip-compressed": ".zip",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/octet-stream": ".bin", "video/mp4": ".mp4",
    "audio/mpeg": ".mp3", "audio/ogg": ".ogg",
}


def extract_pj_list(msg):
    """Liste les PJ (nom + taille) sans les ecrire sur disque"""
    pj_list = []
    if not msg.is_multipart():
        return pj_list

    for part in msg.walk():
        ct = part.get_content_type()
        if ct in SKIP_MIME:
            continue

        filename = part.get_filename()
        if not filename:
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" not in disp:
                continue

        try:
            payload = part.get_payload(decode=True)
        except Exception:
            continue
        if payload is None:
            continue

        sz = len(payload)
        if sz < MIN_PJ_SIZE:
            continue

        if filename:
            name = decode_hdr(filename)
        else:
            ext = EXT_MAP.get(ct, ".bin")
            name = f"pj_sans_nom{ext}"

        if sz < 1048576:
            size_str = f"{sz / 1024:.0f} Ko"
        else:
            size_str = f"{sz / 1048576:.1f} Mo"

        pj_list.append(f"{name} ({size_str})")

    return pj_list


# ============================================
# LABELS GMAIL
# ============================================

def parse_gmail_labels(msg):
    """Extrait X-Gmail-Labels → liste de labels propres"""
    raw = msg.get("X-Gmail-Labels", "")
    if not raw:
        return ["Autres"]

    raw = decode_hdr(raw) if "=?" in str(raw) else str(raw)

    labels = []
    for label in raw.split(","):
        label = label.strip().strip('"')
        if label:
            labels.append(label)

    return labels if labels else ["Autres"]


# ============================================
# SMART CATEGORIES (heuristique, zero IA)
# ============================================

# Mots-cles par categorie — on check dans From + Subject
CAT_SOCIAL = {"facebook", "facebookmail", "linkedin", "twitter", "x.com",
              "instagram", "threads.net", "tiktok",
              "snapchat", "pinterest", "reddit", "discord", "whatsapp",
              "telegram", "meetup", "nextdoor", "strava",
              "mastodon", "bluesky", "bsky"}

CAT_BANQUE = {"banque", "credit", "caisse", "assurance", "mutuelle", "impot",
              "tresor", "boursorama", "fortuneo", "ing direct", "societe generale",
              "bnp", "lcl", "bred", "cic", "hsbc", "la banque postale",
              "paypal", "stripe", "revolut", "n26", "wise", "sofinco",
              "cetelem", "cofidis", "franfinance", "floa", "younited"}

CAT_ACHATS = {"amazon", "cdiscount", "fnac", "vinted", "leboncoin", "aliexpress",
              "ebay", "wish", "shein", "zalando", "asos", "boulanger", "darty",
              "order", "commande", "livraison", "colis", "facture", "invoice",
              "receipt", "shipped", "tracking", "expedition",
              "uber eats", "deliveroo", "just eat", "paack", "chronopost",
              "colissimo", "dpd", "ups", "fedex", "mondial relay", "relais colis",
              "gls", "tnt", "dhl", "laposte", "suivi"}

CAT_NOTIF = {"noreply", "no-reply", "no_reply", "donotreply",
             "ne-pas-repondre", "nepasrepondre", "automated",
             "mailer-daemon", "postmaster", "system@", "alert@",
             "notification@", "notifications@", "notify@"}

CAT_NEWSLETTER = {"newsletter", "digest", "weekly", "hebdo", "info@",
                  "news@", "bulletin", "unsubscribe", "marketing@",
                  "promo@", "campaign", "mailchimp", "sendinblue",
                  "brevo", "mailjet", "substack"}


def categorize_mail(mail_data, has_unsub=False):
    """Classifie un mail en categorie par heuristique sur From + Subject.
    Retourne: Perso, Achats, Banque, Newsletter, Notif, Social"""

    fr = (mail_data.get("ff", "") or "").lower()
    subj = (mail_data.get("s", "") or "").lower()
    haystack = fr + " " + subj
    labels_lower = [lb.lower() for lb in mail_data.get("labels", [])]

    # 1. Social (check first, very specific domain match)
    for kw in CAT_SOCIAL:
        if kw in fr:
            return "Social"

    # 2. Banque/Finance
    for kw in CAT_BANQUE:
        if kw in haystack:
            return "Banque"

    # 3. Achats/Livraisons
    for kw in CAT_ACHATS:
        if kw in haystack:
            return "Achats"

    # 4. Newsletter — AVANT Notif si has_unsub
    #    Fix V8: noreply@newsletter.mediapart.fr + has_unsub = Newsletter, pas Notif
    if has_unsub:
        return "Newsletter"
    for kw in CAT_NEWSLETTER:
        if kw in fr:
            return "Newsletter"

    # 5. Notif/Auto (noreply patterns) — seulement si PAS has_unsub
    for kw in CAT_NOTIF:
        if kw in fr:
            return "Notif"

    # 6. Gmail label hints
    for lb in labels_lower:
        if "achat" in lb or "purchase" in lb or "receipt" in lb:
            return "Achats"
        if "social" in lb:
            return "Social"
        if "promotions" in lb or "promo" in lb:
            return "Newsletter"
        if "updates" in lb or "mises" in lb or "category updates" in lb:
            return "Notif"
        if "forums" in lb or "category forums" in lb:
            return "Newsletter"

    return "Perso"


# ============================================
# PARSE — SHARED HELPER
# ============================================

def _build_mail_dict(message):
    """Transforme un email.message.Message en dict standardise.
    Retourne (mail_data, msg_id, labels, gm_thrid_used) ou None si erreur."""

    raw_id = message.get("Message-ID")
    msg_id = str(raw_id).strip() if raw_id else ""
    labels = parse_gmail_labels(message)

    ds, dd = get_date(message)

    fr = str(message.get("From", ""))
    fr_short = fr
    m = re.match(r'"?([^"<]+)"?\s*<', fr)
    if m:
        fr_short = m.group(1).strip()

    to_raw = str(message.get("To", ""))
    cc_raw = str(message.get("Cc", ""))
    subj = str(message.get("Subject", ""))

    body = extract_body_text(message)
    pj_list = extract_pj_list(message)

    has_unsub = bool(message.get("List-Unsubscribe", ""))

    # Thread ID
    gm_thrid = str(message.get("X-GM-THRID", "")).strip()
    gm_thrid_used = False
    if gm_thrid:
        tid = f"gm-{gm_thrid}"
        gm_thrid_used = True
    else:
        refs_raw = str(message.get("References", ""))
        inreply = str(message.get("In-Reply-To", ""))
        refs_ids = re.findall(r'<[^>]+>', refs_raw)
        if refs_ids:
            tid = refs_ids[0]
        elif inreply and inreply.strip():
            tid = inreply.strip()
        else:
            tid = msg_id or ""

    snippet = ""
    if body:
        snippet = body[:SNIPPET_CHARS].replace("\r", " ").replace("\n", " ")
        snippet = re.sub(r'<[^>]+>', '', snippet)
        snippet = html_mod.unescape(snippet)
        snippet = re.sub(r' +', ' ', snippet).strip()

    mail_data = {
        "ds": ds, "d": dd,
        "f": sanitize_text(fr_short[:80]),
        "ff": sanitize_text(fr[:200]),
        "to": sanitize_text(to_raw[:200]),
        "cc": sanitize_text(cc_raw[:200]),
        "s": sanitize_text(subj[:200]),
        "labels": labels,
        "l": labels[0] if labels else "Autres",
        "p": len(pj_list),
        "pj": [sanitize_text(p) for p in pj_list],
        "b": sanitize_text(body),
        "sn": sanitize_text(snippet),
        "tid": tid,
    }

    mail_data["cat"] = categorize_mail(mail_data, has_unsub)

    labels_lower = {lb.lower() for lb in labels}
    mail_data["spam"] = 1 if labels_lower & {"spam", "junk"} else 0
    mail_data["trash"] = 1 if labels_lower & {"corbeille", "trash"} else 0
    mail_data["sent"] = 1 if labels_lower & {"envoyés", "sent", "envoy\u00e9s"} else 0
    mail_data["_mid"] = msg_id  # Pour extraction PJ (supprime avant JSON)

    return mail_data, msg_id, labels, gm_thrid_used


# ============================================
# PARSE .MBOX
# ============================================

def parse_mbox(mbox_path, test_limit=0, seen_ids=None, existing_mails=None):
    """Parse le .mbox, dedoublonne par Message-ID, retourne liste de dicts.
    Si seen_ids/existing_mails fournis, deduplication cross-fichiers."""

    if not os.path.isfile(mbox_path):
        print(f"\n  [ERREUR] Fichier introuvable : {mbox_path}")
        return existing_mails or []

    # Cross-file dedup state
    if seen_ids is None:
        seen_ids = {}
    mails = existing_mails if existing_mails is not None else []
    cross_file = len(mails) > 0  # True si on ajoute a un resultat existant

    file_size = os.path.getsize(mbox_path)

    print()
    print("=" * 60)
    src_name = os.path.basename(mbox_path)
    if cross_file:
        print(f"  PARSE — {src_name} (fusion)")
    else:
        print(f"  TakeoutReader -- PARSE")
    print("=" * 60)
    print(f"  Source  : {mbox_path}")
    print(f"  Taille  : {file_size / (1024**3):.2f} Go")
    print(f"  Body    : complet (snippet {SNIPPET_CHARS} car. dans la liste)")
    if cross_file:
        print(f"  Deja    : {len(mails):,} mails en memoire ({len(seen_ids):,} IDs)")
    if test_limit:
        print(f"  TEST    : {test_limit} mails max")
    print("=" * 60)
    print()

    parser = BytesParser(policy=policy.default)
    mbox = mailbox.mbox(mbox_path, factory=lambda f: parser.parse(f))

    start = time.time()
    mails_before = len(mails)  # Track per-file additions
    total_raw = 0
    dupes = 0
    erreurs = 0
    gm_thrid_count = 0

    for message in mbox:
        total_raw += 1

        if test_limit and total_raw > test_limit:
            break

        # Progression toutes les 500 avec ETA
        if total_raw % 500 == 0:
            elapsed = time.time() - start
            speed = total_raw / elapsed if elapsed > 0 else 0
            # ETA basee sur la taille: estimer le nb total de mails
            # Heuristique: 1 mail ~ 30-50 Ko dans un mbox moyen
            avg_mail_size = file_size / total_raw if total_raw > 0 else 40000
            est_total = int(file_size / avg_mail_size) if avg_mail_size > 0 else 0
            remaining = max(0, est_total - total_raw)
            eta_s = remaining / speed if speed > 0 else 0
            eta_str = f"~{eta_s:.0f}s" if eta_s < 120 else f"~{eta_s/60:.0f}min"

            print(f"  ... {total_raw:,} lus | {len(mails):,} uniques | "
                  f"{dupes:,} doublons | {elapsed:.0f}s | {speed:.0f}/s | ETA {eta_str}",
                  flush=True)

        try:
            result = _build_mail_dict(message)
            if result is None:
                erreurs += 1
                continue

            mail_data, msg_id, labels, gm_used = result
            if gm_used:
                gm_thrid_count += 1

            # Dedoublonnage
            if msg_id and msg_id in seen_ids:
                idx = seen_ids[msg_id]
                existing = set(mails[idx]["labels"])
                for lb in labels:
                    if lb not in existing:
                        mails[idx]["labels"].append(lb)
                dupes += 1
                continue

            mail_data["_src"] = mbox_path
            mail_data["_src_type"] = "mbox"
            mails.append(mail_data)
            if msg_id:
                seen_ids[msg_id] = len(mails) - 1

        except Exception as e:
            erreurs += 1
            if erreurs <= 10:
                print(f"  [!] Erreur mail #{total_raw}: {e}")

    elapsed = time.time() - start
    mails_added = len(mails) - mails_before
    mails.sort(key=lambda m: m["ds"], reverse=True)

    # Stats labels
    all_labels = Counter()
    for m in mails:
        for lb in m["labels"]:
            all_labels[lb] += 1

    # Stats categories
    cat_stats = Counter(m["cat"] for m in mails)

    # Stats threads
    thread_ids = Counter(m["tid"] for m in mails if m["tid"])
    threads_multi = sum(1 for c in thread_ids.values() if c > 1)

    print()
    print("=" * 60)
    src_name = os.path.basename(mbox_path)
    print(f"  BILAN PARSE — {src_name}")
    print("=" * 60)
    print(f"  Mails bruts (mbox)  : {total_raw:,}")
    print(f"  Doublons supprimes  : {dupes:,}")
    print(f"  Nouveaux ajoutes    : {mails_added:,}")
    if cross_file:
        print(f"  TOTAL cumule        : {len(mails):,}")
    else:
        print(f"  Mails uniques       : {len(mails):,}")
    print(f"  Avec PJ             : {sum(1 for m in mails if m['p'] > 0):,}")
    print(f"  Labels distincts    : {len(all_labels)}")
    print(f"  Threads (multi)     : {threads_multi:,}")
    print(f"  X-GM-THRID (Gmail)  : {gm_thrid_count:,}/{mails_added:,} ({gm_thrid_count*100//max(mails_added,1)}%)")
    spam_count = sum(1 for m in mails if m.get("spam"))
    trash_count = sum(1 for m in mails if m.get("trash"))
    sent_count = sum(1 for m in mails if m.get("sent"))
    print(f"  Spam                : {spam_count:,}")
    print(f"  Corbeille           : {trash_count:,}")
    print(f"  Envoyes             : {sent_count:,}")
    print(f"  Erreurs             : {erreurs}")
    print(f"  Duree               : {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print()
    if not cross_file and cat_stats:
        print("  Categories auto :")
        for cat, count in cat_stats.most_common():
            pct = count * 100 / len(mails) if mails else 0
            print(f"    {cat:15s} : {count:,} ({pct:.0f}%)")
        print()
    if not cross_file and all_labels:
        print("  Top 15 labels :")
        for lb, count in all_labels.most_common(15):
            print(f"    {lb:30s} : {count:,}")
    print("=" * 60)

    return mails, seen_ids


# ============================================
# PARSE DOSSIER .EML
# ============================================

def _find_all_eml(root):
    """Trouve tous les .eml recursivement"""
    eml = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".eml"):
                eml.append(os.path.join(dp, fn))
    return sorted(eml)


def parse_eml_folder(folder_path, test_limit=0, seen_ids=None, existing_mails=None):
    """Parse un dossier de .eml (ex: MAILS_EXTRAITS), meme format que parse_mbox.
    Deduplication cross-fichiers si seen_ids/existing_mails fournis."""

    if not os.path.isdir(folder_path):
        print(f"\n  [ERREUR] Dossier introuvable : {folder_path}")
        return (existing_mails or []), (seen_ids or {})

    if seen_ids is None:
        seen_ids = {}
    mails = existing_mails if existing_mails is not None else []
    cross_file = len(mails) > 0

    # Scan .eml
    eml_files = _find_all_eml(folder_path)
    if not eml_files:
        print(f"\n  [!] Aucun .eml trouve dans {folder_path}")
        return mails, seen_ids

    total_size = sum(os.path.getsize(f) for f in eml_files)

    print()
    print("=" * 60)
    src_name = os.path.basename(folder_path)
    if cross_file:
        print(f"  PARSE EML — {src_name} (fusion)")
    else:
        print(f"  PARSE EML — {src_name}")
    print("=" * 60)
    print(f"  Dossier : {folder_path}")
    print(f"  Fichiers: {len(eml_files):,} .eml ({total_size / (1024**2):.0f} Mo)")
    print(f"  Body    : complet (snippet {SNIPPET_CHARS} car. dans la liste)")
    if cross_file:
        print(f"  Deja    : {len(mails):,} mails en memoire ({len(seen_ids):,} IDs)")
    if test_limit:
        print(f"  TEST    : {test_limit} mails max")
    print("=" * 60)
    print()

    parser = BytesParser(policy=policy.default)
    start = time.time()
    mails_before = len(mails)
    total_raw = 0
    dupes = 0
    erreurs = 0
    gm_thrid_count = 0

    for eml_path in eml_files:
        total_raw += 1

        if test_limit and total_raw > test_limit:
            break

        if total_raw % 500 == 0:
            elapsed = time.time() - start
            speed = total_raw / elapsed if elapsed > 0 else 0
            remaining = len(eml_files) - total_raw
            eta_s = remaining / speed if speed > 0 else 0
            eta_str = f"~{eta_s:.0f}s" if eta_s < 120 else f"~{eta_s/60:.0f}min"
            print(f"  ... {total_raw:,}/{len(eml_files):,} | {len(mails):,} uniques | "
                  f"{dupes:,} doublons | {elapsed:.0f}s | {speed:.0f}/s | ETA {eta_str}",
                  flush=True)

        try:
            with open(eml_path, "rb") as f:
                message = parser.parsebytes(f.read())

            result = _build_mail_dict(message)
            if result is None:
                erreurs += 1
                continue

            mail_data, msg_id, labels, gm_used = result
            if gm_used:
                gm_thrid_count += 1

            # Si pas de labels Gmail, deduire du chemin (sous-dossier = label)
            if not labels or labels == ["Autres"]:
                rel = os.path.relpath(eml_path, folder_path)
                parts = rel.replace("\\", "/").split("/")
                if len(parts) > 1:
                    folder_label = parts[0]
                    if folder_label not in (".", "PJ"):
                        mail_data["labels"] = [folder_label]
                        mail_data["l"] = folder_label

            labels = mail_data["labels"]

            # Dedoublonnage
            if msg_id and msg_id in seen_ids:
                idx = seen_ids[msg_id]
                existing = set(mails[idx]["labels"])
                for lb in labels:
                    if lb not in existing:
                        mails[idx]["labels"].append(lb)
                dupes += 1
                continue

            mail_data["_src"] = eml_path
            mail_data["_src_type"] = "eml"
            mails.append(mail_data)
            if msg_id:
                seen_ids[msg_id] = len(mails) - 1

        except Exception as e:
            erreurs += 1
            if erreurs <= 10:
                print(f"  [!] Erreur {os.path.basename(eml_path)}: {e}")

    elapsed = time.time() - start
    mails_added = len(mails) - mails_before
    mails.sort(key=lambda m: m["ds"], reverse=True)

    print()
    print("=" * 60)
    print(f"  BILAN PARSE EML — {src_name}")
    print("=" * 60)
    print(f"  Fichiers .eml       : {total_raw:,}")
    print(f"  Doublons supprimes  : {dupes:,}")
    print(f"  Nouveaux ajoutes    : {mails_added:,}")
    if cross_file:
        print(f"  TOTAL cumule        : {len(mails):,}")
    else:
        print(f"  Mails uniques       : {len(mails):,}")
    print(f"  Avec PJ             : {sum(1 for m in mails if m['p'] > 0):,}")
    print(f"  X-GM-THRID (Gmail)  : {gm_thrid_count:,}/{mails_added:,} ({gm_thrid_count*100//max(mails_added,1)}%)")
    print(f"  Erreurs             : {erreurs}")
    print(f"  Duree               : {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print("=" * 60)

    return mails, seen_ids


def parse_multi_sources(source_paths, test_limit=0):
    """Parse plusieurs sources (.mbox fichiers ou dossiers .eml) avec dedup cross.
    Retourne la liste fusionnee de mails."""

    # Single source shortcut
    if len(source_paths) == 1:
        p = source_paths[0]
        if os.path.isdir(p):
            mails, _ = parse_eml_folder(p, test_limit=test_limit)
        else:
            mails, _ = parse_mbox(p, test_limit=test_limit)
        return mails

    print()
    print("=" * 60)
    print(f"  FUSION MULTI-SOURCE — {len(source_paths)} sources")
    print("=" * 60)
    for i, p in enumerate(source_paths, 1):
        if os.path.isdir(p):
            eml_count = len(_find_all_eml(p))
            print(f"  [{i}] {os.path.basename(p)}/ ({eml_count:,} .eml)")
        else:
            size_go = os.path.getsize(p) / (1024**3) if os.path.isfile(p) else 0
            print(f"  [{i}] {os.path.basename(p)} ({size_go:.2f} Go)")
    print("=" * 60)

    seen_ids = {}
    mails = []

    for i, src_path in enumerate(source_paths, 1):
        print(f"\n  ━━━ Source {i}/{len(source_paths)} ━━━")
        if os.path.isdir(src_path):
            mails, seen_ids = parse_eml_folder(
                src_path,
                test_limit=test_limit,
                seen_ids=seen_ids,
                existing_mails=mails
            )
        else:
            mails, seen_ids = parse_mbox(
                src_path,
                test_limit=test_limit,
                seen_ids=seen_ids,
                existing_mails=mails
            )

    # Bilan final multi-source
    if len(source_paths) > 1:
        all_labels = Counter()
        for m in mails:
            for lb in m["labels"]:
                all_labels[lb] += 1
        cat_stats = Counter(m["cat"] for m in mails)

        print()
        print("=" * 60)
        print("  BILAN FUSION")
        print("=" * 60)
        print(f"  Sources             : {len(source_paths)}")
        print(f"  Mails uniques total : {len(mails):,}")
        print(f"  IDs connus (dedup)  : {len(seen_ids):,}")
        print(f"  Labels distincts    : {len(all_labels)}")
        print(f"  Avec PJ             : {sum(1 for m in mails if m['p'] > 0):,}")
        print()
        if cat_stats:
            print("  Categories auto :")
            for cat, count in cat_stats.most_common():
                pct = count * 100 / len(mails) if mails else 0
                print(f"    {cat:15s} : {count:,} ({pct:.0f}%)")
            print()
        if all_labels:
            print("  Top 15 labels :")
            for lb, count in all_labels.most_common(15):
                print(f"    {lb:30s} : {count:,}")
        print("=" * 60)

    return mails


# ============================================
# HTML GENERATION — V2


# ============================================
# OUTPUT GENERATION — V4
# Sortie = dossier : index.html + mails.js + bodies.js
# mails.js charge instantanement (pas de body)
# bodies.js charge en arriere-plan (body complet)
# ============================================


def _sanitize_pj_filename(name):
    """Nettoie un nom de fichier PJ pour le filesystem"""
    if not name:
        return "sans_nom"
    forbidden = '<>:"/\\|?*\r\n\t'
    for c in forbidden:
        name = name.replace(c, "_")
    name = name.strip(". ")
    if len(name) > 180:
        base, ext = os.path.splitext(name)
        name = base[:175] + ext
    return name if name else "sans_nom"


def _extract_pj_from_message(msg):
    """Extrait les PJ binaires d'un message. Retourne [(filename, bytes), ...]"""
    pj_files = []
    if not msg.is_multipart():
        return pj_files

    for part in msg.walk():
        ct = part.get_content_type()
        if ct in SKIP_MIME:
            continue

        filename = part.get_filename()
        if not filename:
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" not in disp:
                continue

        try:
            payload = part.get_payload(decode=True)
        except Exception:
            continue
        if payload is None or len(payload) < MIN_PJ_SIZE:
            continue

        if filename:
            name = _sanitize_pj_filename(decode_hdr(filename))
        else:
            ext = EXT_MAP.get(ct, ".bin")
            name = f"pj_sans_nom{ext}"

        pj_files.append((name, payload))

    return pj_files


def extract_pj_to_disk(mails, output_dir):
    """Extrait les PJ sur disque dans output_dir/pj/.
    Met a jour mail['pjp'] avec les chemins relatifs."""

    mails_with_pj = [(i, m) for i, m in enumerate(mails)
                     if m.get("p", 0) > 0 and m.get("_src")]

    if not mails_with_pj:
        print("    Aucune PJ a extraire (pas de source)")
        return 0, 0

    pj_dir = os.path.join(output_dir, "pj")
    os.makedirs(pj_dir, exist_ok=True)

    print(f"  [PJ] Extraction de {len(mails_with_pj):,} mails avec PJ...", flush=True)

    from collections import defaultdict
    eml_mails = [(i, m) for i, m in mails_with_pj if m.get("_src_type") == "eml"]
    mbox_groups = defaultdict(list)
    for i, m in mails_with_pj:
        if m.get("_src_type") == "mbox":
            mbox_groups[m["_src"]].append((i, m))

    nb_extracted = 0
    total_bytes = 0
    erreurs = 0
    start = time.time()

    parser = BytesParser(policy=policy.default)
    for idx_done, (mail_idx, m) in enumerate(eml_mails):
        if (idx_done + 1) % 500 == 0:
            elapsed = time.time() - start
            print(f"    ... {idx_done+1:,}/{len(eml_mails):,} eml | "
                  f"{nb_extracted:,} PJ | {elapsed:.0f}s", flush=True)

        try:
            with open(m["_src"], "rb") as f:
                msg = parser.parsebytes(f.read())

            pj_files = _extract_pj_from_message(msg)
            pjp = []

            if pj_files:
                mail_pj_dir = os.path.join(pj_dir, f"{mail_idx:05d}")
                os.makedirs(mail_pj_dir, exist_ok=True)

                for name, data in pj_files:
                    filepath = os.path.join(mail_pj_dir, name)
                    if os.path.exists(filepath):
                        base, ext = os.path.splitext(name)
                        counter = 1
                        while os.path.exists(filepath):
                            filepath = os.path.join(mail_pj_dir, f"{base}_{counter:02d}{ext}")
                            counter += 1
                        name = os.path.basename(filepath)

                    with open(filepath, "wb") as fout:
                        fout.write(data)

                    rel_path = f"pj/{mail_idx:05d}/{name}"
                    pjp.append(rel_path)
                    nb_extracted += 1
                    total_bytes += len(data)

            m["pjp"] = pjp

        except Exception as e:
            erreurs += 1
            if erreurs <= 10:
                print(f"    [!] PJ erreur {os.path.basename(m.get(chr(95)+chr(115)+chr(114)+chr(99), chr(63)))}: {e}")

    for mbox_path, mail_list in mbox_groups.items():
        if not os.path.isfile(mbox_path):
            continue

        mid_to_mail = {}
        for mail_idx, m in mail_list:
            mid = m.get("_mid", "")
            if mid:
                mid_to_mail[mid] = (mail_idx, m)

        if not mid_to_mail:
            continue

        print(f"    [PJ/MBOX] Re-lecture {os.path.basename(mbox_path)} "
              f"pour {len(mid_to_mail):,} mails...", flush=True)

        mbox = mailbox.mbox(mbox_path, factory=lambda f: parser.parse(f))
        found = 0

        for message in mbox:
            if not mid_to_mail:
                break

            raw_id = message.get("Message-ID")
            msg_id = str(raw_id).strip() if raw_id else ""

            if msg_id not in mid_to_mail:
                continue

            mail_idx, m = mid_to_mail.pop(msg_id)
            found += 1

            try:
                pj_files = _extract_pj_from_message(message)
                pjp = []

                if pj_files:
                    mail_pj_dir = os.path.join(pj_dir, f"{mail_idx:05d}")
                    os.makedirs(mail_pj_dir, exist_ok=True)

                    for name, data in pj_files:
                        filepath = os.path.join(mail_pj_dir, name)
                        if os.path.exists(filepath):
                            base, ext = os.path.splitext(name)
                            counter = 1
                            while os.path.exists(filepath):
                                filepath = os.path.join(mail_pj_dir, f"{base}_{counter:02d}{ext}")
                                counter += 1
                            name = os.path.basename(filepath)

                        with open(filepath, "wb") as fout:
                            fout.write(data)

                        rel_path = f"pj/{mail_idx:05d}/{name}"
                        pjp.append(rel_path)
                        nb_extracted += 1
                        total_bytes += len(data)

                m["pjp"] = pjp

            except Exception as e:
                erreurs += 1

        print(f"    [PJ/MBOX] {found:,} mails trouves, PJ extraites")

    elapsed = time.time() - start
    print(f"  [PJ] {nb_extracted:,} fichiers extraits "
          f"({total_bytes / (1024**2):.1f} Mo) en {elapsed:.0f}s"
          + (f", {erreurs} erreurs" if erreurs else ""))

    return nb_extracted, total_bytes


def generate_output(mails, output_dir):
    """Cree un dossier avec index.html + mails.js + bodies.js.
    Retourne la taille totale en Mo."""

    os.makedirs(output_dir, exist_ok=True)

    all_labels = Counter()
    for m in mails:
        for lb in m["labels"]:
            all_labels[lb] += 1
    total_pj = sum(m["p"] for m in mails)
    nb = len(mails)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    dates = [m["ds"] for m in mails if m["ds"] != "0000-00-00"]
    date_min = dates[-1][:4] if dates else "?"
    date_max = dates[0][:4] if dates else "?"

    # === EXTRACT PJ TO DISK ===
    print("  [PJ] Extraction des pieces jointes...", flush=True)
    extract_pj_to_disk(mails, output_dir)

    # === MAILS.JS — headers + snippet, PAS de body ===
    mails_light = []
    bodies = []
    for m in mails:
        light = {k: m[k] for k in ("ds", "d", "f", "ff", "to", "cc", "s",
                                     "labels", "l", "p", "pj", "cat", "tid", "sn",
                                     "spam", "trash", "sent")}
        # Ajouter chemins PJ si extraites
        if "pjp" in m:
            light["pjp"] = m["pjp"]
        mails_light.append(light)
        bodies.append(m.get("b", ""))

    mails_json = json.dumps(mails_light, ensure_ascii=True, separators=(',', ':'))
    mails_json = mails_json.replace("<", "\\u003C")

    mails_js_path = os.path.join(output_dir, "mails.js")
    with open(mails_js_path, "w", encoding="utf-8") as f:
        f.write("var D=")
        f.write(mails_json)
        f.write(";\n")

    mails_size = os.path.getsize(mails_js_path) / (1024 * 1024)
    print(f"    mails.js  : {mails_size:.1f} Mo ({nb:,} mails)", flush=True)

    # === BODIES.JS — full body array, same index as D ===
    bodies_json = json.dumps(bodies, ensure_ascii=True, separators=(',', ':'))
    bodies_json = bodies_json.replace("<", "\\u003C")

    bodies_js_path = os.path.join(output_dir, "bodies.js")
    with open(bodies_js_path, "w", encoding="utf-8") as f:
        f.write("var B=")
        f.write(bodies_json)
        f.write(";\n")

    bodies_size = os.path.getsize(bodies_js_path) / (1024 * 1024)
    print(f"    bodies.js : {bodies_size:.1f} Mo", flush=True)

    # === DASHBOARD DATA (dans le HTML, pas dans le JSON) ===
    cat_stats = Counter(m["cat"] for m in mails)
    year_stats = Counter()
    sender_stats = Counter()
    for m in mails:
        y = m["ds"][:4]
        if y != "0000":
            year_stats[y] += 1
        sender_stats[m["f"]] += 1
    top_senders = sender_stats.most_common(8)
    years_sorted = sorted(year_stats.items(), reverse=True)

    # Thread count
    tid_count = Counter(m["tid"] for m in mails if m.get("tid"))
    threads_multi = sum(1 for c in tid_count.values() if c > 1)

    cat_order = ["Perso", "Achats", "Banque", "Newsletter", "Notif", "Social"]
    cat_emoji = {"Perso": "&#9993;", "Achats": "&#128230;", "Banque": "&#127974;",
                 "Newsletter": "&#128240;", "Notif": "&#128276;", "Social": "&#128172;"}
    cat_colors = {"Perso": "#4FC3F7", "Achats": "#FFB74D", "Banque": "#81C784",
                  "Newsletter": "#BA68C8", "Notif": "#90A4AE", "Social": "#F06292"}

    max_yr = max(year_stats.values()) if year_stats else 1
    dash_cats = ""
    for cat in cat_order:
        cnt = cat_stats.get(cat, 0)
        if cnt == 0:
            continue
        pct = cnt * 100 // nb if nb else 0
        col = cat_colors.get(cat, "#888")
        emo = cat_emoji.get(cat, "")
        dash_cats += (f'<div class="dc" onclick="dCat(\'{cat}\')" style="border-color:{col}">'
                      f'<div class="dcn">{emo} {cat}</div>'
                      f'<div class="dcc" style="color:{col}">{cnt:,}</div>'
                      f'<div class="dcp">{pct}%</div></div>')

    dash_years = ""
    for yr, cnt in years_sorted:
        w = max(8, cnt * 100 // max_yr)
        dash_years += (f'<div class="dy" onclick="dYr(\'{yr}\')">'
                       f'<span class="dyl">{yr}</span>'
                       f'<div class="dyb"><div class="dyf" style="width:{w}%"></div></div>'
                       f'<span class="dyc">{cnt:,}</span></div>')

    dash_snd = ""
    for snd, cnt in top_senders:
        snd_esc = snd.replace("'", "\\'").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        snd_disp = html_mod.escape(snd[:25] + ("..." if len(snd) > 25 else ""))
        dash_snd += (f'<div class="dse" onclick="dSnd(\'{snd_esc}\')">'
                     f'<span class="dsn">{snd_disp}</span>'
                     f'<span class="dsc">{cnt:,}</span></div>')

    # === INDEX.HTML ===
    index_html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gmail Archive - {nb:,} mails</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#0D0D10;--bg1:#16161D;--bg2:#1E1E28;--bg3:#2A2A38;--brd:#3A3A4A;--t:#E8E8F0;--t2:#B8B8C8;--t3:#8888A0;--ac:#B388FF;--ac2:#9C64FF;--gn:#A5D6A7;--gnbg:#1B2E1E;--hover:#1E1B2E;--act:#251E3E;--actbrd:#B388FF;--dbg:#181820;--shadow:0 1px 4px rgba(80,40,120,.25);--glow:0 0 0 2px rgba(179,136,255,.2)}}
body.light{{--bg:#FDF5F7;--bg1:#FFFFFF;--bg2:#F5EAEE;--bg3:#EADFDF;--brd:#DDD0D5;--t:#2A1A20;--t2:#5A3A45;--t3:#8A6A75;--ac:#E91E63;--ac2:#C2185B;--gn:#2E7D32;--gnbg:#E8F5E9;--hover:#FDE8EE;--act:#FCE4EC;--actbrd:#E91E63;--dbg:#FFFFFF;--shadow:0 1px 4px rgba(120,40,60,.08);--glow:0 0 0 2px rgba(233,30,99,.15)}}
body{{background:var(--bg);color:var(--t);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;font-size:14px;height:100vh;overflow:hidden;display:flex;flex-direction:column;transition:background .3s,color .3s}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
::-webkit-scrollbar{{width:7px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:var(--bg3);border-radius:4px}}::-webkit-scrollbar-thumb:hover{{background:var(--t3)}}
.hdr{{background:var(--bg1);border-bottom:1px solid var(--brd);padding:12px 20px;display:flex;align-items:center;gap:12px;flex-shrink:0;flex-wrap:wrap;box-shadow:var(--shadow);animation:fadeIn .4s}}
.hdr h1{{font-size:18px;font-weight:700;color:var(--t);white-space:nowrap;letter-spacing:-.3px;cursor:pointer}}
.stats{{display:flex;gap:12px;font-size:12px;color:var(--t3)}}.stats b{{color:var(--t2);font-weight:600}}
.hdr-r{{display:flex;gap:8px;margin-left:auto;align-items:center}}
.thb,.cmdb{{background:transparent;border:1px solid var(--brd);border-radius:8px;padding:5px 11px;font-size:14px;cursor:pointer;color:var(--t2);transition:all .2s}}
.thb:hover,.cmdb:hover{{border-color:var(--ac);color:var(--ac);box-shadow:var(--glow)}}
.ctl{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 16px;border-bottom:1px solid var(--brd);background:var(--bg1);flex-shrink:0;box-shadow:var(--shadow);animation:fadeIn .5s}}
.sbw{{position:relative;display:flex;align-items:center}}.sbw::before{{content:"\\1F50D";position:absolute;left:10px;font-size:11px;pointer-events:none;opacity:.45}}
.sb{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:8px 14px 8px 32px;color:var(--t);font-size:13px;width:220px;outline:none;transition:border-color .2s,box-shadow .2s}}
.sb:focus{{border-color:var(--ac);box-shadow:var(--glow)}}.sb::placeholder{{color:var(--t3)}}
select{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:7px 10px;color:var(--t);font-size:12px;outline:none;cursor:pointer;max-width:160px;transition:border-color .2s,box-shadow .2s}}
select:focus{{border-color:var(--ac);box-shadow:var(--glow)}}
.tgl{{display:flex;align-items:center;gap:4px;font-size:11px;color:var(--t3);cursor:pointer;user-select:none}}.tgl input{{accent-color:var(--ac)}}
.tgl.dis{{opacity:.4;pointer-events:none}}
.cnt{{color:var(--t3);font-size:12px;margin-left:auto;white-space:nowrap}}
.bld{{font-size:10px;color:var(--gn);margin-left:4px}}

/* DASHBOARD = MODAL OVERLAY */
.dash-ov{{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998;display:none;align-items:center;justify-content:center}}
.dash-ov.on{{display:flex}}
.dash{{background:var(--bg1);border:1px solid var(--brd);border-radius:16px;width:680px;max-height:80vh;overflow-y:auto;display:flex;flex-direction:column;align-items:center;padding:32px 28px;gap:24px;box-shadow:0 20px 60px rgba(80,40,120,.3);position:relative;animation:fadeUp .3s}}
.dash-t{{font-size:22px;font-weight:700;color:var(--t);text-align:center}}
.dash-t small{{display:block;font-size:13px;font-weight:400;color:var(--t3);margin-top:4px}}
.dash-s{{display:flex;gap:20px;font-size:12px;color:var(--t2);flex-wrap:wrap;justify-content:center}}
.dash-s b{{font-size:18px;display:block;color:var(--t);font-weight:700}}
.dash-x{{position:absolute;top:12px;right:16px;background:none;border:none;color:var(--t3);font-size:20px;cursor:pointer;padding:4px 8px;border-radius:4px}}
.dash-x:hover{{color:var(--t);background:var(--bg3)}}
.dcs{{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;max-width:700px}}
.dc{{background:var(--bg1);border:1px solid var(--brd);border-left:3px solid;border-radius:10px;padding:14px 18px;min-width:100px;cursor:pointer;transition:transform .15s,box-shadow .15s;text-align:center}}
.dc:hover{{transform:translateY(-2px);box-shadow:0 6px 16px rgba(0,0,0,.3)}}
.dcn{{font-size:12px;color:var(--t2);margin-bottom:4px}}.dcc{{font-size:22px;font-weight:700}}.dcp{{font-size:11px;color:var(--t3)}}
.dyr{{max-width:500px;width:100%}}.dyr-t{{font-size:13px;font-weight:600;color:var(--t2);margin-bottom:8px}}
.dy{{display:flex;align-items:center;gap:8px;padding:3px 0;cursor:pointer;border-radius:4px;transition:background .1s}}.dy:hover{{background:var(--hover)}}
.dyl{{width:40px;text-align:right;font-size:12px;color:var(--t3);font-variant-numeric:tabular-nums}}
.dyb{{flex:1;height:16px;background:var(--bg3);border-radius:3px;overflow:hidden}}.dyf{{height:100%;background:var(--ac);border-radius:3px;transition:width .3s}}
.dyc{{width:45px;font-size:12px;color:var(--t2);font-variant-numeric:tabular-nums}}
.dss{{max-width:500px;width:100%}}.dss-t{{font-size:13px;font-weight:600;color:var(--t2);margin-bottom:8px}}
.dse{{display:flex;justify-content:space-between;padding:4px 8px;cursor:pointer;border-radius:4px;transition:background .1s;font-size:12px}}.dse:hover{{background:var(--hover)}}
.dsn{{color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.dsc{{color:var(--t3);flex-shrink:0;margin-left:8px;font-variant-numeric:tabular-nums}}

/* COMMAND PALETTE */
.cpo{{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:999;display:none;align-items:flex-start;justify-content:center;padding-top:15vh}}
.cpo.on{{display:flex}}
.cpb{{background:var(--bg1);border:1px solid var(--brd);border-radius:14px;width:520px;max-height:400px;overflow:hidden;box-shadow:0 20px 60px rgba(80,40,120,.3);animation:fadeUp .2s}}
.cpi{{width:100%;padding:14px 18px;border:none;border-bottom:1px solid var(--brd);background:transparent;color:var(--t);font-size:15px;outline:none}}.cpi::placeholder{{color:var(--t3)}}
.cpr{{overflow-y:auto;max-height:340px}}
.cpri{{padding:10px 18px;cursor:pointer;display:flex;align-items:center;gap:10px;font-size:13px;color:var(--t2);transition:background .1s}}
.cpri:hover,.cpri.sel{{background:var(--hover);color:var(--t)}}
.cpri .ck{{color:var(--t3);font-size:11px;margin-left:auto}}.cpri .ce{{font-size:16px;width:22px;text-align:center}}

/* MAIN SPLIT */
.main{{flex:1;display:flex;overflow:hidden}}
.lp{{width:44%;min-width:320px;border-right:1px solid var(--brd);display:flex;flex-direction:column;overflow:hidden}}
.ls{{flex:1;overflow-y:auto}}
.mr{{padding:10px 14px;border-bottom:1px solid var(--bg3);cursor:pointer;transition:background .15s,transform .1s;display:flex;gap:10px;align-items:flex-start;animation:fadeUp .25s backwards}}
.mr:hover{{background:var(--hover);transform:translateX(2px)}}
.mr.act{{background:var(--act);border-left:3px solid var(--actbrd);padding-left:11px;transform:translateX(0)}}
.av{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0;margin-top:1px;letter-spacing:-.5px;box-shadow:0 1px 3px rgba(0,0,0,.3)}}
.mc{{flex:1;min-width:0}}
.mc .top{{display:flex;justify-content:space-between;gap:8px}}
.mc .frm{{font-weight:600;font-size:13px;color:var(--t);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}}
.mc .dt{{font-size:11px;color:var(--t3);white-space:nowrap;font-variant-numeric:tabular-nums}}
.mc .su{{font-size:13px;color:var(--t2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}}
.mc .sn{{font-size:12px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px;line-height:1.3}}
.mc .mt{{display:flex;gap:4px;margin-top:3px;flex-wrap:wrap;align-items:center}}
.lb{{background:var(--bg3);border:1px solid var(--brd);border-radius:4px;padding:2px 7px;font-size:10px;color:var(--t3);letter-spacing:.2px}}
.lb2{{background:var(--bg3);border:1px solid var(--brd);border-radius:4px;padding:2px 6px;font-size:9px;color:var(--t3);opacity:.7}}
.pt{{background:var(--gnbg);color:var(--gn);border-radius:4px;padding:2px 7px;font-size:10px;font-weight:600}}
.ct{{border-radius:4px;padding:2px 7px;font-size:10px;font-weight:500;border:1px solid}}
.pgn{{display:flex;justify-content:center;align-items:center;gap:10px;padding:8px;border-top:1px solid var(--brd);flex-shrink:0;background:var(--bg1)}}
.pgn button{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:6px 16px;color:var(--t);cursor:pointer;font-size:13px;transition:all .2s}}
.pgn button:hover:not(:disabled){{border-color:var(--ac);color:var(--ac);box-shadow:var(--glow)}}.pgn button:disabled{{opacity:.3;cursor:default}}.pgn .pi{{color:var(--t3);font-size:11px}}
.rp{{flex:1;display:flex;flex-direction:column;overflow:hidden}}
.re{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--t3);font-size:14px;text-align:center;line-height:2.2}}
.rh{{padding:18px 24px;border-bottom:1px solid var(--brd);flex-shrink:0;animation:fadeUp .25s}}
.rs{{font-size:18px;font-weight:700;color:var(--t);margin-bottom:12px;line-height:1.35}}
.rm{{display:grid;grid-template-columns:55px 1fr;gap:3px 10px;font-size:12px}}
.rm .k{{color:var(--t3);text-align:right}}.rm .v{{color:var(--t2);word-break:break-all}}
.rlbs{{padding:6px 20px;border-bottom:1px solid var(--brd);display:flex;flex-wrap:wrap;gap:4px;flex-shrink:0}}
.rlbs .rlb{{padding:2px 8px;background:var(--bg3);border:1px solid var(--brd);border-radius:4px;font-size:11px;color:var(--t2)}}
.rpj{{padding:10px 20px;border-bottom:1px solid var(--brd);display:flex;flex-wrap:wrap;gap:6px;flex-shrink:0}}
.rpj .pjit{{display:flex;align-items:center;gap:6px;padding:6px 12px;background:var(--bg2);border:1px solid var(--brd);border-radius:8px;color:var(--t);font-size:12px;transition:all .2s;text-decoration:none}}
.rpj a.pjit{{cursor:pointer}}
.rpj a.pjit:hover{{border-color:var(--ac);box-shadow:var(--glow);color:var(--ac)}}
.rpj span.pjit:hover{{border-color:var(--brd)}}
.rb{{flex:1;overflow-y:auto;padding:20px 24px}}
.rb pre{{color:var(--t2);font-size:13px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word;font-family:'Segoe UI',system-ui,sans-serif}}
.rb .emp{{color:var(--t3);font-style:italic}}
.kh{{position:fixed;bottom:6px;left:8px;color:var(--t3);font-size:10px;opacity:.35}}
.foot{{position:fixed;bottom:6px;right:8px;color:var(--t3);font-size:10px;opacity:.35}}

/* THREAD */
.thb2{{background:#2A1F3E;color:#CE93D8;border-radius:3px;padding:1px 6px;font-size:10px;font-weight:600;cursor:pointer}}
body.light .thb2{{background:#F3E5F5;color:#8E24AA}}
.tv{{flex:1;overflow-y:auto;padding:12px 20px}}
.tm{{background:var(--bg2);border:1px solid var(--brd);border-radius:10px;margin-bottom:8px;overflow:hidden;transition:all .2s;box-shadow:var(--shadow);animation:fadeUp .3s backwards}}
.tm:hover{{box-shadow:var(--glow)}}
.tm.cur{{border-color:var(--ac)}}
.tmh{{display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:pointer;transition:background .15s}}
.tmh:hover{{background:var(--bg3)}}
.tmh .tma{{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;flex-shrink:0}}
.tmh .tmi{{flex:1;min-width:0}}
.tmh .tmf{{font-size:12px;font-weight:600;color:var(--t)}}
.tmh .tmd{{font-size:11px;color:var(--t3);margin-left:auto;white-space:nowrap;font-variant-numeric:tabular-nums}}
.tmh .tms{{font-size:11px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tmh .arr{{color:var(--t3);font-size:10px;transition:transform .15s;margin-left:6px}}
.tm.exp .tmh .arr{{transform:rotate(90deg)}}
.tmb{{display:none;padding:0 14px 12px 52px;border-top:1px solid var(--brd)}}
.tm.exp .tmb{{display:block}}
.tmb pre{{color:var(--t2);font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;font-family:'Segoe UI',system-ui,sans-serif;margin-top:8px}}
.tmb .tmpj{{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}}
.tmb .tmpji{{padding:3px 8px;background:var(--bg3);border:1px solid var(--brd);border-radius:4px;font-size:11px;color:var(--t2)}}

/* SELECTION */
.stb{{display:none;gap:8px;align-items:center;padding:6px 16px;background:#1A237E;border-bottom:1px solid #283593;flex-shrink:0}}
body.light .stb{{background:#E8EAF6;border-color:#C5CAE9}}
.stb.on{{display:flex}}
.stb .sc{{color:#90CAF9;font-size:13px;font-weight:600}}
body.light .stb .sc{{color:#1565C0}}
.stb button{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);border-radius:6px;padding:4px 12px;color:#fff;font-size:12px;cursor:pointer;transition:background .15s}}
body.light .stb button{{background:var(--bg2);border-color:var(--brd);color:var(--t)}}
.stb button:hover{{background:rgba(255,255,255,.2)}}
.stb .sep{{flex:1}}
.stb .exp{{background:#2E7D32;border-color:#388E3C}}
.stb .exp:hover{{background:#388E3C}}
.stb .hid{{background:#B71C1C;border-color:#C62828}}
.stb .hid:hover{{background:#C62828}}
.mr .ck{{width:16px;height:16px;accent-color:var(--ac);flex-shrink:0;margin-top:2px;cursor:pointer}}
.mr.sel{{background:#1A237E20}}
body.light .mr.sel{{background:#E8EAF630}}
</style>
</head>
<body>
<div class="hdr">
  <h1 id="logo">&#9993; Gmail Archive</h1>
  <div class="stats">
    <span><b>{nb:,}</b> mails</span>
    <span><b>{total_pj:,}</b> PJ</span>
    <span><b>{len(all_labels)}</b> labels</span>
    <span><b>{date_min}-{date_max}</b></span>
  </div>
  <div class="hdr-r">
    <button class="cmdb" id="stB" title="Statistiques">&#128202;</button>
    <button class="cmdb" id="cmdB" title="Ctrl+K">&#8984; K</button>
    <button class="thb" id="thB" title="Theme">&#9788;</button>
  </div>
</div>
<div class="ctl">
  <div class="sbw"><input type="text" class="sb" id="sI" placeholder="Rechercher..."></div>
  <select id="cF"><option value="">&#128193; Categorie</option></select>
  <select id="yF"><option value="">&#128197; Annee</option></select>
  <select id="lF"><option value="">&#127991; Labels</option></select>
  <select id="fF"><option value="">&#128100; Expediteur</option></select>
  <select id="pF"><option value="">&#128206; PJ</option><option value="y">Avec PJ</option><option value="n">Sans PJ</option></select>
  <select id="dF"><option value="">&#128229; Boite</option><option value="inbox">Recus</option><option value="sent">Envoyes</option><option value="spam">Spam</option><option value="trash">Corbeille</option></select>
  <label class="tgl" id="bsL"><input type="checkbox" id="bS"> &#128196; corps</label>
  <span class="bld" id="bld"></span>
  <span class="cnt" id="cE"></span>
</div>
<div class="stb" id="stbar">
  <span class="sc" id="sCnt">0 selectionne(s)</span>
  <button onclick="selPage()">&#9745; Page</button>
  <button onclick="selAll()">&#9745; Tous (filtre)</button>
  <button onclick="selNone()">&#9746; Aucun</button>
  <span class="sep"></span>
  <button onclick="hideSelected()" class="hid">&#128683; Masquer</button>
  <button class="exp" onclick="exportSel()">&#128190; Exporter HTML</button>
</div>
<div class="dash-ov" id="dashOv">
<div class="dash" id="dash">
  <button class="dash-x" onclick="closeStats()">&times;</button>
  <div class="dash-t">&#128202; Ton archive Gmail<small>{nb:,} mails &middot; {date_min} a {date_max}</small></div>
  <div class="dash-s"><div><b>{nb:,}</b> mails</div><div><b>{total_pj:,}</b> pieces jointes</div><div><b>{len(all_labels)}</b> labels</div><div><b>{threads_multi:,}</b> conversations</div></div>
  <div class="dcs">{dash_cats}</div>
  <div class="dyr"><div class="dyr-t">Mails par annee</div>{dash_years}</div>
  <div class="dss"><div class="dss-t">Top expediteurs</div>{dash_snd}</div>
</div>
</div>
<div class="main" id="mainP">
  <div class="lp"><div class="ls" id="ls"></div><div class="pgn" id="pg"></div></div>
  <div class="rp" id="rp"><div class="re"><div style="font-size:48px;opacity:.3;margin-bottom:12px">&#9993;</div>Selectionne un mail<br><small style="color:var(--t3)">j/k naviguer &middot; / recherche &middot; Ctrl+K commandes &middot; Esc reset</small></div></div>
</div>
<div class="cpo" id="cpo"><div class="cpb"><input class="cpi" id="cpI" placeholder="&#128269; Rechercher label, expediteur, annee, categorie..."><div class="cpr" id="cpR"></div></div></div>
<div class="kh">j/k &middot; / recherche &middot; Ctrl+K commandes &middot; Esc reset</div>
<div class="foot">Genere {now} &middot; TakeoutReader</div>
<script src="mails.js"></script>
<script>
"use strict";
var B=null,BL=false;
var F=[].concat(D),pg=0,pp=100,si=-1;

// === THREAD MAP: tid → [indices in D] sorted by date asc ===
var TH={{}};
(function(){{
for(var i=0;i<D.length;i++){{
  var t=D[i].tid;
  if(!t)continue;
  if(!TH[t])TH[t]=[];
  TH[t].push(i);
}}
// Sort each thread by date ascending (oldest first)
for(var t in TH){{
  if(TH[t].length>1){{
    TH[t].sort(function(a,b){{return D[a].ds<D[b].ds?-1:D[a].ds>D[b].ds?1:0;}});
  }}
}}
}})();
function thLen(m){{var t=m.tid;return(t&&TH[t])?TH[t].length:1;}}

// Pre-index: chaque D[i] porte son index (O(1) au lieu de indexOf O(n))
for(var _i=0;_i<D.length;_i++)D[_i]._di=_i;
function gDi(m){{return(m&&m._di!==undefined)?m._di:-1;}}

// === SELECTION STATE ===
var sel={{}};  // D-index → true (selected)
var hidden={{}}; // D-index → true (hidden)
function updSelBar(){{
var n=Object.keys(sel).length;
sCnt.textContent=n+" selectionne"+(n>1?"s":"");
if(n>0)stbar.classList.add("on");else stbar.classList.remove("on");
}}
function tgSel(fi,ev){{
if(ev)ev.stopPropagation();
var m=F[fi];var di=gDi(m);if(di<0)return;
if(sel[di])delete sel[di];else sel[di]=true;
var row=document.querySelector("[data-i=\\""+fi+"\\"]");
if(row){{var cb=row.querySelector(".ck");if(cb)cb.checked=!!sel[di];row.classList.toggle("sel",!!sel[di]);}}
updSelBar();
}}
function selPage(){{
var s=pg*pp,en=Math.min(s+pp,F.length);
for(var j=s;j<en;j++){{var di=gDi(F[j]);if(di>=0)sel[di]=true;}}
rl();updSelBar();
}}
function selAll(){{
for(var j=0;j<F.length;j++){{var di=gDi(F[j]);if(di>=0)sel[di]=true;}}
rl();updSelBar();
}}
function selNone(){{sel={{}};rl();updSelBar();}}

function hideSelected(){{
var keys=Object.keys(sel);
for(var i=0;i<keys.length;i++)hidden[keys[i]]=true;
sel={{}};af();updSelBar();
}}
function restoreHidden(){{hidden={{}};af();}}

// Export selection as standalone HTML download
function exportSel(){{
var keys=Object.keys(sel);if(!keys.length)return;
var h="<!DOCTYPE html><html lang=\\"fr\\"><head><meta charset=\\"UTF-8\\"><title>Gmail Export - "+keys.length+" mails</title>"
+"<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0A0A0A;color:#E0E0E0;font-family:'Segoe UI',system-ui,sans-serif;padding:20px;max-width:900px;margin:0 auto}}"
+"h1{{font-size:20px;margin-bottom:20px;color:#fff}}"
+".m{{border:1px solid #333;border-radius:8px;margin-bottom:12px;overflow:hidden}}"
+".mh{{background:#111;padding:12px 16px;display:flex;justify-content:space-between;cursor:pointer}}"
+".mh:hover{{background:#1A1A2E}}"
+".mf{{font-weight:600;color:#E0E0E0}}.md{{color:#666;font-size:12px}}"
+".ms{{color:#AAA;font-size:13px;padding:4px 16px 8px}}"
+".mb{{display:none;padding:12px 16px;border-top:1px solid #333;color:#AAA;font-size:13px;white-space:pre-wrap;line-height:1.6}}"
+".m.exp .mb{{display:block}}.m.exp .mh{{border-bottom:1px solid #222}}"
+"</style></head><body>"
+"<h1>Gmail Export &mdash; "+keys.length+" mails</h1>";
keys.sort(function(a,b){{return D[b].ds<D[a].ds?-1:D[b].ds>D[a].ds?1:0;}});
for(var i=0;i<keys.length;i++){{
var di=parseInt(keys[i]);var m=D[di];
var body=(BL&&B&&di>=0)?B[di]:"";
h+="<div class=\\"m\\" onclick=\\"this.classList.toggle('exp')\\">"
+"<div class=\\"mh\\"><span class=\\"mf\\">"+esc(m.f)+" &mdash; "+esc(m.s)+"</span><span class=\\"md\\">"+esc(m.d)+"</span></div>"
+"<div class=\\"ms\\">A: "+esc(m.to)+"</div>"
+"<div class=\\"mb\\">"+esc(body)+"</div></div>";
}}
h+="</body></html>";
var blob=new Blob([h],{{type:"text/html;charset=utf-8"}});
var url=URL.createObjectURL(blob);
var a=document.createElement("a");
a.href=url;a.download="gmail_export_"+keys.length+"_mails.html";
document.body.appendChild(a);a.click();document.body.removeChild(a);
URL.revokeObjectURL(url);
}}
var ls=document.getElementById("ls"),pgD=document.getElementById("pg"),
rp=document.getElementById("rp"),sI=document.getElementById("sI"),
lF=document.getElementById("lF"),pF=document.getElementById("pF"),
yF=document.getElementById("yF"),fF=document.getElementById("fF"),
cF=document.getElementById("cF"),
dF=document.getElementById("dF"),
bS=document.getElementById("bS"),bsL=document.getElementById("bsL"),
bld=document.getElementById("bld"),
cE=document.getElementById("cE"),
thB=document.getElementById("thB"),cmdB=document.getElementById("cmdB"),
stB=document.getElementById("stB"),
stbar=document.getElementById("stbar"),sCnt=document.getElementById("sCnt"),
dashOv=document.getElementById("dashOv"),
mainP=document.getElementById("mainP"),
cpo=document.getElementById("cpo"),cpI=document.getElementById("cpI"),
cpR=document.getElementById("cpR");

// === LAZY LOAD BODIES ===
bsL.classList.add("dis");
bld.textContent="chargement corps...";
var bScript=document.createElement("script");
bScript.src="bodies.js";
bScript.onload=function(){{BL=true;bsL.classList.remove("dis");bld.textContent="corps charge";setTimeout(function(){{bld.textContent="";}},3000);}};
bScript.onerror=function(){{bld.textContent="corps indisponible";}};
document.body.appendChild(bScript);

var catC={{"Perso":"#4FC3F7","Achats":"#FFB74D","Banque":"#81C784","Newsletter":"#BA68C8","Notif":"#90A4AE","Social":"#F06292"}};
thB.addEventListener("click",function(){{document.body.classList.toggle("light");thB.innerHTML=document.body.classList.contains("light")?"&#9789;":"&#9788;";}});
function avH(s){{var h=0;for(var i=0;i<s.length;i++){{h=s.charCodeAt(i)+((h<<5)-h);}}return Math.abs(h)%360;}}
function avI(n){{if(!n)return"?";var p=n.trim().split(/\\s+/);if(p.length>=2)return(p[0][0]+p[1][0]).toUpperCase();return n.substring(0,Math.min(2,n.length)).toUpperCase();}}

// Dropdowns
var ccnt={{}};D.forEach(function(m){{ccnt[m.cat]=(ccnt[m.cat]||0)+1;}});
["Perso","Achats","Banque","Newsletter","Notif","Social"].forEach(function(c){{if(!ccnt[c])return;var o=document.createElement("option");o.value=c;o.textContent=c+" ("+ccnt[c]+")";cF.appendChild(o);}});
var lc={{}};D.forEach(function(m){{var arr=m.labels||[m.l];for(var i=0;i<arr.length;i++){{lc[arr[i]]=(lc[arr[i]]||0)+1;}}}});
Object.keys(lc).sort().forEach(function(l){{var o=document.createElement("option");o.value=l;o.textContent=l+" ("+lc[l]+")";lF.appendChild(o);}});
var yrs={{}};D.forEach(function(m){{var y=m.ds.substring(0,4);if(y!=="0000")yrs[y]=(yrs[y]||0)+1;}});
Object.keys(yrs).sort().reverse().forEach(function(y){{var o=document.createElement("option");o.value=y;o.textContent=y+" ("+yrs[y]+")";yF.appendChild(o);}});
var sndC={{}};D.forEach(function(m){{sndC[m.f]=(sndC[m.f]||0)+1;}});
var top30=Object.keys(sndC).sort(function(a,b){{return sndC[b]-sndC[a];}}).slice(0,30);
top30.forEach(function(s){{var o=document.createElement("option");o.value=s;o.textContent=s+" ("+sndC[s]+")";fF.appendChild(o);}});

function esc(s){{var d=document.createElement("div");d.textContent=s;return d.innerHTML;}}
function cpTxt(text,btn){{if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(text).then(function(){{cpOk(btn);}}).catch(function(){{cpFb(text,btn);}});}}else{{cpFb(text,btn);}}}}
function cpFb(text,btn){{var ta=document.createElement("textarea");ta.value=text;ta.style.cssText="position:fixed;left:-9999px";document.body.appendChild(ta);ta.select();try{{document.execCommand("copy");cpOk(btn);}}catch(e){{btn.textContent="Echec";}}document.body.removeChild(ta);}}
function cpOk(btn){{var orig=btn.getAttribute("data-label")||btn.textContent;btn.textContent="Copie !";setTimeout(function(){{btn.textContent=orig;}},1500);}}

// Stats modal open/close
function openStats(){{dashOv.classList.add("on");}}
function closeStats(){{dashOv.classList.remove("on");}}
stB.addEventListener("click",openStats);
dashOv.addEventListener("click",function(ev){{if(ev.target===dashOv)closeStats();}});
function dCat(c){{closeStats();cF.value=c;af();sI.focus();}}
function dYr(y){{closeStats();yF.value=y;af();sI.focus();}}
function dSnd(s){{closeStats();fF.value=s;af();sI.focus();}}

// Command palette
var cpSel=0,cpItems=[];
function buildPaletteItems(){{
cpItems=[];
cpItems.push({{t:"&#128202; Statistiques",k:"dashboard stats statistiques",fn:function(){{closePalette();openStats();}}}});
cpItems.push({{t:"&#128270; Reset filtres",k:"reset filtres tous browse",fn:function(){{closePalette();cF.value="";yF.value="";fF.value="";lF.value="";pF.value="";dF.value="";sI.value="";bS.checked=false;af();}}}});
["Perso","Achats","Banque","Newsletter","Notif","Social"].forEach(function(c){{if(!ccnt[c])return;cpItems.push({{t:"&#128193; "+c+" ("+ccnt[c]+")",k:"categorie "+c.toLowerCase(),fn:function(){{closePalette();cF.value=c;yF.value="";fF.value="";lF.value="";pF.value="";sI.value="";af();}}}});}});
Object.keys(yrs).sort().reverse().forEach(function(y){{cpItems.push({{t:"&#128197; "+y+" ("+yrs[y]+")",k:"annee "+y,fn:function(){{closePalette();yF.value=y;af();}}}});}});
top30.slice(0,15).forEach(function(s){{cpItems.push({{t:"&#128100; "+s+" ("+sndC[s]+")",k:"expediteur "+s.toLowerCase(),fn:function(){{closePalette();fF.value=s;af();}}}});}});
Object.keys(lc).sort().forEach(function(l){{cpItems.push({{t:"&#127991; "+l+" ("+lc[l]+")",k:"label "+l.toLowerCase(),fn:function(){{closePalette();lF.value=l;af();}}}});}});
cpItems.push({{t:"&#9728; Theme clair",k:"theme light clair",fn:function(){{closePalette();document.body.classList.add("light");thB.innerHTML="&#9789;";}}}});
cpItems.push({{t:"&#9790; Theme sombre",k:"theme dark sombre",fn:function(){{closePalette();document.body.classList.remove("light");thB.innerHTML="&#9788;";}}}});
cpItems.push({{t:"&#128206; Avec PJ uniquement",k:"pieces jointes attachments",fn:function(){{closePalette();pF.value="y";af();}}}});
cpItems.push({{t:"&#9850; Restaurer masques",k:"restaurer masques hidden",fn:function(){{closePalette();restoreHidden();}}}});
cpItems.push({{t:"&#128229; Mails recus",k:"recus inbox boite reception",fn:function(){{closePalette();dF.value="inbox";af();}}}});
cpItems.push({{t:"&#128228; Mails envoyes",k:"envoyes sent",fn:function(){{closePalette();dF.value="sent";af();}}}});
cpItems.push({{t:"&#128165; Voir spam",k:"spam junk",fn:function(){{closePalette();dF.value="spam";af();}}}});
cpItems.push({{t:"&#128465; Voir corbeille",k:"corbeille trash poubelle",fn:function(){{closePalette();dF.value="trash";af();}}}});
}}
buildPaletteItems();
function openPalette(){{cpo.classList.add("on");cpI.value="";cpSel=0;renderPalette("");cpI.focus();}}
function closePalette(){{cpo.classList.remove("on");cpI.blur();}}
function renderPalette(q){{
var fl=cpItems;
if(q){{var ws=q.toLowerCase().split(/\\s+/);fl=cpItems.filter(function(it){{for(var i=0;i<ws.length;i++)if(it.k.indexOf(ws[i])===-1)return false;return true;}});}}
if(cpSel>=fl.length)cpSel=Math.max(0,fl.length-1);
var h="";for(var i=0;i<Math.min(fl.length,12);i++){{var cls=i===cpSel?"cpri sel":"cpri";h+="<div class=\\""+cls+"\\" data-pi=\\""+i+"\\">"+fl[i].t+"</div>";}}
if(!fl.length)h="<div class=\\"cpri\\" style=\\"color:var(--t3)\\">Aucun resultat</div>";
cpR.innerHTML=h;
var els=cpR.querySelectorAll("[data-pi]");for(var i=0;i<els.length;i++){{(function(idx){{els[idx].addEventListener("click",function(){{
var f2=cpItems;if(cpI.value){{var ws2=cpI.value.toLowerCase().split(/\\s+/);f2=cpItems.filter(function(it){{for(var j=0;j<ws2.length;j++)if(it.k.indexOf(ws2[j])===-1)return false;return true;}});}}
if(f2[idx])f2[idx].fn();}});}})( i);}}
return fl;}}
cpI.addEventListener("input",function(){{cpSel=0;renderPalette(cpI.value);}});
cpI.addEventListener("keydown",function(ev){{
var q=cpI.value;var fl=cpItems;
if(q){{var ws=q.toLowerCase().split(/\\s+/);fl=cpItems.filter(function(it){{for(var i=0;i<ws.length;i++)if(it.k.indexOf(ws[i])===-1)return false;return true;}});}}
if(ev.key==="ArrowDown"){{ev.preventDefault();cpSel=Math.min(cpSel+1,Math.min(fl.length-1,11));renderPalette(q);}}
else if(ev.key==="ArrowUp"){{ev.preventDefault();cpSel=Math.max(cpSel-1,0);renderPalette(q);}}
else if(ev.key==="Enter"){{ev.preventDefault();if(fl[cpSel])fl[cpSel].fn();}}
else if(ev.key==="Escape"){{ev.preventDefault();closePalette();}}}});
cpo.addEventListener("click",function(ev){{if(ev.target===cpo)closePalette();}});
cmdB.addEventListener("click",openPalette);

// Filter
function af(){{
sel={{}};updSelBar();
var q=sI.value.toLowerCase().trim(),lb=lF.value,pj=pF.value,yr=yF.value,sn=fF.value,ct=cF.value,dr=dF.value,deep=bS.checked&&BL;
var ws=q?q.split(/\\s+/):[];
F=D.filter(function(m){{
var di=m._di;if(hidden[di])return false;
// Direction filter: inbox=hide spam+trash, sent/spam/trash=show only that
if(dr==="inbox"&&(m.spam||m.trash))return false;
if(dr==="sent"&&!m.sent)return false;
if(dr==="spam"&&!m.spam)return false;
if(dr==="trash"&&!m.trash)return false;
// Default (no filter): hide spam+trash
if(!dr&&(m.spam||m.trash))return false;
if(yr&&m.ds.substring(0,4)!==yr)return false;
if(ct&&m.cat!==ct)return false;
if(lb){{var arr=m.labels||[m.l];var found=false;for(var i=0;i<arr.length;i++){{if(arr[i]===lb){{found=true;break;}}}}if(!found)return false;}}
if(sn&&m.f!==sn)return false;
if(pj==="y"&&m.p===0)return false;
if(pj==="n"&&m.p>0)return false;
if(q){{
var labs=(m.labels||[m.l]).join(" ");
var h=(m.d+" "+m.f+" "+m.s+" "+labs+" "+(m.cat||"")).toLowerCase();
if(deep){{if(di>=0&&B&&B[di])h+=" "+B[di].toLowerCase();}}
for(var i=0;i<ws.length;i++)if(h.indexOf(ws[i])===-1)return false;}}
return true;}});
pg=0;si=-1;rl();}}

// Render list
function rl(){{
var s=pg*pp,en=Math.min(s+pp,F.length),sl=F.slice(s,en);
var h="";
for(var j=0;j<sl.length;j++){{
var m=sl[j],idx=s+j;
var di=gDi(m);var isSel=!!sel[di];
var cls=(idx===si?"mr act":"mr")+(isSel?" sel":"");
var chk=isSel?" checked":"";
var pjt=m.p>0?"<span class=\\"pt\\">"+m.p+" PJ</span>":"";
var thn=thLen(m);var tht=thn>1?"<span class=\\"thb2\\">"+thn+" msgs</span>":"";
var arr=m.labels||[m.l];var lbh="<span class=\\"lb\\">"+esc(arr[0])+"</span>";
if(arr.length>1)lbh+="<span class=\\"lb2\\">+"+String(arr.length-1)+"</span>";
var cc=catC[m.cat]||"#888";var cbt="<span class=\\"ct\\" style=\\"color:"+cc+";border-color:"+cc+"\\">"+esc(m.cat||"")+"</span>";
var hue=avH(m.f);var ini=avI(m.f);
h+="<div class=\\""+cls+"\\" data-i=\\""+idx+"\\" onclick=\\"sm("+idx+")\\">"
+"<input type=\\"checkbox\\" class=\\"ck\\""+chk+" onclick=\\"tgSel("+idx+",event)\\">"
+"<div class=\\"av\\" style=\\"background:hsl("+hue+",42%,55%)\\">"+esc(ini)+"</div>"
+"<div class=\\"mc\\">"
+"<div class=\\"top\\"><span class=\\"frm\\">"+esc(m.f)+"</span><span class=\\"dt\\">"+esc(m.d)+"</span></div>"
+"<div class=\\"su\\">"+esc(m.s)+"</div>"
+(m.sn?"<div class=\\"sn\\">"+esc(m.sn)+"</div>":"")
+"<div class=\\"mt\\">"+cbt+lbh+pjt+tht+"</div>"
+"</div></div>";}}
ls.innerHTML=h;
var hn=Object.keys(hidden).length;
var htxt=hn>0?" <span style=\\"color:var(--ac);cursor:pointer\\" onclick=\\"restoreHidden()\\">"+hn+" masque"+(hn>1?"s":"")+", restaurer</span>":"";
cE.innerHTML=F.length.toLocaleString()+" mail"+(F.length>1?"s":"")+htxt;
var tp=Math.ceil(F.length/pp);
pgD.innerHTML="<button onclick=\\"gp("+(pg-1)+")\\""+( pg<1?" disabled":"")+">&#8592;</button><span class=\\"pi\\">"+(pg+1)+"/"+Math.max(tp,1)+"</span><button onclick=\\"gp("+(pg+1)+")\\""+( pg>=tp-1?" disabled":"")+">&#8594;</button>";}}

function gp(p){{var tp=Math.ceil(F.length/pp);if(p<0||p>=tp)return;pg=p;si=-1;rl();ls.scrollTop=0;}}

// Show mail — thread-aware
function sm(i){{
si=i;
var rows=document.querySelectorAll(".mr");for(var r=0;r<rows.length;r++)rows[r].classList.toggle("act",parseInt(rows[r].dataset.i)===i);
var m=F[i];
var gIdx=m._di;
var tids=(m.tid&&TH[m.tid])?TH[m.tid]:[];
var isThread=tids.length>1;

if(!isThread){{
  // === SINGLE MAIL VIEW ===
  var cc=catC[m.cat]||"#888";
  var h="<div class=\\"rh\\"><div class=\\"rs\\">"+esc(m.s)+"</div><div class=\\"rm\\">"
  +"<span class=\\"k\\">De</span><span class=\\"v\\">"+esc(m.ff)+"</span>"
  +"<span class=\\"k\\">A</span><span class=\\"v\\">"+esc(m.to)+"</span>";
  if(m.cc)h+="<span class=\\"k\\">Cc</span><span class=\\"v\\">"+esc(m.cc)+"</span>";
  h+="<span class=\\"k\\">Date</span><span class=\\"v\\">"+esc(m.d)+"</span>"
  +"<span class=\\"k\\">Cat.</span><span class=\\"v\\" style=\\"color:"+cc+"\\">"+esc(m.cat||"")+"</span>"
  +"</div></div>";
  var arr=m.labels||[m.l];
  if(arr.length>0){{h+="<div class=\\"rlbs\\">";for(var g=0;g<arr.length;g++){{h+="<span class=\\"rlb\\">"+esc(arr[g])+"</span>";}}h+="</div>";}}
  if(m.pj&&m.pj.length>0){{h+="<div class=\\"rpj\\">";for(var p=0;p<m.pj.length;p++){{if(m.pjp&&m.pjp[p]){{h+="<a class=\\"pjit\\" href=\\""+esc(m.pjp[p])+"\\" target=\\"_blank\\">&#128206; "+esc(m.pj[p])+"</a>";}}else{{h+="<span class=\\"pjit\\">&#128206; "+esc(m.pj[p])+"</span>";}}}}h+="</div>";}}
  h+="<div class=\\"rb\\">";
  var body=(BL&&B&&gIdx>=0)?B[gIdx]:"";
  if(body){{h+="<pre>"+esc(body)+"</pre>";}}
  else if(!BL){{h+="<div class=\\"emp\\">Chargement du corps en cours...</div>";}}
  else{{h+="<div class=\\"emp\\">Aucun contenu texte extrait.</div>";}}
  h+="</div>";
  rp.innerHTML=h;
}} else {{
  // === THREAD VIEW (conversation) ===
  var h="<div class=\\"rh\\"><div class=\\"rs\\">"+esc(m.s)+"</div>"
  +"<div style=\\"font-size:12px;color:var(--t3);margin-top:4px\\">"+tids.length+" messages dans cette conversation</div></div>";
  h+="<div class=\\"tv\\">";
  for(var t=0;t<tids.length;t++){{
    var ti=tids[t];var tm=D[ti];
    var isCur=ti===gIdx;
    var cls2=isCur?"tm exp cur":"tm";
    var hue2=avH(tm.f);var ini2=avI(tm.f);
    h+="<div class=\\""+cls2+"\\" data-tm=\\""+t+"\\">"
    +"<div class=\\"tmh\\" onclick=\\"tgTm(this)\\">"
    +"<div class=\\"tma\\" style=\\"background:hsl("+hue2+",42%,55%)\\">"+esc(ini2)+"</div>"
    +"<div class=\\"tmi\\"><div class=\\"tmf\\">"+esc(tm.f)+"</div>"
    +"<div class=\\"tms\\">"+esc(tm.s)+"</div></div>"
    +"<span class=\\"tmd\\">"+esc(tm.d)+"</span>"
    +"<span class=\\"arr\\">&#9654;</span>"
    +"</div>";
    h+="<div class=\\"tmb\\">";
    if(tm.to)h+="<div style=\\"font-size:11px;color:var(--t3);margin-top:6px\\">A: "+esc(tm.to)+"</div>";
    if(tm.pj&&tm.pj.length>0){{
      h+="<div class=\\"tmpj\\">";
      for(var p2=0;p2<tm.pj.length;p2++){{if(tm.pjp&&tm.pjp[p2]){{h+="<a class=\\"tmpji\\" href=\\""+esc(tm.pjp[p2])+"\\" target=\\"_blank\\" style=\\"text-decoration:none;color:var(--t2)\\">&#128206; "+esc(tm.pj[p2])+"</a>";}}else{{h+="<span class=\\"tmpji\\">&#128206; "+esc(tm.pj[p2])+"</span>";}}}}
      h+="</div>";
    }}
    var tbody=(BL&&B&&ti>=0)?B[ti]:"";
    if(tbody){{h+="<pre>"+esc(tbody)+"</pre>";}}
    else if(!BL){{h+="<div class=\\"emp\\">Chargement...</div>";}}
    else{{h+="<div class=\\"emp\\">Aucun contenu texte.</div>";}}
    h+="</div></div>";
  }}
  h+="</div>";
  rp.innerHTML=h;
  // Scroll to current message
  var curEl=rp.querySelector(".tm.cur");
  if(curEl)setTimeout(function(){{curEl.scrollIntoView({{block:"nearest",behavior:"smooth"}});}},50);
}}
}}
// Toggle thread message expand/collapse
function tgTm(el){{
var card=el.parentElement;
card.classList.toggle("exp");
}}

// Keyboard
document.addEventListener("keydown",function(ev){{
if((ev.ctrlKey||ev.metaKey)&&ev.key==="k"){{ev.preventDefault();openPalette();return;}}
if(cpo.classList.contains("on"))return;
if(dashOv.classList.contains("on")){{if(ev.key==="Escape")closeStats();return;}}
if(ev.target.tagName==="INPUT"||ev.target.tagName==="SELECT"){{if(ev.key==="Escape"){{sI.blur();sI.value="";af();}}return;}}
if(ev.key==="ArrowDown"||ev.key==="j"){{ev.preventDefault();if(si<0){{sm(0);}}else if(si<F.length-1){{var np=Math.floor((si+1)/pp);if(np!==pg){{pg=np;rl();}}sm(si+1);}}var el=document.querySelector(".mr.act");if(el)el.scrollIntoView({{block:"nearest"}});}}
else if(ev.key==="ArrowUp"||ev.key==="k"){{ev.preventDefault();if(si>0){{var np2=Math.floor((si-1)/pp);if(np2!==pg){{pg=np2;rl();}}sm(si-1);}}var el2=document.querySelector(".mr.act");if(el2)el2.scrollIntoView({{block:"nearest"}});}}
else if(ev.key==="Escape"){{sI.value="";lF.value="";yF.value="";fF.value="";pF.value="";cF.value="";dF.value="";bS.checked=false;af();}}
else if(ev.key==="/"){{ev.preventDefault();sI.focus();sI.select();}}}});

var st;sI.addEventListener("input",function(){{clearTimeout(st);st=setTimeout(af,200);}});
lF.addEventListener("change",af);pF.addEventListener("change",af);
yF.addEventListener("change",af);fF.addEventListener("change",af);
cF.addEventListener("change",af);dF.addEventListener("change",af);bS.addEventListener("change",af);
af();
</script>
</body>
</html>'''

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    index_size = os.path.getsize(index_path) / (1024 * 1024)
    print(f"    index.html: {index_size:.2f} Mo", flush=True)

    total_size = mails_size + bodies_size + index_size
    return total_size, index_path


# ============================================
# VALIDATION — Protocole Rebouclage Qualite
# ============================================
# Invariants declares : chaque generation verifie que
# toutes les features V1-V9 sont presentes et qu'aucune
# regression connue n'est reapparue.

# Features qui DOIVENT exister dans index.html
MUST_EXIST_HTML = {
    # V1 — Core (var D/B sont dans mails.js/bodies.js, pas dans index.html)
    "function af()": "Filtre principal",
    "function rl()": "Render liste",
    "function sm(": "Affichage mail",
    # V2 — Avatars + Theme
    "avH(": "Avatars couleur",
    "body.light": "Theme clair",
    # V3 — Categories + Command palette
    "openPalette": "Command palette Ctrl+K",
    "catC[": "Couleurs categories",
    "closePalette": "Fermeture palette",
    # V4 — Archi split
    "mails.js": "Chargement mails.js",
    "bodies.js": "Chargement bodies.js",
    # V5 — Threads
    "tgTm": "Toggle thread message",
    "thLen(": "Thread length helper",
    "TH[": "Thread map",
    # V6 — Stats modal
    "openStats": "Ouverture modal stats",
    "closeStats": "Fermeture modal stats",
    "dash-ov": "Overlay modal stats",
    # V7 — Selection + Export
    "tgSel": "Toggle selection",
    "exportSel": "Export selection HTML",
    "selPage": "Selection page",
    "selAll": "Selection tous",
    "hideSelected": "Masquer selection",
    "restoreHidden": "Restaurer masques",
    # V8 — Spam/Sent/Trash + Perf
    "dF": "Filtre direction (boite)",
    "m.spam": "Flag spam",
    "m.trash": "Flag corbeille",
    "m.sent": "Flag envoye",
    "_di": "Pre-index perf",
    # V12 — Violet/Rose palette + icons + animations
    "#B388FF": "Accent violet dark",
    "#E91E63": "Accent rose light",
    "fadeUp": "Animation fadeUp",
    "--glow": "Glow variable",
    "sbw": "Search icon wrapper",
}

# Champs obligatoires dans mails.js (chaque mail doit les avoir)
MUST_EXIST_FIELDS = ("ds", "d", "f", "s", "cat", "tid", "sn", "spam", "trash", "sent")

# Patterns qui ne doivent PLUS exister (regressions connues)
MUST_NOT_EXIST = {
    "goBrowse": "V6 regression: dashboard bloquant",
    "goDash": "V6 regression: dashboard bloquant",
    "viewMode": "V6 regression: mode dashboard",
    "dash-go": "V6 regression: bouton Explorer",
    "D.indexOf": "V8 regression: perf O(n)",
}


def validate_output(output_dir, nb_mails):
    """Validation post-generation : invariants structurels + features + regressions.
    Retourne (pass_count, fail_count, warn_count)."""

    index_path = os.path.join(output_dir, "index.html")
    mails_path = os.path.join(output_dir, "mails.js")
    bodies_path = os.path.join(output_dir, "bodies.js")

    print()
    print("=" * 60)
    print("  VALIDATION — Invariants Rebouclage")
    print("=" * 60)

    passed = 0
    failed = 0
    warned = 0

    # --- 1. Fichiers existent ---
    for fpath, fname in [(index_path, "index.html"), (mails_path, "mails.js"), (bodies_path, "bodies.js")]:
        if os.path.isfile(fpath):
            passed += 1
        else:
            print(f"  [FAIL] Fichier manquant: {fname}")
            failed += 1

    if failed > 0:
        print(f"\n  ABANDON: fichiers manquants")
        return passed, failed, warned

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    with open(mails_path, "r", encoding="utf-8") as f:
        mails_js = f.read()

    # --- 2. MUST_EXIST dans index.html ---
    for pattern, desc in MUST_EXIST_HTML.items():
        if pattern in html:
            passed += 1
        else:
            print(f"  [FAIL] ABSENT: '{pattern}' — {desc}")
            failed += 1

    # --- 3. MUST_NOT_EXIST ---
    for pattern, desc in MUST_NOT_EXIST.items():
        if pattern in html:
            print(f"  [FAIL] REGRESSION: '{pattern}' — {desc}")
            failed += 1
        else:
            passed += 1

    # --- 4. Structurel: JS braces equilibrees ---
    js_start = html.find("<script>", html.find("mails.js"))
    js_end = html.find("</script>", js_start) if js_start >= 0 else -1
    if js_start >= 0 and js_end >= 0:
        js = html[js_start+8:js_end]
        opens = js.count("{")
        closes = js.count("}")
        if opens == closes:
            passed += 1
        else:
            print(f"  [FAIL] JS braces desequilibrees: {opens} ouvrantes / {closes} fermantes")
            failed += 1
    else:
        print(f"  [WARN] Impossible d'extraire le JS principal")
        warned += 1

    # --- 5. mails.js: JSON valide, bon nombre de mails, champs presents ---
    try:
        data = json.loads(mails_js[len("var D="):-2])  # strip "var D=[...];\n"
        if len(data) == nb_mails:
            passed += 1
        else:
            print(f"  [FAIL] mails.js: {len(data)} mails, attendu {nb_mails}")
            failed += 1

        # Check var D= wrapper
        if mails_js.startswith("var D="):
            passed += 1
        else:
            print(f"  [FAIL] mails.js: ne commence pas par 'var D='")
            failed += 1

        # Check champs obligatoires sur premier mail
        first = data[0] if data else {}
        for field in MUST_EXIST_FIELDS:
            if field in first:
                passed += 1
            else:
                print(f"  [FAIL] mails.js: champ '{field}' manquant")
                failed += 1
    except Exception as e:
        print(f"  [FAIL] mails.js: JSON invalide — {e}")
        failed += 1

    # --- 6. bodies.js valide ---
    bodies_path = os.path.join(output_dir, "bodies.js")
    try:
        with open(bodies_path, "r", encoding="utf-8") as f:
            bodies_js = f.read()
        if bodies_js.startswith("var B="):
            passed += 1
        else:
            print(f"  [FAIL] bodies.js: ne commence pas par 'var B='")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] bodies.js: illisible — {e}")
        failed += 1

    # --- 7. Tailles coherentes ---
    html_size = len(html)
    mails_size = len(mails_js)
    if html_size > 10000:
        passed += 1
    else:
        print(f"  [WARN] index.html tres petit: {html_size} chars")
        warned += 1

    if mails_size > 100:
        passed += 1
    else:
        print(f"  [WARN] mails.js tres petit: {mails_size} chars")
        warned += 1

    # --- Bilan ---
    total = passed + failed + warned
    print()
    if failed == 0:
        print(f"  VALIDATION OK — {passed}/{total} checks passed" +
              (f", {warned} warnings" if warned else ""))
    else:
        print(f"  VALIDATION ECHOUEE — {failed} FAIL / {passed} pass / {warned} warn")
        print(f"  -> Corriger les FAIL avant de livrer")

    return passed, failed, warned


def main():
    test_limit, auto_open = parse_args()
    temp_dirs = []

    print()
    print("=" * 60)
    print("  TakeoutReader")
    print("  .mbox / dossier .eml → HTML interactif standalone")
    print("  Multi-source + fusion + deduplication")
    print("  Zero dependance, zero serveur, offline a vie")
    print("=" * 60)

    # [0] Input — auto-detection (retourne liste)
    raw_paths = find_mbox_auto()
    if not raw_paths:
        print("\n  [!] Aucun fichier selectionne. Abandon.")
        return

    # Resolve all inputs (.zip → extract, .mbox/.eml dir → direct)
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
            print(f"  [!] index.html introuvable dans {output_dir} — redirect non cree")
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


if __name__ == "__main__":
    # Log TOUTE la sortie console dans un fichier a cote du script
    _script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    _log_path = os.path.join(_script_dir, "DIAG_execution.log")

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
