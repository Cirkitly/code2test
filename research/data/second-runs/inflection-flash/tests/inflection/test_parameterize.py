import re
import unicodedata
import pytest
from inflection import parameterize

def test_parameterize_converts_spaces_to_dashes_and_lowercases():
    """The documented example: spaces become dashes and the result is lowercased."""
    assert parameterize(u"Donald E. Knuth") == 'donald-e-knuth'

def test_parameterize_replaces_punctuation_with_separator():
    """Punctuation is unwanted; a run of it becomes exactly one separator."""
    # '!' is replaced by '-', then the trailing '-' is stripped.
    assert parameterize("Hello world!") == 'hello-world'
    # A run of punctuation between words collapses to a single separator.
    assert parameterize("one!!!two") == 'one-two'

def test_parameterize_preserves_allowed_alphanumerics_digits_underscores_and_dashes():
    """Letters, digits, underscores and dashes are allowed and pass through."""
    assert parameterize("abc123") == 'abc123'
    # Underscores are an allowed character, so they survive untouched.
    assert parameterize("hello_world") == 'hello_world'
    # Existing dashes are allowed characters and are preserved.
    assert parameterize("already-dashed") == 'already-dashed'
    # Digits are preserved even at the start of the string.
    assert parameterize("100 Cotton") == '100-cotton'

def test_parameterize_does_not_collapse_allowed_underscores():
    """Only the separator is collapsed; underscores are allowed characters."""
    # '_' is in the allowed set [^a-z0-9\\-_] so it is never replaced or collapsed.
    assert parameterize("hello___world") == 'hello___world'

def test_parameterize_removes_leading_and_trailing_separator():
    """Leading and trailing separator characters are removed from the output."""
    assert parameterize("  spaced out  ") == 'spaced-out'
    assert parameterize("!!!leading") == 'leading'
    assert parameterize("trailing!!!") == 'trailing'

def test_parameterize_collapses_repeated_separators():
    """Runs of two or more separators are reduced to a single separator."""
    # Adjacent replaced groups produce '-', and existing dashes stay, giving '---',
    # which is collapsed to '-'.
    assert parameterize("a - b") == 'a-b'
    assert parameterize("a--b") == 'a-b'
    assert parameterize("a - - b") == 'a-b'

def test_parameterize_strips_separator_only_string_to_empty():
    """A string consisting only of separators yields an empty string after stripping."""
    # '-' is an allowed character, so '---' collapses to '-' and is then stripped.
    assert parameterize("---") == ''
    # ' ' is unwanted, becomes '-', which is then stripped from both ends.
    assert parameterize("   ") == ''

def test_parameterize_returns_empty_string_for_empty_input():
    """Empty input produces an empty output without raising."""
    result = parameterize("")
    assert result == ''
    assert isinstance(result, str)

def test_parameterize_result_always_lowercase():
    """The returned string is always lowercase."""
    result = parameterize("MiXeD CaSe InPuT")
    assert result == result.lower()
    assert result == 'mixed-case-input'

def test_parameterize_transliterates_non_ascii_characters():
    """Non-ASCII input is transliterated to its ASCII approximation."""
    # Accented letters transliterate to plain ASCII letters.
    assert parameterize(u"Ünïcödé Tëst") == 'unicode-test'
    # 'ü' transliterates to 'u', while 'ß' has no ASCII decomposition and is
    # dropped entirely (not expanded to 'ss'). Spaces become the separator.
    assert parameterize(u"Grüße über alles") == 'grue-uber-alles'

def test_parameterize_with_custom_underscore_separator():
    """A custom separator is used for replacement, collapsing and stripping."""
    assert parameterize("Donald E. Knuth", "_") == 'donald_e_knuth'
    assert parameterize("  spaced out  ", "_") == 'spaced_out'
    # Existing '_' characters are allowed, so repeated '_' runs are collapsed
    # because '_' is now the separator.
    assert parameterize("a___b", "_") == 'a_b'

def test_parameterize_with_custom_separator_containing_regex_metacharacters():
    """Regex-special separators are escaped and therefore work literally."""
    assert parameterize("a b c", ".") == 'a.b.c'
    assert parameterize("a+b", "+") == 'a+b'
    assert parameterize("a/b", "/") == 'a/b'
    # Leading/trailing separators built from metacharacters are still stripped.
    assert parameterize(" x y ", ".") == 'x.y'

def test_parameterize_with_empty_separator_removes_unwanted_characters():
    """With separator='' every unwanted character is simply removed."""
    # The substitution deletes the spaces and the cleanup block is skipped.
    assert parameterize("Donald E. Knuth", "") == 'donaldeknuth'
    assert parameterize("!!!", "") == ''
    assert parameterize("a b", "") == 'ab'

def test_parameterize_with_single_character_separator():
    """A multi-character separator is inserted verbatim into the result."""
    assert parameterize("a b", "__") == 'a__b'
    # A run of unwanted characters maps to one full separator occurrence.
    assert parameterize("a    b", "__") == 'a__b'

def test_parameterize_output_contains_no_unescaped_whitespace_or_specials():
    """Property check: the result is 'pretty URL' safe."""
    result = parameterize("  Hello, World! (v2.0) @ Home?  ")
    assert isinstance(result, str)
    # No whitespace or other special characters survive.
    assert not any(ch.isspace() for ch in result)
    assert all(ch.isalnum() or ch in '-_' for ch in result)
    # The result never starts or ends with the separator.
    assert not result.startswith('-')
    assert not result.endswith('-')

def test_parameterize_output_never_has_consecutive_separators():
    """Property check: the 'no more than one separator in a row' rule holds."""
    messy = "a  b   c????d----e---f  "
    result = parameterize(messy)
    assert '--' not in result
    assert not result.startswith('-')
    assert not result.endswith('-')

def test_parameterize_is_idempotent_for_default_separator():
    """Property check: parameterizing an already-clean string changes nothing."""
    once = parameterize("Some Fancy Title! -- Part #2")
    assert parameterize(once) == once

def test_parameterize_handles_url_like_input():
    """Realistic 'pretty URL' usage: turn a phrase into a URL fragment."""
    assert parameterize("The Quick Brown Fox") == 'the-quick-brown-fox'
    assert parameterize("  Multiple   spaces   here ") == 'multiple-spaces-here'
    assert parameterize("C# Programming 101") == 'c-programming-101'

def test_parameterize_raises_type_error_for_non_string_input():
    """Non-string input raises TypeError rather than silently succeeding."""
    with pytest.raises(TypeError):
        parameterize(None)
    with pytest.raises(TypeError):
        parameterize(123)

def test_parameterize_raises_type_error_for_non_string_separator():
    """A non-string separator is rejected by the regex substitution step."""
    with pytest.raises(TypeError):
        parameterize("hello world", 1)

def test_parameterize_returns_str_for_various_inputs():
    """Type contract: parameterize always returns a str."""
    for value in ["", "a", "A B", "123", u"ü", "!!!", "a-b_c"]:
        result = parameterize(value)
        assert isinstance(result, str)
