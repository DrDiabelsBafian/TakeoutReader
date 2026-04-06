# ============================================
# takeoutreader/core/sanitizer.py
# Nettoyage texte pour JSON/JS safe output
# ============================================

import re
import html as html_mod
from email.header import decode_header


def sanitize_text(s):
    """Supprime les caracteres de controle qui cassent JSON/JS"""
    if not s:
        return s
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)


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
