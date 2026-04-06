# ============================================
# takeoutreader/core/constants.py
# Configuration globale TakeoutReader
# ============================================

BODY_MAX_CHARS = 0            # 0 = pas de troncature body (bodies.js separe)
SNIPPET_CHARS = 150           # Snippet dans la liste + mails.js
MIN_PJ_SIZE = 1024            # Ignore PJ < 1 Ko (pixels tracking)

# MIME types a ignorer lors de l'extraction PJ
SKIP_MIME = {"text/plain", "text/html", "multipart/alternative", "multipart/mixed",
             "multipart/related", "multipart/signed", "multipart/report",
             "message/delivery-status", "message/rfc822"}

# Extension map pour PJ sans nom
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

# Features qui DOIVENT exister dans index.html (validation rebouclage)
MUST_EXIST_HTML = {
    # V1 -- Core
    "function af()": "Filtre principal",
    "function rl()": "Render liste",
    "function sm(": "Affichage mail",
    # V2 -- Avatars + Theme
    "avH(": "Avatars couleur",
    "body.light": "Theme clair",
    # V3 -- Categories + Command palette
    "openPalette": "Command palette Ctrl+K",
    "catC[": "Couleurs categories",
    "closePalette": "Fermeture palette",
    # V4 -- Archi split
    "mails.js": "Chargement mails.js",
    "bodies.js": "Chargement bodies.js",
    # V5 -- Threads
    "tgTm": "Toggle thread message",
    "thLen(": "Thread length helper",
    "TH[": "Thread map",
    # V6 -- Stats modal
    "openStats": "Ouverture modal stats",
    "closeStats": "Fermeture modal stats",
    "dash-ov": "Overlay modal stats",
    # V7 -- Selection + Export
    "tgSel": "Toggle selection",
    "exportSel": "Export selection HTML",
    "selPage": "Selection page",
    "selAll": "Selection tous",
    "hideSelected": "Masquer selection",
    "restoreHidden": "Restaurer masques",
    # V8 -- Spam/Sent/Trash + Perf
    "dF": "Filtre direction (boite)",
    "m.spam": "Flag spam",
    "m.trash": "Flag corbeille",
    "m.sent": "Flag envoye",
    "_di": "Pre-index perf",
    # V12 -- Violet/Rose palette + icons + animations
    "#B388FF": "Accent violet dark",
    "#E91E63": "Accent rose light",
    "fadeUp": "Animation fadeUp",
    "--glow": "Glow variable",
    "sbw": "Search icon wrapper",
}

# Champs obligatoires dans mails.js
MUST_EXIST_FIELDS = ("ds", "d", "f", "s", "cat", "tid", "sn", "spam", "trash", "sent")

# Patterns qui ne doivent PLUS exister (regressions connues)
MUST_NOT_EXIST = {
    "goBrowse": "V6 regression: dashboard bloquant",
    "goDash": "V6 regression: dashboard bloquant",
    "viewMode": "V6 regression: mode dashboard",
    "dash-go": "V6 regression: bouton Explorer",
    "D.indexOf": "V8 regression: perf O(n)",
}
