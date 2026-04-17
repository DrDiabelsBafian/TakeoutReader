# TakeoutReader

![Version](https://img.shields.io/github/v/release/DrDiabelsBafian/TakeoutReader?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat-square)

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
| 50 emails | ~44s | 0.3 Mo |
| 4,741 emails | ~2 min | 19 Mo |
| 19,000+ emails | ~16 min | ~47 Mo |

---

## Download

> **[Download TakeoutReader_Setup_3.0.0.exe](https://github.com/DrDiabelsBafian/TakeoutReader/releases/latest)**

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
    __init__.py          # Package metadata
    __main__.py          # CLI entry point
    core/
        constants.py     # Configuration, MIME maps, categories
        sanitizer.py     # Text cleaning, MIME header decoding
        detection.py     # Auto-detect .mbox/.eml/.zip sources
        parser.py        # Parse mbox/eml, dedup, threading
        extractor.py     # Attachment extraction to disk
        renderer.py      # HTML/JS output generation
        validator.py     # Post-generation quality checks
    gui/
        app.py           # CustomTkinter GUI
```

Each module has a single responsibility. The core runs independently of the GUI — you can use it as a library:

```python
from takeoutreader.core.parser import parse_mbox

mails, seen_ids = parse_mbox("my_export.mbox")
print(f"{len(mails)} emails parsed")
```

---

## Build from source

**Requirements:** Python 3.10+, CustomTkinter, Pillow

```bash
# Clone
git clone https://github.com/DrDiabelsBafian/TakeoutReader.git
cd TakeoutReader

# Install dependencies
pip install customtkinter Pillow

# Run GUI
python takeoutreader_gui.py

# Or run CLI
python -m takeoutreader my_export.mbox

# Build executable (Nuitka, recommended)
python -m nuitka --standalone --enable-plugin=tk-inter --include-package=takeoutreader --include-package=customtkinter --windows-console-mode=disable takeoutreader_gui.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed build instructions.

---

## Tech Stack

- **Python 3.14** — zero external dependency for core parsing (stdlib only)
- **CustomTkinter** — modern GUI framework
- **Nuitka** — compiled to C, no Python needed at runtime
- **Inno Setup** — professional Windows installer

---

## Competitive Advantage

| Feature | TakeoutReader | RecoveryTools | 4n6 | BitRecover |
|---|---|---|---|---|
| Cross-platform output | HTML (any browser) | Windows viewer | Windows viewer | Windows viewer |
| Fully offline | Yes | Partial | Partial | Partial |
| Open source | MIT | No | No | No |
| Zero install viewer | Yes (HTML file) | No | No | No |
| Free | Yes | Freemium ($49) | Freemium ($39) | Freemium ($29) |
| Privacy | No data leaves machine | Unknown | Unknown | Unknown |

---

## License

[MIT](LICENSE.txt) — Use it, fork it, ship it.

---

Made by [Dr. Diabels Bafian](https://github.com/DrDiabelsBafian)
