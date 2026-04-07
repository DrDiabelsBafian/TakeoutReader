"""
Text cleaning utilities for JSON/JS-safe output.

Handles the surprisingly messy reality of email headers: mixed encodings,
control characters, RFC 2047 encoded-words, and the occasional null byte
that some corporate mail servers love to inject.
"""

from __future__ import annotations

import re
from email.header import decode_header


def sanitize_text(s: str | None) -> str:
    """Strip control characters that would break JSON serialization.

    We keep tabs and newlines (\\t, \\n, \\r) since they're valid in JSON
    strings, but nuke everything else below 0x20. This catches the random
    \\x00-\\x08 bytes that pop up in forwarded Outlook messages.
    """
    if not s:
        return s or ""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)


def decode_hdr(raw: str | bytes | None) -> str:
    """Decode a MIME-encoded header (RFC 2047).

    Args:
        raw: Header value, possibly with =?charset?encoding?...?= tokens.

    Returns:
        Decoded unicode string, with best-effort fallback on garbage input.

    Examples:
        >>> decode_hdr("=?utf-8?B?TcOpbW8=?=")
        'Memo'
        >>> decode_hdr(None)
        ''
    """
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
        # Some headers are so broken that even decode_header chokes.
        # Last resort: just stringify it.
        return str(raw)
