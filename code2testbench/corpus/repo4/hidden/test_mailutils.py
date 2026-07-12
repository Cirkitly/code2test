"""Hidden ground-truth tests for corpus/repo4/mailutils.is_valid_email."""

from __future__ import annotations
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "code"))

from mailutils import is_valid_email


def test_valid_basic():
    assert is_valid_email("alice@example.com") is True


def test_valid_with_subdomain():
    assert is_valid_email("alice@mail.example.com") is True


def test_valid_with_plus():
    # Implementation accepts plus in local part.
    assert is_valid_email("alice+test@example.com") is True


def test_invalid_no_at():
    assert is_valid_email("alice.example.com") is False


def test_invalid_no_tld():
    assert is_valid_email("alice@example") is False


def test_invalid_empty_string():
    assert is_valid_email("") is False


def test_invalid_whitespace():
    assert is_valid_email("alice @example.com") is False


def test_invalid_non_string():
    assert is_valid_email(None) is False  # type: ignore[arg-type]
