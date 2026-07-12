"""Hidden ground-truth tests for corpus/repo3/datetools.format_date."""

from __future__ import annotations
import os
import sys
from datetime import date

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "code"))

import pytest
from datetools import format_date


def test_default_format():
    assert format_date(date(2026, 7, 11)) == "2026-07-11"


def test_alternative_format():
    assert format_date(date(2026, 7, 11), "DD/MM/YYYY") == "11/07/2026"


def test_year_only():
    assert format_date(date(2026, 1, 1), "YYYY") == "2026"


def test_empty_format_returns_empty():
    assert format_date(date(2026, 1, 1), "") == ""


def test_unknown_tokens_kept():
    assert format_date(date(2026, 7, 11), "Hello YYYY") == "Hello 2026"


def test_rejects_non_date():
    with pytest.raises(TypeError):
        format_date("2026-07-11")  # type: ignore[arg-type]


def test_rejects_non_string_format():
    with pytest.raises(TypeError):
        format_date(date(2026, 1, 1), 12345)  # type: ignore[arg-type]
