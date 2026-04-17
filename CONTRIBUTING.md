# Contributing to TakeoutReader

Thanks for your interest in contributing! TakeoutReader is an open-source project and contributions are welcome.

## How to contribute

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add: my feature"`)
4. Push to your branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## Commit conventions

Prefix your commits for clarity:

- `Add:` — new feature or file
- `Fix:` — bug fix
- `Refactor:` — code restructuring (no behavior change)
- `Docs:` — documentation only
- `Test:` — adding or updating tests

## Code style

- **Python**: Google-style docstrings, type hints on public function signatures
- **ASCII only** in strings and comments (no accented characters in code)
- Run `pytest` before submitting

## Reporting bugs

Open a [GitHub Issue](https://github.com/DrDiabelsBafian/TakeoutReader/issues) with:

- Steps to reproduce
- Expected vs actual behavior
- Your OS and Python version
- The input format you used (.mbox, .zip, or .eml folder)

## Feature requests

Open an issue with the `enhancement` label. Describe what you'd like and why it would be useful.

## Project structure

```
takeoutreader/
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

Each module has a single responsibility. Keep it that way.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE.txt).
