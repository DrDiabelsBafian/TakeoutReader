"""
Global configuration for TakeoutReader.

Thresholds, MIME maps, category keywords, and validation invariants.
Tweak these if you're adapting the tool for a different locale or email provider.
"""

from __future__ import annotations

# --- Parsing thresholds ---

BODY_MAX_CHARS = 0       # 0 = no truncation (bodies live in a separate .js file anyway)
SNIPPET_CHARS = 150      # preview text shown in the mail list
MIN_PJ_SIZE = 1024       # skip attachments < 1 KB (tracking pixels, spacer gifs)

# MIME types that are part of the message structure, not real attachments
SKIP_MIME = {
    "text/plain", "text/html",
    "multipart/alternative", "multipart/mixed", "multipart/related",
    "multipart/signed", "multipart/report",
    "message/delivery-status", "message/rfc822",
}

# Fallback extensions when an attachment has no filename
# (surprisingly common with older Android email clients)
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

# --- Smart categories ---
# Keyword-based heuristics checked against From + Subject.
# Not ML, but works well for the 90% case (social networks, banks, shops).
# TODO: make this configurable via a user-facing JSON file

CAT_SOCIAL = {
    "facebook", "facebookmail", "linkedin", "twitter", "x.com",
    "instagram", "threads.net", "tiktok",
    "snapchat", "pinterest", "reddit", "discord", "whatsapp",
    "telegram", "meetup", "nextdoor", "strava",
    "mastodon", "bluesky", "bsky",
}

CAT_BANQUE = {
    "banque", "credit", "caisse", "assurance", "mutuelle", "impot",
    "tresor", "boursorama", "fortuneo", "ing direct", "societe generale",
    "bnp", "lcl", "bred", "cic", "hsbc", "la banque postale",
    "paypal", "stripe", "revolut", "n26", "wise", "sofinco",
    "cetelem", "cofidis", "franfinance", "floa", "younited",
}

CAT_ACHATS = {
    "amazon", "cdiscount", "fnac", "vinted", "leboncoin", "aliexpress",
    "ebay", "wish", "shein", "zalando", "asos", "boulanger", "darty",
    "order", "commande", "livraison", "colis", "facture", "invoice",
    "receipt", "shipped", "tracking", "expedition",
    "uber eats", "deliveroo", "just eat", "paack", "chronopost",
    "colissimo", "dpd", "ups", "fedex", "mondial relay", "relais colis",
    "gls", "tnt", "dhl", "laposte", "suivi",
}

CAT_NOTIF = {
    "noreply", "no-reply", "no_reply", "donotreply",
    "ne-pas-repondre", "nepasrepondre", "automated",
    "mailer-daemon", "postmaster", "system@", "alert@",
    "notification@", "notifications@", "notify@",
}

CAT_NEWSLETTER = {
    "newsletter", "digest", "weekly", "hebdo", "info@",
    "news@", "bulletin", "unsubscribe", "marketing@",
    "promo@", "campaign", "mailchimp", "sendinblue",
    "brevo", "mailjet", "substack",
}

# --- Validation invariants ---
# Used by validator.py to check that the generated HTML is complete.
# Each key is a string that MUST appear in index.html; value is a human description.

MUST_EXIST_HTML: dict[str, str] = {
    # Core rendering
    "function af()": "Main filter function",
    "function rl()": "Render mail list",
    "function sm(": "Show single mail",
    # Avatars + theme
    "avH(": "Color avatar helper",
    "body.light": "Light theme class",
    # Categories + command palette
    "openPalette": "Command palette (Ctrl+K)",
    "catC[": "Category color map",
    "closePalette": "Close palette handler",
    # Split architecture (external JS)
    "mails.js": "External mail data file",
    "bodies.js": "External body data file",
    # Threading
    "tgTm": "Toggle thread message",
    "thLen(": "Thread length helper",
    "TH[": "Thread index map",
    # Stats modal
    "openStats": "Open stats modal",
    "closeStats": "Close stats modal",
    "dash-ov": "Stats modal overlay",
    # Selection + export
    "tgSel": "Toggle selection",
    "exportSel": "Export selection as HTML",
    "selPage": "Select current page",
    "selAll": "Select all",
    "hideSelected": "Hide selected mails",
    "restoreHidden": "Restore hidden mails",
    # Mailbox filters (inbox/sent/spam/trash)
    "dF": "Direction filter",
    "m.spam": "Spam flag",
    "m.trash": "Trash flag",
    "m.sent": "Sent flag",
    "_di": "Pre-computed search index",
    # Visual identity
    "#B388FF": "Violet accent (dark mode)",
    "#E91E63": "Pink accent (light mode)",
    "fadeUp": "fadeUp animation",
    "--glow": "Glow CSS variable",
    "sbw": "Search icon wrapper",
}

# Required fields in each mail object inside mails.js
MUST_EXIST_FIELDS = ("ds", "d", "f", "s", "cat", "tid", "sn", "spam", "trash", "sent")

# Patterns that should NOT appear (known regressions from earlier versions)
MUST_NOT_EXIST: dict[str, str] = {
    "goBrowse": "v6 regression: blocking dashboard",
    "goDash": "v6 regression: blocking dashboard",
    "viewMode": "v6 regression: dashboard mode",
    "dash-go": "v6 regression: Explore button",
    "D.indexOf": "v8 regression: O(n) search",
}
