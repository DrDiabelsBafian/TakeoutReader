"""
Post-generation quality checks.

Validates that the output HTML archive is structurally complete: all
required files exist, JS is syntactically balanced, mails.js contains
the right number of entries, no known regressions are present, etc.

This is our "Rebouclage" protocol — a safety net that catches broken
output before the user tries to open it in a browser.
"""

from __future__ import annotations

import os
import json
import logging

from takeoutreader.core.constants import (
    MUST_EXIST_HTML, MUST_EXIST_FIELDS, MUST_NOT_EXIST,
)

log = logging.getLogger(__name__)


def validate_output(output_dir: str, nb_mails: int) -> tuple[int, int, int]:
    """Run all validation checks on the generated output.

    Args:
        output_dir: Path to the generated archive folder.
        nb_mails: Expected number of mails (from the parser).

    Returns:
        Tuple of (pass_count, fail_count, warn_count).
    """
    index_path = os.path.join(output_dir, "index.html")
    mails_path = os.path.join(output_dir, "mails.js")
    bodies_path = os.path.join(output_dir, "bodies.js")

    print()
    print("=" * 60)
    print("  VALIDATION")
    print("=" * 60)

    passed = 0
    failed = 0
    warned = 0

    # Check that all output files exist
    for fpath, fname in [(index_path, "index.html"), (mails_path, "mails.js"), (bodies_path, "bodies.js")]:
        if os.path.isfile(fpath):
            passed += 1
        else:
            print(f"  [FAIL] Missing file: {fname}")
            failed += 1

    if failed > 0:
        print(f"\n  ABORT: critical files missing")
        return passed, failed, warned

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    with open(mails_path, "r", encoding="utf-8") as f:
        mails_js = f.read()

    # Check required patterns in index.html
    for pattern, desc in MUST_EXIST_HTML.items():
        if pattern in html:
            passed += 1
        else:
            print(f"  [FAIL] MISSING: '{pattern}' -- {desc}")
            failed += 1

    # Check that known regressions haven't crept back in
    for pattern, desc in MUST_NOT_EXIST.items():
        if pattern in html:
            print(f"  [FAIL] REGRESSION: '{pattern}' -- {desc}")
            failed += 1
        else:
            passed += 1

    # Verify JS braces are balanced (catches truncated output)
    js_start = html.find("<script>", html.find("mails.js"))
    js_end = html.find("</script>", js_start) if js_start >= 0 else -1
    if js_start >= 0 and js_end >= 0:
        js = html[js_start+8:js_end]
        opens = js.count("{")
        closes = js.count("}")
        if opens == closes:
            passed += 1
        else:
            print(f"  [FAIL] Unbalanced JS braces: {opens} open / {closes} close")
            failed += 1
    else:
        print(f"  [WARN] Could not locate main JS block")
        warned += 1

    # Validate mails.js: parseable JSON, correct count, required fields
    try:
        # mails.js format: "var D=[...data...];\n"
        data = json.loads(mails_js[len("var D="):-2])
        if len(data) == nb_mails:
            passed += 1
        else:
            print(f"  [FAIL] mails.js: {len(data)} mails, expected {nb_mails}")
            failed += 1

        if mails_js.startswith("var D="):
            passed += 1
        else:
            print(f"  [FAIL] mails.js: doesn't start with 'var D='")
            failed += 1

        # Spot-check required fields on the first mail
        first = data[0] if data else {}
        for field in MUST_EXIST_FIELDS:
            if field in first:
                passed += 1
            else:
                print(f"  [FAIL] mails.js: missing field '{field}'")
                failed += 1
    except Exception as e:
        print(f"  [FAIL] mails.js: invalid JSON -- {e}")
        failed += 1

    # Validate bodies.js
    try:
        with open(bodies_path, "r", encoding="utf-8") as f:
            bodies_js = f.read()
        if bodies_js.startswith("var B="):
            passed += 1
        else:
            print(f"  [FAIL] bodies.js: doesn't start with 'var B='")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] bodies.js: unreadable -- {e}")
        failed += 1

    # Sanity check on file sizes
    html_size = len(html)
    mails_size = len(mails_js)
    if html_size > 10000:
        passed += 1
    else:
        print(f"  [WARN] index.html suspiciously small: {html_size} chars")
        warned += 1

    if mails_size > 100:
        passed += 1
    else:
        print(f"  [WARN] mails.js suspiciously small: {mails_size} chars")
        warned += 1

    # Summary
    total = passed + failed + warned
    print()
    if failed == 0:
        print(f"  VALIDATION OK -- {passed}/{total} checks passed" +
              (f", {warned} warnings" if warned else ""))
    else:
        print(f"  VALIDATION FAILED -- {failed} FAIL / {passed} pass / {warned} warn")
        print(f"  -> Fix the FAILs before shipping")

    return passed, failed, warned
