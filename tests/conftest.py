"""Shared test fixtures."""

from __future__ import annotations

import os
import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_mbox_path() -> str:
    """Path to a small .mbox with 3 valid emails."""
    return os.path.join(FIXTURES_DIR, "sample.mbox")


@pytest.fixture
def empty_mbox_path() -> str:
    """Path to an empty .mbox file."""
    return os.path.join(FIXTURES_DIR, "empty.mbox")


@pytest.fixture
def edge_cases_mbox_path() -> str:
    """Path to a .mbox with corrupted headers and duplicate Message-IDs."""
    return os.path.join(FIXTURES_DIR, "edge_cases.mbox")
