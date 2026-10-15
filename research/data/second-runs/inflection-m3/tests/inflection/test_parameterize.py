import pytest
from inflection import parameterize

def test_parameterize_docstring_example():
    """Primary happy path: 'Donald E. Knuth' -> 'donald-e-knuth'."""
    assert parameterize("Donald E. Knuth") == "donald-e-knuth"


def test_parameterize_replaces_spaces_with_default_separator():
    """Spaces in the input string are replaced with the default separator '-'."""
    assert parameterize("hello world") == "hello-world"


def test_parameterize_collapses_consecutive_separators():
    """Multiple consecutive separators in the result are collapsed into a single separator.

    The hyphen is allowed, the space becomes '-', producing '--' which the
    collapse step reduces to '-'.
    """
    assert parameterize("hello- world") == "hello-world"


def test_parameterize_collapses_runs_of_special_characters_into_single_separator():
    """A run of non-alphanumeric characters becomes a single separator."""
    assert parameterize("hello!!!world") == "hello-world"


def test_parameterize_strips_leading_separator():
    """Leading separator characters are removed from the result."""
    assert parameterize("!!!hello") == "hello"


def test_parameterize_strips_trailing_separator():
    """Trailing separator characters are removed from the result."""
    assert parameterize("hello!!!") == "hello"


def test_parameterize_strips_both_leading_and_trailing_separators():
    """Both leading and trailing separator characters are removed from the result."""
    assert parameterize("!!!hello!!!") == "hello"


def test_parameterize_preserves_underscores():
    """Underscores are allowed characters and are preserved in the output."""
    assert parameterize("hello_world") == "hello_world"


def test_parameterize_uses_custom_single_character_separator():
    """A custom single-character separator is used to replace special characters."""
    assert parameterize("hello world", "_") == "hello_world"


def test_parameterize_collapses_consecutive_custom_separators():
    """Consecutive runs of a custom separator character are collapsed into one."""
    assert parameterize("hello___world", "_") == "hello_world"


def test_parameterize_uses_custom_multi_character_separator():
    """A multi-character custom separator is used to replace special characters."""
    assert parameterize("hello world foo", "--") == "hello--world--foo"


def test_parameterize_with_empty_separator_does_not_trim_boundary_hyphens():
    """An empty separator does not trim boundary characters.

    The `if separator:` branch is skipped, so the leading and trailing
    hyphens are preserved as-is.
    """
    assert parameterize("---hello---", "") == "---hello---"


def test_parameterize_with_empty_separator_removes_interior_special_characters():
    """An empty separator causes interior special characters to be removed entirely."""
    assert parameterize("a!!!b", "") == "ab"


def test_parameterize_with_empty_string_returns_empty_string():
    """An empty input string returns an empty string."""
    assert parameterize("") == ""


def test_parameterize_transliterates_unicode_characters_to_ascii():
    """Non-ASCII characters are transliterated to their ASCII approximation.

    'é' (U+00E9) is decomposed via NFKD, the combining mark is dropped by
    ASCII encoding, and the result is the bare ASCII 'e'.
    """
    assert parameterize("Café") == "cafe"


def test_parameterize_lowercases_the_result():
    """The result is converted to lowercase, even when the input is uppercase."""
    assert parameterize("HELLO World") == "hello-world"


def test_parameterize_string_of_only_special_characters_becomes_empty():
    """A string consisting only of special characters becomes an empty string after trimming."""
    assert parameterize("!!!") == ""


def test_parameterize_preserves_alphanumeric_characters():
    """Letters and digits are preserved in the output."""
    assert parameterize("Item123") == "item123"


def test_parameterize_preserves_existing_hyphens():
    """Existing hyphens in the input are preserved as part of the result."""
    assert parameterize("already-hyphenated") == "already-hyphenated"


def test_parameterize_handles_tabs_and_newlines_as_special_characters():
    """Tab and newline characters are treated as non-alphanumeric and become the separator."""
    assert parameterize("hello\tworld\n") == "hello-world"


def test_parameterize_returns_str_type():
    """The function returns a string."""
    assert isinstance(parameterize("Hello World"), str)


def test_parameterize_with_regex_special_character_separator_trims_correctly():
    """A separator containing regex special characters is properly escaped during trimming.

    '.' is a regex special character; `re.escape` ensures the trim regex
    matches a literal period, not 'any character'.
    """
    assert parameterize("hello.world.", ".") == "hello.world"


def test_parameterize_with_regex_special_character_separator_collapses():
    """Consecutive runs of a regex special separator character are collapsed into one."""
    assert parameterize("hello..world", ".") == "hello.world"


def test_parameterize_raises_typeerror_for_non_string_input():
    """Passing a non-string input raises a TypeError (transliterate requires a str)."""
    with pytest.raises(TypeError):
        parameterize(123)

