import pytest
from inflection import parameterize

def test_parameterize_docstring_example():
    """Primary happy path: validates the documented example from the docstring.

    Confirms that parameterize("Donald E. Knuth") returns "donald-e-knuth".
    """
    assert parameterize("Donald E. Knuth") == "donald-e-knuth"

def test_parameterize_returns_lowercase():
    """Validates that the result of parameterize is always in lowercase.

    Mixed-case input should always be normalized to lowercase output.
    """
    result = parameterize("Mixed Case")
    assert result == result.lower()
    assert result == "mixed-case"

@pytest.mark.parametrize("input_str,expected", [
    ("hello!!!world", "hello-world"),
    ("hello---world", "hello-world"),
    ("hello   world", "hello-world"),
    ("hello???world", "hello-world"),
])
def test_parameterize_collapses_consecutive(input_str, expected):
    """Validates that runs of consecutive non-allowed chars or separators collapse to a single separator.

    The regex `[^a-z0-9\\-_]+` matches the entire run and replaces once,
    then the `separator{2,}` regex further reduces any remaining runs.
    """
    assert parameterize(input_str) == expected

@pytest.mark.parametrize("input_str,expected", [
    ("---hello", "hello"),
    ("hello---", "hello"),
    ("---hello---", "hello"),
    ("!@#hello", "hello"),
    ("hello!@#", "hello"),
])
def test_parameterize_strips_separators_at_edges(input_str, expected):
    """Validates that leading and/or trailing separator characters are stripped.

    The regex `^(sep)|(sep)$` removes any separator at the start or end.
    """
    assert parameterize(input_str) == expected

@pytest.mark.parametrize("input_str,expected", [
    ("test_string", "test_string"),
    ("test-string", "test-string"),
    ("hello 123", "hello-123"),
    ("abc123", "abc123"),
    ("a__b", "a__b"),
    ("a_b-c", "a_b-c"),
])
def test_parameterize_preserves_allowed_characters(input_str, expected):
    """Validates that underscores, dashes, and digits are preserved in the output.

    These characters are in the allowed set `[a-z0-9\\-_]` (with case-insensitive flag).
    """
    assert parameterize(input_str) == expected

@pytest.mark.parametrize("input_str,expected", [
    ("hello@world", "hello-world"),
    ("hello,world", "hello-world"),
    ("hello!world", "hello-world"),
    ("hello?world", "hello-world"),
    ("hello.world", "hello-world"),
    ("hello\tworld", "hello-world"),
    ("hello\nworld", "hello-world"),
])
def test_parameterize_replaces_special_characters(input_str, expected):
    """Validates that various non-allowed characters are replaced with the separator."""
    assert parameterize(input_str) == expected

def test_parameterize_custom_separator_underscore():
    """Validates that a custom underscore separator is used instead of the default."""
    assert parameterize("Hello World", "_") == "hello_world"

def test_parameterize_custom_separator_period():
    """Validates that a custom period separator is used instead of the default."""
    assert parameterize("Hello World", ".") == "hello.world"

def test_parameterize_custom_separator_collapses_consecutive():
    """Validates that the custom separator is also collapsed when it occurs multiple times in a row."""
    assert parameterize("hello!!!world", "_") == "hello_world"

def test_parameterize_custom_separator_strips_edges():
    """Validates that the custom separator is also stripped from the start and end."""
    assert parameterize("!!!hello!!!", "_") == "hello"

def test_parameterize_custom_separator_replaces_existing_default_separator():
    """Hyphens are always allowed characters and pass through unchanged,
    even when a different separator is requested.
    """
    assert parameterize("hello-world", "_") == "hello-world"

def test_parameterize_empty_separator_removes_characters():
    """Validates that an empty separator removes the special characters entirely."""
    assert parameterize("hello world!", "") == "helloworld"

def test_parameterize_empty_separator_skips_post_processing():
    """Validates that with an empty separator, the collapse/strip block is skipped.

    An empty string is falsy, so the `if separator:` block does not run.
    As a consequence, no leading/trailing cleanup happens.
    """
    # With empty separator, the surrounding '!' chars are removed, but no edge stripping
    assert parameterize("!hello!", "") == "hello"

def test_parameterize_empty_string_returns_empty_string():
    """Validates that an empty input string returns an empty string."""
    assert parameterize("") == ""

def test_parameterize_only_special_characters_returns_empty_string():
    """Validates that a string of only special characters collapses to an empty string.

    All characters are non-allowed, replaced with separator, then stripped at edges.
    """
    assert parameterize("!@#$%") == ""

def test_parameterize_transliterates_accents_to_ascii():
    """Validates that accented characters are transliterated to ASCII before parameterization.

    The 'é' character should be transliterated to 'e', giving the result 'cafe'.
    """
    result = parameterize("café")
    assert "é" not in result
    assert result.isascii()
    assert result == "cafe"

def test_parameterize_transliterates_then_separates():
    """Validates that transliteration happens before separator replacement.

    'Café au lait' should first become 'Cafe au lait' then 'cafe-au-lait'.
    """
    result = parameterize("Café au lait")
    assert "é" not in result
    assert result.isascii()
    assert result == "cafe-au-lait"

def test_parameterize_returns_string_type():
    """Validates that the return value is always a string instance, regardless of input."""
    assert isinstance(parameterize("anything"), str)
    assert isinstance(parameterize(""), str)
    assert isinstance(parameterize("!@#"), str)
    assert isinstance(parameterize("hello world"), str)

@pytest.mark.parametrize("non_string", [123, None, [], {}, 1.5])
def test_parameterize_non_string_input_raises_error(non_string):
    """Validates that passing a non-string input raises a TypeError or AttributeError.

    The function ultimately calls .lower() and relies on transliterate(),
    either of which will fail on a non-string input.
    """
    with pytest.raises((TypeError, AttributeError)):
        parameterize(non_string)

@pytest.mark.parametrize("input_str,expected", [
    ("Hello World", "hello-world"),
    ("Foo Bar Baz", "foo-bar-baz"),
    ("UPPERCASE", "uppercase"),
    ("Mixed CaSe", "mixed-case"),
    ("   spaces   ", "spaces"),
    ("trailing space ", "trailing-space"),
    (" leading space", "leading-space"),
    ("a-b-c", "a-b-c"),
    ("a---b", "a-b"),
    ("abc123", "abc123"),
    ("123 numbers here", "123-numbers-here"),
    ("hello world!", "hello-world"),
    ("foo & bar", "foo-bar"),
])
def test_parameterize_various_inputs(input_str, expected):
    """Comprehensive parameterized coverage of various input strings using the default separator."""
    assert parameterize(input_str) == expected
