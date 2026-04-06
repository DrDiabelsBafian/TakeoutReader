# ============================================
# takeoutreader/core/extractor.py
# Extraction des pieces jointes sur disque
# ============================================

import os
import time
import mailbox
from collections import defaultdict
from email import policy
from email.parser import BytesParser

from takeoutreader.core.constants import MIN_PJ_SIZE, SKIP_MIME, EXT_MAP
from takeoutreader.core.sanitizer import decode_hdr


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

    # --- EML files ---
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
                print(f"    [!] PJ erreur: {e}")

    # --- MBOX files (re-lecture pour extraction) ---
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
