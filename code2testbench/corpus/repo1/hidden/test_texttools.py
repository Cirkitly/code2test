"""Hidden ground-truth tests for corpus/repo1/texttools.truncate."""

from __future__ import annotations
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "code"))

import pytest
from texttools import truncate


def test_short_text_passthrough():
    assert truncate("hello", max_chars=10) == "hello"


def test_truncates_at_word_boundary():
    out = truncate("the quick brown fox jumps over the lazy dog", max_chars=12)
    assert out.endswith("...")
    # Implementation: keep = max_chars - len("...") = 12 - 3 = 9; then
    # last_space in text[:9] = "the quick" is index 3 -> cut to "the".
    assert out == "the..."


def test_truncates_to_max_chars_with_ellipsis():
    long = "a" * 100
    out = truncate(long, max_chars=10)
    assert len(out) <= 10
    assert out.endswith("...")


def test_max_chars_smaller_than_ellipsis():
    # Implementation raises nothing — but ensure no crash, returns truncated ellipsis.
    out = truncate("hello world", max_chars=2)
    assert len(out) <= 2


def test_rejects_non_string():
    with pytest.raises(TypeError):
        truncate(None)  # type: ignore[arg-type]


def test_rejects_invalid_max_chars():
    with pytest.raises(ValueError):
        truncate("hi", max_chars=0)
