import pytest
from inflection import dasherize

def test_dasherize_replaces_underscore_with_dash_docstring_example():
    """The documented example: 'puni_puni' should be dasherized to 'puni-puni'."""
    assert dasherize("puni_puni") == "puni-puni"


def test_dasherize_replaces_multiple_underscores():
    """All underscore occurrences in the string should be replaced (not just the first)."""
    assert dasherize("foo_bar_baz_qux") == "foo-bar-baz-qux"


def test_dasherize_replaces_consecutive_underscores():
    """Consecutive underscores should each be replaced with their own dash."""
    assert dasherize("foo__bar") == "foo--bar"


def test_dasherize_replaces_long_run_of_underscores():
    """A long run of underscores should become a matching run of dashes."""
    assert dasherize("____") == "----"


def test_dasherize_replaces_leading_underscore():
    """A leading underscore should be replaced with a leading dash."""
    assert dasherize("_foo") == "-foo"


def test_dasherize_replaces_trailing_underscore():
    """A trailing underscore should be replaced with a trailing dash."""
    assert dasherize("foo_") == "foo-"


def test_dasherize_single_underscore_becomes_single_dash():
    """A string containing only one underscore should become a single dash."""
    assert dasherize("_") == "-"


def test_dasherize_leaves_string_without_underscores_unchanged():
    """A string with no underscores at all should be returned identically."""
    assert dasherize("foobar") == "foobar"


def test_dasherize_leaves_string_with_only_dashes_unchanged():
    """A string containing only dashes (no underscores) should be returned identically."""
    assert dasherize("foo-bar-baz") == "foo-bar-baz"


def test_dasherize_leaves_empty_string_unchanged():
    """The empty string is the identity for this transformation."""
    assert dasherize("") == ""


def test_dasherize_only_dash_unchanged():
    """A single dash (no underscores) should be returned identically."""
    assert dasherize("-") == "-"


def test_dasherize_preserves_alphanumeric_characters():
    """Digits and letters that are not underscores should be preserved exactly."""
    assert dasherize("test_123_abc") == "test-123-abc"


def test_dasherize_preserves_existing_dashes():
    """Dashes already present in the string should be left untouched."""
    # Only underscores are transformed; existing dashes are preserved.
    assert dasherize("a_b-c_d") == "a-b-c-d"


def test_dasherize_preserves_unicode_characters():
    """Unicode characters that are not underscores should be preserved exactly."""
    # The function only does a literal '_' -> '-' substitution, no Unicode normalization.
    assert dasherize("caf\u00e9_na\u00efve") == "caf\u00e9-na\u00efve"


def test_dasherize_preserves_whitespace():
    """Spaces, tabs, and other whitespace should be preserved untouched."""
    assert dasherize("hello world_foo bar") == "hello world-foo bar"


def test_dasherize_returns_str_type():
    """The return value must always be a str, regardless of input contents."""
    result = dasherize("foo_bar")
    assert isinstance(result, str)


def test_dasherize_does_not_mutate_input_string():
    """Strings are immutable; dasherize must not modify the caller's string."""
    original = "foo_bar"
    result = dasherize(original)
    assert original == "foo_bar"
    assert result == "foo-bar"
    assert result is not original


def test_dasherize_raises_on_integer_input():
    """Non-string inputs (e.g. int) lack a .replace method, so AttributeError should be raised."""
    with pytest.raises(AttributeError):
        dasherize(123)


def test_dasherize_raises_on_none_input():
    """None has no .replace method, so dasherize(None) should raise AttributeError."""
    with pytest.raises(AttributeError):
        dasherize(None)


def test_dasherize_raises_on_list_input():
    """A list has no .replace method, so dasherize(<list>) should raise AttributeError."""
    with pytest.raises(AttributeError):
        dasherize(["foo_bar"])
