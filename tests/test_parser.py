"""Tests for the mbox/eml parser."""

from __future__ import annotations

import os
import pytest

from takeoutreader.core.parser import (
    parse_mbox,
    categorize_mail,
    get_date,
    extract_body_text,
    parse_gmail_labels,
)


class TestParseMbox:
    """Integration tests for the full parse pipeline."""

    def test_parse_sample_mbox(self, sample_mbox_path: str) -> None:
        """Parse a valid .mbox with 3 emails."""
        mails, seen_ids = parse_mbox(sample_mbox_path)

        assert len(mails) == 3
        assert len(seen_ids) == 3

        # Check that mails are sorted newest first
        dates = [m["ds"] for m in mails]
        assert dates == sorted(dates, reverse=True)

    def test_parse_empty_mbox(self, empty_mbox_path: str) -> None:
        """An empty .mbox should return zero mails, not crash."""
        mails, seen_ids = parse_mbox(empty_mbox_path)

        assert len(mails) == 0
        assert len(seen_ids) == 0

    def test_parse_missing_file(self, tmp_path) -> None:
        """A missing file should return empty results, not raise."""
        mails, seen_ids = parse_mbox(str(tmp_path / "does_not_exist.mbox"))

        assert mails == []

    def test_deduplication(self, edge_cases_mbox_path: str) -> None:
        """Duplicate Message-IDs should be merged, not duplicated."""
        mails, seen_ids = parse_mbox(edge_cases_mbox_path)

        # edge_cases.mbox has 3 raw messages but 2 unique IDs
        # (the third is a dupe of the second with a different label)
        dupe_mails = [m for m in mails if m.get("_mid") == "<dupe001@test.com>"]
        assert len(dupe_mails) == 1

        # The duplicate's label ("Important") should be merged in
        assert "Important" in dupe_mails[0]["labels"]

    def test_corrupted_headers_dont_crash(self, edge_cases_mbox_path: str) -> None:
        """Emails with broken headers should be skipped, not crash the parser."""
        mails, seen_ids = parse_mbox(edge_cases_mbox_path)

        # Should have parsed at least the valid mails
        assert len(mails) >= 1

    def test_required_fields_present(self, sample_mbox_path: str) -> None:
        """Every parsed mail must have the required fields for mails.js."""
        mails, _ = parse_mbox(sample_mbox_path)

        required = {"ds", "d", "f", "ff", "s", "cat", "tid", "sn", "spam", "trash", "sent"}
        for mail in mails:
            missing = required - set(mail.keys())
            assert not missing, f"Missing fields: {missing}"

    def test_test_limit(self, sample_mbox_path: str) -> None:
        """--test flag should limit the number of parsed mails."""
        mails, _ = parse_mbox(sample_mbox_path, test_limit=1)

        assert len(mails) <= 1


class TestCategorize:
    """Unit tests for the keyword-based categorizer."""

    def test_social_from_facebook(self) -> None:
        mail = {"ff": "noreply@facebookmail.com", "s": "New notification", "labels": []}
        assert categorize_mail(mail) == "Social"

    def test_banque_from_boursorama(self) -> None:
        mail = {"ff": "alert@boursorama.com", "s": "Votre releve", "labels": []}
        assert categorize_mail(mail) == "Banque"

    def test_achats_from_amazon(self) -> None:
        mail = {"ff": "shipping@amazon.com", "s": "Your order has shipped", "labels": []}
        assert categorize_mail(mail) == "Achats"

    def test_newsletter_with_unsub(self) -> None:
        mail = {"ff": "random@company.com", "s": "Weekly digest", "labels": []}
        assert categorize_mail(mail, has_unsub=True) == "Newsletter"

    def test_notif_from_noreply(self) -> None:
        mail = {"ff": "noreply@someapp.com", "s": "Password changed", "labels": []}
        assert categorize_mail(mail) == "Notif"

    def test_perso_fallback(self) -> None:
        """A regular email from a person should be categorized as Perso."""
        mail = {"ff": "friend@gmail.com", "s": "Dinner tonight?", "labels": []}
        assert categorize_mail(mail) == "Perso"

    def test_gmail_label_hint(self) -> None:
        """Gmail labels should be used as fallback for categorization."""
        mail = {"ff": "unknown@unknown.com", "s": "hello", "labels": ["Promotions"]}
        assert categorize_mail(mail) == "Newsletter"


class TestGetDate:
    """Edge cases for date parsing."""

    def test_valid_date(self) -> None:
        """Standard RFC 2822 date should parse correctly."""
        import mailbox
        from email import policy
        from email.parser import BytesParser

        raw = (
            b"From: test@test.com\r\n"
            b"Date: Mon, 01 Jan 2024 12:00:00 +0100\r\n"
            b"\r\n"
            b"body\r\n"
        )
        parser = BytesParser(policy=policy.default)
        msg = parser.parsebytes(raw)
        ds, dd = get_date(msg)

        assert ds.startswith("2024-01-01")
        assert "01/01/2024" in dd

    def test_missing_date_returns_fallback(self) -> None:
        """A message with no Date header should return the fallback."""
        from email import policy
        from email.parser import BytesParser

        raw = b"From: test@test.com\r\n\r\nbody\r\n"
        parser = BytesParser(policy=policy.default)
        msg = parser.parsebytes(raw)
        ds, dd = get_date(msg)

        assert ds == "0000-00-00"
        assert dd == ""
