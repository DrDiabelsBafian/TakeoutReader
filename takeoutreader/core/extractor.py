"""
Attachment extraction to disk.

Re-reads source files (.mbox or .eml) to pull out binary attachments
for mails that were flagged during parsing. This two-pass approach keeps
the parser fast (no disk I/O on first pass) while still extracting
everything we need.
"""

from __future__ import annotations

import os
import time
import logging
import mailbox
from collections import defaultdict
from email import policy
from email.parser import BytesParser
from typing import Any

from takeoutreader.core.constants import MIN_PJ_SIZE, SKIP_MIME, EXT_MAP
from takeoutreader.core.sanitizer import decode_hdr

log = logging.getLogger(__name__)

MailDict = dict[str, Any]


def _sanitize_pj_filename(name: str) -> str:
    """Clean up an attachment filename for safe writing to disk.

    Strips characters that Windows/macOS/Linux disallow in filenames,
    and truncates absurdly long names (looking at you, Outlook).
    """
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


def _extract_pj_from_message(msg: mailbox.mboxMessage) -> list[tuple[str, bytes]]:
    """Extract binary attachments from a single message.

    Returns:
        List of (filename, raw_bytes) tuples.
    """
    pj_files: list[tuple[str, bytes]] = []
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


def _write_attachment(
    mail_pj_dir: str, name: str, data: bytes, mail_idx: int,
) -> tuple[str, int]:
    """Write a single attachment to disk, handling filename collisions.

    Returns:
        Tuple of (relative_path, bytes_written).
    """
    os.makedirs(mail_pj_dir, exist_ok=True)
    filepath = os.path.join(mail_pj_dir, name)

    # Handle duplicate filenames within the same mail
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
    return rel_path, len(data)


def extract_pj_to_disk(
    mails: list[MailDict], output_dir: str,
) -> tuple[int, int]:
    """Extract all attachments to output_dir/pj/.

    Updates each mail's ``pjp`` field with relative paths to the extracted
    files. Handles both .eml and .mbox sources — .mbox requires a second
    pass through the file since we can't keep all payloads in memory.

    Args:
        mails: List of parsed mail dicts (modified in place).
        output_dir: Root output directory.

    Returns:
        Tuple of (files_extracted, total_bytes).
    """
    mails_with_pj = [
        (i, m) for i, m in enumerate(mails)
        if m.get("p", 0) > 0 and m.get("_src")
    ]

    if not mails_with_pj:
        print("    No attachments to extract")
        return 0, 0

    pj_dir = os.path.join(output_dir, "pj")
    os.makedirs(pj_dir, exist_ok=True)

    print(f"  [PJ] Extracting from {len(mails_with_pj):,} mails with attachments...", flush=True)

    # Split by source type — .eml can be read individually, .mbox needs
    # a full re-read (grouped by file to avoid reading the same mbox N times)
    eml_mails = [(i, m) for i, m in mails_with_pj if m.get("_src_type") == "eml"]
    mbox_groups: dict[str, list[tuple[int, MailDict]]] = defaultdict(list)
    for i, m in mails_with_pj:
        if m.get("_src_type") == "mbox":
            mbox_groups[m["_src"]].append((i, m))

    nb_extracted = 0
    total_bytes = 0
    erreurs = 0
    start = time.time()

    parser = BytesParser(policy=policy.default)

    # --- .eml files: read each one individually ---
    for idx_done, (mail_idx, m) in enumerate(eml_mails):
        if (idx_done + 1) % 500 == 0:
            elapsed = time.time() - start
            print(f"    ... {idx_done+1:,}/{len(eml_mails):,} eml | "
                  f"{nb_extracted:,} files | {elapsed:.0f}s", flush=True)

        try:
            with open(m["_src"], "rb") as f:
                msg = parser.parsebytes(f.read())

            pj_files = _extract_pj_from_message(msg)
            pjp: list[str] = []

            if pj_files:
                mail_pj_dir = os.path.join(pj_dir, f"{mail_idx:05d}")
                for name, data in pj_files:
                    rel_path, sz = _write_attachment(mail_pj_dir, name, data, mail_idx)
                    pjp.append(rel_path)
                    nb_extracted += 1
                    total_bytes += sz

            m["pjp"] = pjp

        except Exception as e:
            erreurs += 1
            if erreurs <= 10:
                log.warning("Attachment extraction error: %s", e)
                print(f"    [!] PJ error: {e}")

    # --- .mbox files: re-read and match by Message-ID ---
    for mbox_path, mail_list in mbox_groups.items():
        if not os.path.isfile(mbox_path):
            continue

        mid_to_mail: dict[str, tuple[int, MailDict]] = {}
        for mail_idx, m in mail_list:
            mid = m.get("_mid", "")
            if mid:
                mid_to_mail[mid] = (mail_idx, m)

        if not mid_to_mail:
            continue

        print(f"    [PJ/MBOX] Re-reading {os.path.basename(mbox_path)} "
              f"for {len(mid_to_mail):,} mails...", flush=True)

        mbox = mailbox.mbox(mbox_path, factory=lambda f: parser.parse(f))
        found = 0

        for message in mbox:
            if not mid_to_mail:
                break  # found everything we need, stop early

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
                    for name, data in pj_files:
                        rel_path, sz = _write_attachment(mail_pj_dir, name, data, mail_idx)
                        pjp.append(rel_path)
                        nb_extracted += 1
                        total_bytes += sz

                m["pjp"] = pjp

            except Exception as e:
                erreurs += 1

        print(f"    [PJ/MBOX] {found:,} mails matched, attachments extracted")

    elapsed = time.time() - start
    print(f"  [PJ] {nb_extracted:,} files extracted "
          f"({total_bytes / (1024**2):.1f} MB) in {elapsed:.0f}s"
          + (f", {erreurs} errors" if erreurs else ""))

    return nb_extracted, total_bytes
