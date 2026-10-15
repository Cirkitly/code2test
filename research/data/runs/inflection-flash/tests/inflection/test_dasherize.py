import pytest
from inflection import dasherize

def test_dasherize_replaces_underscore_with_dash():
    """Underscores in the input string are replaced with dashes."""
    assert dasherize("puni_puni") == "puni-puni"

def test_dasherize_leaves_word_without_underscores_unchanged():
    """A string containing no underscores is returned exactly as given."""
    assert dasherize("puni") == "puni"

def test_dasherize_returns_empty_string_for_empty_input():
    """An empty input string yields an empty output string."""
    assert dasherize("") == ""

def test_dasherize_replaces_all_occurrences_of_underscores():
    """All underscores are replaced, not just the first occurrence."""
    assert dasherize("my_dash_snake_string") == "my-dash-snake-string"

def test_dasherize_handles_string_that_is_only_underscores():
    """A string made only of underscores becomes an equal number of dashes."""
    assert dasherize("___") == "---"

def test_dasherize_handles_leading_and_trailing_underscores():
    """Leading and trailing underscores are converted to dashes."""
    assert dasherize("_leading_and_trailing_") == "-leading-and-trailing-"

def test_dasherize_handles_adjacent_underscores():
    """Runs of consecutive underscores produce runs of dashes of the same length."""
    assert dasherize("foo__bar") == "foo--bar"

def test_dasherize_preserves_characters_other_than_underscore():
    """Characters other than '_' (including dashes, spaces, digits and case) are untouched."""
    assert dasherize("Foo Bar-baz_qux_42!") == "Foo Bar-baz-qux-42!"

def test_dasherize_does_not_convert_dashes_into_underscores():
    """Existing dashes are preserved; dasherize is not the inverse of underscore()."""
    assert dasherize("already-dasherized") == "already-dasherized"

def test_dasherize_preserves_whitespace_including_newlines_and_tabs():
    """Whitespace characters such as newlines and tabs are preserved verbatim."""
    assert dasherize("foo_bar\nbaz\tqux_quux") == "foo-bar\nbaz\tqux-quux"

def test_dasherize_handles_non_ascii_characters():
    """Non-ASCII characters pass through unchanged while underscores still become dashes."""
    assert dasherize("puni_ünïcode_日本語") == "puni-ünïcode-日本語"

@pytest.mark.parametrize(
    "word",
    ["", "_", "a_b", "__leading__", "no-underscores", "foo_bar_baz"],
)
def test_dasherize_preserves_length_and_type_of_input(word):
    """The replacement is 1:1, so the output is a str with the same length as the input."""
    result = dasherize(word)

    assert isinstance(result, str)
    assert len(result) == len(word)

def test_dasherize_output_contains_no_underscores_when_input_has_none():
    """The returned string never contains underscores, whatever the input was."""
    result = dasherize("some_mixed-Case_string_123")

    assert "_" not in result

def test_dasherize_is_idempotent():
    """Calling dasherize twice equals calling it once, since dashes are not underscores."""
    once = dasherize("already_underscored")

    assert dasherize(once) == once

def test_dasherize_with_non_string_raises_attribute_error():
    """Non-string input (an int) raises AttributeError since str.replace is unavailable."""
    with pytest.raises(AttributeError):
        dasherize(123)  # type: ignore[arg-type]

def test_dasherize_with_none_raises_attribute_error():
    """None has no .replace method, so calling dasherize(None) raises AttributeError."""
    with pytest.raises(AttributeError):
        dasherize(None)  # type: ignore[arg-type]

def test_dasherize_with_bytes_raises_type_error():
    """bytes.replace only accepts bytes arguments, so passing str arguments raises TypeError."""
    with pytest.raises(TypeError):
        dasherize(b"foo_bar")  # type: ignore[arg-type]
