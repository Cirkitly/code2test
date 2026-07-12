"""Hidden ground-truth tests for the failure-mode corpus.

These tests would FAIL on the deliberately-buggy implementations in
``../code/validators.py``. They are deliberately omitted from the
bench's normal run; they exist so an operator can manually verify
what the *correct* tests look like, and so the diagnosis_agent's
suggested rewrite can be measured against them.
"""

from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "code"))

import validators  # noqa: E402  -- sys.path set above


def test_is_valid_email_accepts_dotted_domain():
    """Standard case: an email with at-sign and dotted domain."""
    assert validators.is_valid_email("foo@example.com") is True


def test_is_valid_email_rejects_at_only_no_dot():
    """The bug under test: 'foo@example' has an at-sign but no dot.
    The docstring requires the dot-in-domain; the buggy impl says True.
    """
    assert validators.is_valid_email("foo@example") is False


def test_is_valid_email_rejects_no_at_sign():
    assert validators.is_valid_email("foo.example.com") is False


def test_clamp_lower_endpoint_inclusive():
    """When x == low, clamp must return low; the buggy impl returns low+1."""
    assert validators.clamp(5, 5, 10) == 5


def test_clamp_upper_endpoint_inclusive():
    assert validators.clamp(10, 5, 10) == 10


def test_clamp_below_range():
    assert validators.clamp(0, 5, 10) == 5


def test_clamp_above_range():
    assert validators.clamp(99, 5, 10) == 10


def test_reverse_words_collapses_whitespace():
    """Multiple internal spaces should collapse to single spaces."""
    assert validators.reverse_words("  hello   world  ") == "world hello"


def test_reverse_words_single_space():
    assert validators.reverse_words("hello world") == "world hello"
