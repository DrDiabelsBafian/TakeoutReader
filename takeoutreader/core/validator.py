# ============================================
# takeoutreader/core/validator.py
# Protocole Rebouclage Qualite
# Validation post-generation de l'output HTML
# ============================================

import os
import json

from takeoutreader.core.constants import (
    MUST_EXIST_HTML, MUST_EXIST_FIELDS, MUST_NOT_EXIST,
)

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
