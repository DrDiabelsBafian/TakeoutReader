# TakeoutReader

**Convert your Gmail Takeout exports into a fast, searchable, offline HTML archive.**

Zero server. Zero cloud. Zero telemetry. Your emails stay 100% on your machine.

---

## The Problem

Google Takeout exports your Gmail as `.mbox` files — a raw format that no regular user can open. Most "solutions" are Windows-only freemium tools from the 2000s that upload your data to their servers.

## The Solution

TakeoutReader converts your `.mbox` (or `.zip` or `.eml` folder) into a **standalone HTML archive** you can browse in any web browser, offline, forever.

### What you get

- **Full-text search** across thousands of emails in milliseconds
- **Gmail threads** preserved (conversation view, just like Gmail)
- **Smart categories** — auto-sorted into Perso, Achats, Banque, Newsletter, Notif, Social
- **Attachments** extracted to disk and clickable from the interface
- **Command palette** (Ctrl+K) for power users
- **Dark/Light theme** with violet accent
- **Selection + Export** — select emails and export as standalone HTML
- **Keyboard navigation** — j/k to browse, / to search, Esc to reset

### Performance

| Dataset | Time | Output |
|---|---|---|
| 50 emails | ~44s | 0.3 MB |
| 4,741 emails | ~2 min | 19 MB |
| 19,000+ emails | ~16 min | ~47 MB |

---

## Download

> **[Download the latest release](https://github.com/DrDiabelsBafian/TakeoutReader/releases/latest)**

Windows 10/11. No Python required. No admin rights needed.

---

## How to use

1. **Export your Gmail** at [takeout.google.com](https://takeout.google.com) (select only "Mail", format `.mbox`)
2. **Run TakeoutReader** and select your `.mbox` file, `.zip` archive, or `.eml` folder
3. **Browse** your archive — open `INDEX_GMAIL.html` in any browser

That's it. No account, no server, no configuration.

---

## Privacy

TakeoutReader **never connects to the Internet**. Not during install, not during conversion, not ever.

- No telemetry
- No analytics
- No cloud upload
- No third-party dependencies at runtime
- All processing happens locally

Your emails are yours. Period.

---

## Project Structure

```
takeoutreader/
    __init__.py          # Package metadata + version
    __main__.py          # CLI entry point
    core/
        constants.py     # Configuration, MIME maps, category keywords
        sanitizer.py     # Text cleaning, MIME header decoding
        detection.py     # Auto-detect .mbox/.eml/.zip sources
        parser.py        # Parse mbox/eml, dedup, threading
        extractor.py     # Attachment extraction to disk
        renderer.py      # HTML/JS output generation
        validator.py     # Post-generation quality checks
    gui/
        app.py           # CustomTkinter GUI
tests/
    fixtures/            # Small .mbox samples for testing
    test_parser.py
    test_extractor.py
    test_sanitizer.py
```

Each module has a single responsibility. The core runs independently of the GUI — you can use it as a library:

```python
from takeoutreader.core.parser import parse_mbox

mails, seen_ids = parse_mbox("my_export.mbox")
print(f"{len(mails)} emails parsed")
```

---

## Install from source

**Requirements:** Python 3.10+

```bash
# Clone
git clone https://github.com/DrDiabelsBafian/TakeoutReader.git
cd TakeoutReader

# Install (editable, with dev dependencies)
pip install -e ".[dev]"

# Run GUI
takeoutreader-gui

# Run CLI
takeoutreader my_export.mbox
# or
python -m takeoutreader my_export.mbox

# Run tests
pytest

# Build executable (Nuitka)
python -m nuitka --standalone --enable-plugin=tk-inter \
    --include-package=takeoutreader --include-package=customtkinter \
    --windows-console-mode=disable takeoutreader_gui.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed build instructions.

---

## Tech Stack

- **Python 3.10+** — core parsing uses stdlib only (no external dependencies)
- **CustomTkinter** — modern cross-platform GUI
- **Nuitka** — compiled to C, no Python needed at runtime
- **Inno Setup** — Windows installer

---

## Comparison

| Feature | TakeoutReader | RecoveryTools | 4n6 | BitRecover |
|---|---|---|---|---|
| Cross-platform output | HTML (any browser) | Windows viewer | Windows viewer | Windows viewer |
| Fully offline | Yes | Partial | Partial | Partial |
| Open source | MIT | No | No | No |
| Zero install viewer | Yes (HTML file) | No | No | No |
| Free | Yes | Freemium ($49) | Freemium ($39) | Freemium ($29) |
| Privacy | No data leaves machine | Unknown | Unknown | Unknown |

---

## How this was built

I'm not a software engineer — I'm a workflow architect who needed a tool that didn't exist. TakeoutReader was built with significant AI assistance (Claude by Anthropic) for code generation, while I handled the product vision, UX decisions, and testing against real-world Gmail exports (19,000+ emails across 15 years).

The architecture decisions are mine. The code is AI-generated and human-audited. If you spot something that could be improved, PRs are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Known Limitations

- Output is in French (English localization planned)
- Categories are keyword-based, not ML — works well for common senders, less so for niche ones
- Very large attachments (>50 MB) may slow down extraction
- No incremental updates — re-run processes the full export each time

---

## License

[MIT](LICENSE.txt) — Use it, fork it, ship it.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

---

Made by [Dr. Diabels Bafian](https://github.com/DrDiabelsBafian)
