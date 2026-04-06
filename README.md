# TakeoutReader

**Convert your Gmail exports into a searchable offline HTML archive.**

Zero server. Zero cloud. Your emails stay 100% on your computer.

---

## What it does

TakeoutReader takes your Google Takeout export (`.mbox`, `.zip`, or extracted `.eml` folders) and generates a fast, interactive HTML archive you can browse offline forever.

**Features:**
- 19,000+ emails in ~16 minutes
- Full-text search across all emails
- Gmail labels, threads, and conversation view
- Clickable attachments extracted to disk
- Dark/light theme
- Works on any browser, no server needed

## Download

> **[Download TakeoutReader_Setup_1.0.0.exe](https://github.com/fabiandeblander/TakeoutReader/releases/latest)**

Windows 10/11. No Python required. No admin rights needed.

## How to use

1. **Export your Gmail** at [takeout.google.com](https://takeout.google.com) (select only "Mail")
2. **Install TakeoutReader** (double-click the setup, follow the wizard)
3. **Run TakeoutReader** and select your `.mbox` file or `.eml` folder
4. **Browse** your archive in any web browser -- offline, forever

## Privacy

TakeoutReader never connects to the Internet. No telemetry, no analytics, no cloud.
All processing happens locally on your machine. Period.

## Build from source

See [CONTRIBUTING.md](CONTRIBUTING.md) for build instructions.

Requires: Python 3.10+ and either PyInstaller or Nuitka.

## License

[MIT](LICENSE.txt)

---

Made by [Fabian De Blander](https://github.com/fabiandeblander)
