"""Tests for attachment extraction."""

from __future__ import annotations

from takeoutreader.core.extractor import _sanitize_pj_filename


class TestSanitizeFilename:
    """Ensure filenames are filesystem-safe."""

    def test_normal_filename(self) -> None:
        assert _sanitize_pj_filename("report.pdf") == "report.pdf"

    def test_strips_forbidden_chars(self) -> None:
        result = _sanitize_pj_filename('file<>:"/\\|?*.txt')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert result.endswith(".txt")

    def test_empty_filename(self) -> None:
        assert _sanitize_pj_filename("") == "sans_nom"
        assert _sanitize_pj_filename(None) == "sans_nom"

    def test_truncates_long_names(self) -> None:
        long_name = "a" * 200 + ".pdf"
        result = _sanitize_pj_filename(long_name)
        assert len(result) <= 180
        assert result.endswith(".pdf")

    def test_strips_dots_and_spaces(self) -> None:
        assert _sanitize_pj_filename("  ..file..  ") == "file"
