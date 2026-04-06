# ============================================
# takeoutreader/core/parser.py
# Parsing .mbox et .eml, deduplication, threading
# ============================================

import mailbox
import os
import re
import time
import html as html_mod
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from datetime import datetime
from collections import Counter

from takeoutreader.core.constants import (
    SNIPPET_CHARS, MIN_PJ_SIZE, SKIP_MIME, EXT_MAP,
    CAT_SOCIAL, CAT_BANQUE, CAT_ACHATS, CAT_NOTIF, CAT_NEWSLETTER,
)
from takeoutreader.core.sanitizer import sanitize_text, decode_hdr


# ============================================
# FONCTIONS UTILITAIRES
# ============================================

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
    """Extrait X-Gmail-Labels -> liste de labels propres"""
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

    # 4. Newsletter -- AVANT Notif si has_unsub
    if has_unsub:
        return "Newsletter"
    for kw in CAT_NEWSLETTER:
        if kw in fr:
            return "Newsletter"

    # 5. Notif/Auto (noreply patterns) -- seulement si PAS has_unsub
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
# PARSE -- SHARED HELPER
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
    mail_data["sent"] = 1 if labels_lower & {"envoy\u00e9s", "sent", "envoy\u00e9s"} else 0
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
        print(f"  PARSE -- {src_name} (fusion)")
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
    print(f"  BILAN PARSE -- {src_name}")
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
        print(f"  PARSE EML -- {src_name} (fusion)")
    else:
        print(f"  PARSE EML -- {src_name}")
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
    print(f"  BILAN PARSE EML -- {src_name}")
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
    print(f"  FUSION MULTI-SOURCE -- {len(source_paths)} sources")
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
        print(f"\n  --- Source {i}/{len(source_paths)} ---")
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
