"""Tests for text sanitization and MIME header decoding."""

from __future__ import annotations

from takeoutreader.core.sanitizer import sanitize_text, decode_hdr


class TestSanitizeText:
    """Ensure control characters are stripped without losing real content."""

    def test_strips_null_bytes(self) -> None:
        assert sanitize_text("hello\x00world") == "helloworld"

    def test_strips_control_chars(self) -> None:
        # \x01 through \x08 should be removed
        assert sanitize_text("a\x01b\x07c") == "abc"

    def test_preserves_newlines_and_tabs(self) -> None:
        # \t (0x09), \n (0x0a), \r (0x0d) are fine in JSON strings
        assert sanitize_text("line1\nline2\ttab") == "line1\nline2\ttab"

    def test_empty_input(self) -> None:
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""

    def test_normal_text_unchanged(self) -> None:
        text = "Hello, this is a perfectly normal email body."
        assert sanitize_text(text) == text

    def test_unicode_preserved(self) -> None:
        # French accents, emoji, CJK — should all pass through
        text = "Bonjour cafe et croissant"
        assert sanitize_text(text) == text


class TestDecodeHdr:
    """Test MIME header decoding (RFC 2047)."""

    def test_plain_ascii(self) -> None:
        assert decode_hdr("Hello World") == "Hello World"

    def test_none_input(self) -> None:
        assert decode_hdr(None) == ""

    def test_utf8_encoded(self) -> None:
        # =?utf-8?B?...?= is base64-encoded UTF-8
        result = decode_hdr("=?utf-8?B?Qm9uam91cg==?=")
        assert result == "Bonjour"

    def test_iso_encoded(self) -> None:
        # =?iso-8859-1?Q?...?= is quoted-printable
        result = decode_hdr("=?iso-8859-1?Q?caf=E9?=")
        assert "caf" in result  # should contain "caf" + e-acute

    def test_garbage_input_doesnt_crash(self) -> None:
        # Some mail servers produce truly broken headers
        result = decode_hdr("=?broken?garbage?=")
        # Should return something, not raise
        assert isinstance(result, str)
