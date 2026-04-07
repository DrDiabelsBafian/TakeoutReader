"""
Email parsing engine for .mbox and .eml sources.

Handles the full pipeline: read -> decode headers -> extract body -> list
attachments -> deduplicate by Message-ID -> reconstruct Gmail threads ->
auto-categorize. Tested against 19,000+ real-world Gmail exports spanning
15 years of format variations.
"""

from __future__ import annotations

import mailbox
import os
import re
import time
import logging
import html as html_mod
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from datetime import datetime
from collections import Counter
from typing import Any

from takeoutreader.core.constants import (
    SNIPPET_CHARS, MIN_PJ_SIZE, SKIP_MIME, EXT_MAP,
    CAT_SOCIAL, CAT_BANQUE, CAT_ACHATS, CAT_NOTIF, CAT_NEWSLETTER,
)
from takeoutreader.core.sanitizer import sanitize_text, decode_hdr

log = logging.getLogger(__name__)

# Type alias for the mail dict that flows through the whole pipeline
MailDict = dict[str, Any]


def get_date(msg: mailbox.mboxMessage) -> tuple[str, str]:
    """Extract a usable date from an email message.

    Tries the Date header first, falls back to Received. Gmail is generally
    well-behaved, but forwarded corporate emails can have truly bizarre
    date formats (e.g. two-digit years, missing timezones).

    Returns:
        Tuple of (sortable "YYYY-MM-DD HH:MM:SS", display "DD/MM/YYYY HH:MM").
        Falls back to ("0000-00-00", "") if nothing works.
    """
    for hdr in ("Date", "Received"):
        raw = msg.get(hdr, "")
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            loc = datetime.fromtimestamp(dt.timestamp())
            return loc.strftime("%Y-%m-%d %H:%M:%S"), loc.strftime("%d/%m/%Y %H:%M")
        except Exception:
            # Gmail sometimes wraps dates in weird whitespace or comments.
            # Try to fish out something that looks like a date.
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


def extract_body_text(msg: mailbox.mboxMessage) -> str:
    """Extract the readable body from an email message.

    Prefers text/plain over text/html. If only HTML is available, strips
    tags and does a best-effort conversion to plain text. Caps output at
    50K chars to avoid blowing up memory on giant newsletters.

    Returns:
        Plain text body, or empty string if nothing could be extracted.
    """
    text = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if part.get_filename():
                continue  # it's an attachment, not the body
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
        return text[:50000]

    if html_body:
        # Quick and dirty HTML-to-text. Not perfect, but good enough for
        # search snippets and body preview. A real converter like html2text
        # would be overkill here since we also show the raw HTML in the viewer.
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


def extract_pj_list(msg: mailbox.mboxMessage) -> list[str]:
    """List attachments in a message (name + size) without writing to disk.

    This is the fast path used during parsing — actual extraction to disk
    happens later in extractor.py, only for mails that have attachments.

    Returns:
        List of "filename (size)" strings.
    """
    pj_list: list[str] = []
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


def parse_gmail_labels(msg: mailbox.mboxMessage) -> list[str]:
    """Extract Gmail labels from the X-Gmail-Labels header.

    Gmail Takeout exports include this non-standard header. If absent
    (e.g. non-Gmail .eml files), defaults to ["Autres"].
    """
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


def categorize_mail(mail_data: MailDict, has_unsub: bool = False) -> str:
    """Classify a mail into one of 6 categories using keyword heuristics.

    Categories: Perso, Achats, Banque, Newsletter, Notif, Social.
    The logic checks From + Subject against known keywords, with Gmail
    labels as a secondary signal. Not ML — just pattern matching that
    works well enough for the 90% case.

    Args:
        mail_data: Parsed mail dict with 'ff' (full from) and 's' (subject).
        has_unsub: Whether the mail has a List-Unsubscribe header.

    Returns:
        Category string.
    """
    fr = (mail_data.get("ff", "") or "").lower()
    subj = (mail_data.get("s", "") or "").lower()
    haystack = fr + " " + subj
    labels_lower = [lb.lower() for lb in mail_data.get("labels", [])]

    # Check order matters — social domains are very specific, check first
    for kw in CAT_SOCIAL:
        if kw in fr:
            return "Social"

    for kw in CAT_BANQUE:
        if kw in haystack:
            return "Banque"

    for kw in CAT_ACHATS:
        if kw in haystack:
            return "Achats"

    # List-Unsubscribe is a strong newsletter signal — check before noreply
    if has_unsub:
        return "Newsletter"
    for kw in CAT_NEWSLETTER:
        if kw in fr:
            return "Newsletter"

    # noreply patterns — only if it doesn't have List-Unsubscribe
    for kw in CAT_NOTIF:
        if kw in fr:
            return "Notif"

    # Gmail label hints as fallback
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


def _build_mail_dict(message: mailbox.mboxMessage) -> tuple[MailDict, str, list[str], bool] | None:
    """Transform a raw email message into our standardized dict format.

    This is the heart of the parser — every mail passes through here.
    Returns None if the message is too broken to process.

    Returns:
        Tuple of (mail_data, msg_id, labels, used_gmail_thread_id), or None.
    """
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

    # Thread reconstruction: prefer Gmail's X-GM-THRID (globally unique),
    # fall back to References/In-Reply-To, then Message-ID as last resort
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
            tid = refs_ids[0]  # first reference = thread root
        elif inreply and inreply.strip():
            tid = inreply.strip()
        else:
            tid = msg_id or ""

    # Build search snippet from body (stripped of HTML remnants)
    snippet = ""
    if body:
        snippet = body[:SNIPPET_CHARS].replace("\r", " ").replace("\n", " ")
        snippet = re.sub(r'<[^>]+>', '', snippet)
        snippet = html_mod.unescape(snippet)
        snippet = re.sub(r' +', ' ', snippet).strip()

    mail_data: MailDict = {
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

    # Gmail-specific flags derived from label names
    labels_lower = {lb.lower() for lb in labels}
    mail_data["spam"] = 1 if labels_lower & {"spam", "junk"} else 0
    mail_data["trash"] = 1 if labels_lower & {"corbeille", "trash"} else 0
    mail_data["sent"] = 1 if labels_lower & {"envoy\u00e9s", "sent"} else 0
    mail_data["_mid"] = msg_id  # kept for attachment extraction, stripped before JSON

    return mail_data, msg_id, labels, gm_thrid_used


def parse_mbox(
    mbox_path: str,
    test_limit: int = 0,
    seen_ids: dict[str, int] | None = None,
    existing_mails: list[MailDict] | None = None,
) -> tuple[list[MailDict], dict[str, int]]:
    """Parse a .mbox file and deduplicate by Message-ID.

    When ``seen_ids`` and ``existing_mails`` are provided, performs
    cross-file deduplication (useful when merging multiple exports).

    Args:
        mbox_path: Path to the .mbox file.
        test_limit: Stop after N mails (0 = no limit). Dev/debug only.
        seen_ids: Shared Message-ID -> index map for cross-file dedup.
        existing_mails: Shared mail list to append to.

    Returns:
        Tuple of (mails, seen_ids).
    """
    if not os.path.isfile(mbox_path):
        print(f"\n  [ERROR] File not found: {mbox_path}")
        return existing_mails or [], seen_ids or {}

    if seen_ids is None:
        seen_ids = {}
    mails = existing_mails if existing_mails is not None else []
    cross_file = len(mails) > 0

    file_size = os.path.getsize(mbox_path)

    print()
    print("=" * 60)
    src_name = os.path.basename(mbox_path)
    if cross_file:
        print(f"  PARSE -- {src_name} (merging)")
    else:
        print(f"  TakeoutReader -- PARSE")
    print("=" * 60)
    print(f"  Source  : {mbox_path}")
    print(f"  Size    : {file_size / (1024**3):.2f} GB")
    print(f"  Body    : full (snippet {SNIPPET_CHARS} chars in list)")
    if cross_file:
        print(f"  Existing: {len(mails):,} mails in memory ({len(seen_ids):,} IDs)")
    if test_limit:
        print(f"  TEST    : {test_limit} mails max")
    print("=" * 60)
    print()

    parser = BytesParser(policy=policy.default)
    mbox = mailbox.mbox(mbox_path, factory=lambda f: parser.parse(f))

    start = time.time()
    mails_before = len(mails)
    total_raw = 0
    dupes = 0
    erreurs = 0
    gm_thrid_count = 0

    for message in mbox:
        total_raw += 1

        if test_limit and total_raw > test_limit:
            break

        # Progress with ETA every 500 mails
        if total_raw % 500 == 0:
            elapsed = time.time() - start
            speed = total_raw / elapsed if elapsed > 0 else 0
            avg_mail_size = file_size / total_raw if total_raw > 0 else 40000
            est_total = int(file_size / avg_mail_size) if avg_mail_size > 0 else 0
            remaining = max(0, est_total - total_raw)
            eta_s = remaining / speed if speed > 0 else 0
            eta_str = f"~{eta_s:.0f}s" if eta_s < 120 else f"~{eta_s/60:.0f}min"

            print(f"  ... {total_raw:,} read | {len(mails):,} unique | "
                  f"{dupes:,} dupes | {elapsed:.0f}s | {speed:.0f}/s | ETA {eta_str}",
                  flush=True)

        try:
            result = _build_mail_dict(message)
            if result is None:
                erreurs += 1
                continue

            mail_data, msg_id, labels, gm_used = result
            if gm_used:
                gm_thrid_count += 1

            # Deduplication: if we've seen this ID, merge labels instead of adding
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
                log.warning("Error on mail #%d: %s", total_raw, e)
                print(f"  [!] Error mail #{total_raw}: {e}")

    elapsed = time.time() - start
    mails_added = len(mails) - mails_before
    mails.sort(key=lambda m: m["ds"], reverse=True)

    # Stats
    all_labels: Counter[str] = Counter()
    for m in mails:
        for lb in m["labels"]:
            all_labels[lb] += 1

    cat_stats = Counter(m["cat"] for m in mails)
    thread_ids = Counter(m["tid"] for m in mails if m["tid"])
    threads_multi = sum(1 for c in thread_ids.values() if c > 1)

    print()
    print("=" * 60)
    print(f"  RESULTS -- {src_name}")
    print("=" * 60)
    print(f"  Raw messages        : {total_raw:,}")
    print(f"  Duplicates removed  : {dupes:,}")
    print(f"  New mails added     : {mails_added:,}")
    if cross_file:
        print(f"  TOTAL (cumulative)  : {len(mails):,}")
    else:
        print(f"  Unique mails        : {len(mails):,}")
    print(f"  With attachments    : {sum(1 for m in mails if m['p'] > 0):,}")
    print(f"  Distinct labels     : {len(all_labels)}")
    print(f"  Threads (multi-msg) : {threads_multi:,}")
    print(f"  X-GM-THRID (Gmail)  : {gm_thrid_count:,}/{mails_added:,} ({gm_thrid_count*100//max(mails_added,1)}%)")
    spam_count = sum(1 for m in mails if m.get("spam"))
    trash_count = sum(1 for m in mails if m.get("trash"))
    sent_count = sum(1 for m in mails if m.get("sent"))
    print(f"  Spam                : {spam_count:,}")
    print(f"  Trash               : {trash_count:,}")
    print(f"  Sent                : {sent_count:,}")
    print(f"  Errors              : {erreurs}")
    print(f"  Duration            : {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print()
    if not cross_file and cat_stats:
        print("  Auto-categories:")
        for cat, count in cat_stats.most_common():
            pct = count * 100 / len(mails) if mails else 0
            print(f"    {cat:15s} : {count:,} ({pct:.0f}%)")
        print()
    if not cross_file and all_labels:
        print("  Top 15 labels:")
        for lb, count in all_labels.most_common(15):
            print(f"    {lb:30s} : {count:,}")
    print("=" * 60)

    return mails, seen_ids


def _find_all_eml(root: str) -> list[str]:
    """Recursively find all .eml files under a directory."""
    eml = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".eml"):
                eml.append(os.path.join(dp, fn))
    return sorted(eml)


def parse_eml_folder(
    folder_path: str,
    test_limit: int = 0,
    seen_ids: dict[str, int] | None = None,
    existing_mails: list[MailDict] | None = None,
) -> tuple[list[MailDict], dict[str, int]]:
    """Parse a folder of .eml files. Same interface as parse_mbox.

    When no Gmail labels are found in the .eml headers (common for
    non-Takeout exports), infers a label from the subfolder name.
    """
    if not os.path.isdir(folder_path):
        print(f"\n  [ERROR] Folder not found: {folder_path}")
        return (existing_mails or []), (seen_ids or {})

    if seen_ids is None:
        seen_ids = {}
    mails = existing_mails if existing_mails is not None else []
    cross_file = len(mails) > 0

    eml_files = _find_all_eml(folder_path)
    if not eml_files:
        print(f"\n  [!] No .eml files found in {folder_path}")
        return mails, seen_ids

    total_size = sum(os.path.getsize(f) for f in eml_files)

    print()
    print("=" * 60)
    src_name = os.path.basename(folder_path)
    if cross_file:
        print(f"  PARSE EML -- {src_name} (merging)")
    else:
        print(f"  PARSE EML -- {src_name}")
    print("=" * 60)
    print(f"  Folder  : {folder_path}")
    print(f"  Files   : {len(eml_files):,} .eml ({total_size / (1024**2):.0f} MB)")
    print(f"  Body    : full (snippet {SNIPPET_CHARS} chars in list)")
    if cross_file:
        print(f"  Existing: {len(mails):,} mails in memory ({len(seen_ids):,} IDs)")
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
            print(f"  ... {total_raw:,}/{len(eml_files):,} | {len(mails):,} unique | "
                  f"{dupes:,} dupes | {elapsed:.0f}s | {speed:.0f}/s | ETA {eta_str}",
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

            # No Gmail labels? Infer from subfolder name (e.g. "Inbox/mail.eml")
            if not labels or labels == ["Autres"]:
                rel = os.path.relpath(eml_path, folder_path)
                parts = rel.replace("\\", "/").split("/")
                if len(parts) > 1:
                    folder_label = parts[0]
                    if folder_label not in (".", "PJ"):
                        mail_data["labels"] = [folder_label]
                        mail_data["l"] = folder_label

            labels = mail_data["labels"]

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
                print(f"  [!] Error {os.path.basename(eml_path)}: {e}")

    elapsed = time.time() - start
    mails_added = len(mails) - mails_before
    mails.sort(key=lambda m: m["ds"], reverse=True)

    print()
    print("=" * 60)
    print(f"  RESULTS EML -- {src_name}")
    print("=" * 60)
    print(f"  .eml files          : {total_raw:,}")
    print(f"  Duplicates removed  : {dupes:,}")
    print(f"  New mails added     : {mails_added:,}")
    if cross_file:
        print(f"  TOTAL (cumulative)  : {len(mails):,}")
    else:
        print(f"  Unique mails        : {len(mails):,}")
    print(f"  With attachments    : {sum(1 for m in mails if m['p'] > 0):,}")
    print(f"  X-GM-THRID (Gmail)  : {gm_thrid_count:,}/{mails_added:,} ({gm_thrid_count*100//max(mails_added,1)}%)")
    print(f"  Errors              : {erreurs}")
    print(f"  Duration            : {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print("=" * 60)

    return mails, seen_ids


def parse_multi_sources(
    source_paths: list[str],
    test_limit: int = 0,
) -> list[MailDict]:
    """Parse multiple sources (.mbox files and .eml folders) with cross-file dedup.

    This is the main entry point for multi-export merging. Each source is
    parsed in order, with Message-IDs tracked across all files to prevent
    duplicates when the same email appears in multiple exports.

    Returns:
        Merged and deduplicated list of mails, sorted newest first.
    """
    # Single source — skip the merge ceremony
    if len(source_paths) == 1:
        p = source_paths[0]
        if os.path.isdir(p):
            mails, _ = parse_eml_folder(p, test_limit=test_limit)
        else:
            mails, _ = parse_mbox(p, test_limit=test_limit)
        return mails

    print()
    print("=" * 60)
    print(f"  MULTI-SOURCE MERGE -- {len(source_paths)} sources")
    print("=" * 60)
    for i, p in enumerate(source_paths, 1):
        if os.path.isdir(p):
            eml_count = len(_find_all_eml(p))
            print(f"  [{i}] {os.path.basename(p)}/ ({eml_count:,} .eml)")
        else:
            size_gb = os.path.getsize(p) / (1024**3) if os.path.isfile(p) else 0
            print(f"  [{i}] {os.path.basename(p)} ({size_gb:.2f} GB)")
    print("=" * 60)

    seen_ids: dict[str, int] = {}
    mails: list[MailDict] = []

    for i, src_path in enumerate(source_paths, 1):
        print(f"\n  --- Source {i}/{len(source_paths)} ---")
        if os.path.isdir(src_path):
            mails, seen_ids = parse_eml_folder(
                src_path, test_limit=test_limit,
                seen_ids=seen_ids, existing_mails=mails,
            )
        else:
            mails, seen_ids = parse_mbox(
                src_path, test_limit=test_limit,
                seen_ids=seen_ids, existing_mails=mails,
            )

    if len(source_paths) > 1:
        all_labels: Counter[str] = Counter()
        for m in mails:
            for lb in m["labels"]:
                all_labels[lb] += 1
        cat_stats = Counter(m["cat"] for m in mails)

        print()
        print("=" * 60)
        print("  MERGE RESULTS")
        print("=" * 60)
        print(f"  Sources             : {len(source_paths)}")
        print(f"  Unique mails total  : {len(mails):,}")
        print(f"  Known IDs (dedup)   : {len(seen_ids):,}")
        print(f"  Distinct labels     : {len(all_labels)}")
        print(f"  With attachments    : {sum(1 for m in mails if m['p'] > 0):,}")
        print()
        if cat_stats:
            print("  Auto-categories:")
            for cat, count in cat_stats.most_common():
                pct = count * 100 / len(mails) if mails else 0
                print(f"    {cat:15s} : {count:,} ({pct:.0f}%)")
            print()
        if all_labels:
            print("  Top 15 labels:")
            for lb, count in all_labels.most_common(15):
                print(f"    {lb:30s} : {count:,}")
        print("=" * 60)

    return mails
