# Changelog

All notable changes to TakeoutReader will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v2.0.0

### Added
- `pyproject.toml` for standard Python packaging
- `CHANGELOG.md`
- Type hints on all public function signatures
- Google-style docstrings on all public functions
- `tests/` directory with pytest suite (parse, extract, dedup, edge cases)

### Changed
- Console messages switched from French to English
- `print()` calls replaced with `logging` stdlib
- Comments overhauled: removed mechanical headers, added contextual documentation
- README updated with test badge, "Built with AI" section, and v2.0.0 download link

### Fixed
- Silent failures on corrupted attachments now raise explicit errors
- `.gitignore` expanded to cover build artifacts and IDE files

## [1.1.0] — 2026-04-06

### Changed
- **Modular architecture**: refactored 2,352-line monolith into 9 modules
  - `core/parser.py` — .mbox and .eml parsing, deduplication, threading
  - `core/renderer.py` — HTML/JS output generation
  - `core/extractor.py` — attachment extraction to disk
  - `core/sanitizer.py` — text cleaning and MIME header decoding
  - `core/detection.py` — auto-detect .mbox/.eml/.zip input sources
  - `core/validator.py` — post-generation quality checks (56 invariants)
  - `core/constants.py` — configuration and category keywords
  - `gui/app.py` — CustomTkinter GUI (dark violet theme)
  - `__main__.py` — CLI entry point
- README expanded with project structure, benchmarks, and competitive comparison
- Nuitka build with `--onedir` mode (3-5s startup)
- Inno Setup installer for Windows 10/11

## [1.0.0] — 2026-04-06

### Added
- Initial public release
- Parse `.mbox`, `.zip`, and `.eml` folder inputs
- Full-text search across thousands of emails (client-side JavaScript)
- Gmail thread reconstruction (conversation view)
- Smart auto-categories: Perso, Achats, Banque, Newsletter, Notif, Social
- Attachment extraction to disk with clickable links
- Command palette (Ctrl+K)
- Dark/Light theme with violet accent
- Selection and export as standalone HTML
- Keyboard navigation (j/k, /, Esc)
- 100% offline — zero telemetry, zero cloud, zero server
- CustomTkinter GUI with dark violet theme
- Nuitka-compiled Windows executable
- Inno Setup installer (no admin rights required)

[Unreleased]: https://github.com/DrDiabelsBafian/TakeoutReader/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/DrDiabelsBafian/TakeoutReader/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/DrDiabelsBafian/TakeoutReader/releases/tag/v1.0.0
