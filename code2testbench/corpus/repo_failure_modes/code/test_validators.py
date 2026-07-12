import pytest
from validators import is_valid_email, clamp, reverse_words

def test_is_valid_email_accepts_fully_qualified_address():
    """foo@example.com has both '@' and a dotted domain, so it is valid."""
    assert is_valid_email('foo@example.com') is True


def test_is_valid_email_rejects_address_without_dotted_domain():
    """foo@example has '@' but lacks a domain dot, so it must be invalid."""
    assert is_valid_email('foo@example') is False


def test_is_valid_email_rejects_plain_string():
    """A string lacking '@' is not an email."""
    assert is_valid_email('foo.example.com') is False


def test_clamp_includes_lower_endpoint():
    """The lower bound of [low, high] must be included in the output."""
    assert clamp(0, 0, 10) == 0


def test_clamp_includes_upper_endpoint():
    """The upper bound of [low, high] must be included in the output."""
    assert clamp(10, 0, 10) == 10


def test_clamp_clamps_below_range():
    """Values below low are clamped up to the inclusive lower bound."""
    assert clamp(-5, 0, 10) == 0


def test_reverse_words_swaps_simple_pair():
    """The happy path: 'hello world' reverses to 'world hello'."""
    assert reverse_words('hello world') == 'world hello'


def test_reverse_words_collapses_multiple_spaces():
    """Multiple spaces between words collapse to a single separator."""
    assert reverse_words('hello   world') == 'world hello'


def test_reverse_words_strips_outer_whitespace():
    """Outer whitespace is not a word and should not appear in the result."""
    assert reverse_words('  hello world  ') == 'world hello'

