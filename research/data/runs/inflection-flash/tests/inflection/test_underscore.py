import pytest
from inflection import underscore
from inflection import camelize

from inflection import underscore


def test_underscore_converts_pascal_case_to_snake_case():
    """The documented primary example turns a CamelCase word into snake_case."""
    assert underscore("DeviceType") == "device_type"


def test_underscore_converts_single_camel_case_word():
    """A single lowercase-initial CamelCase word is split into two lowercase parts."""
    assert underscore("camelCase") == "camel_case"


def test_underscore_lowercases_plain_lowercase_input_unchanged():
    """An already lowercase word with no separators is returned unchanged."""
    assert underscore("word") == "word"


def test_underscore_keeps_existing_underscores():
    """Existing underscores act as the word separator and are preserved."""
    assert underscore("already_underscored") == "already_underscored"


def test_underscore_replaces_dashes_with_underscores():
    """Dashes are normalized into underscores, matching the '-' -> '_' replacement step."""
    assert underscore("foo-bar") == "foo_bar"

from inflection import underscore, camelize


def test_underscore_handles_consecutive_uppercase_letters():
    """A run of uppercase letters followed by a capitalized word is split correctly.

    ``IOError`` -> first regex makes it ``IO_Error`` -> lowered to ``io_error``.
    """
    assert underscore("IOError") == "io_error"


def test_underscore_is_not_a_perfect_inverse_of_camelize_for_acronyms():
    """Documents the documented caveat: round-tripping an acronym loses information."""
    assert camelize(underscore("IOError")) == "IoError"


def test_underscore_all_uppercase_word_is_only_lowercased():
    """A fully uppercase word has no lowercase/digit boundary, so it is only lowercased."""
    assert underscore("RUBY") == "ruby"


def test_underscore_splits_uppercase_acronym_before_final_capitalized_word():
    """'HTTPServer' -> 'HTTP_Server' -> 'http_server': the acronym boundary rule fires once."""
    assert underscore("HTTPServer") == "http_server"


def test_underscore_splits_all_capital_word_followed_by_lowercase():
    """'ABCd' matches ([A-Z]+)([A-Z][a-z]) as 'AB' + 'Cd' -> 'ab_cd'."""
    assert underscore("ABCd") == "ab_cd"

from inflection import underscore


def test_underscore_underscores_uppercase_following_digits():
    """A digit directly followed by an uppercase letter is treated as a word boundary."""
    assert underscore("version1Point0") == "version1_point0"


def test_underscore_does_not_underscore_digit_followed_by_lowercase():
    """Digits followed by lowercase letters are left alone (no boundary rule matches)."""
    assert underscore("address1") == "address1"


def test_underscore_handles_multiple_word_boundaries():
    """Several CamelCase boundaries are all converted into underscores."""
    assert underscore("FooBarBaz") == "foo_bar_baz"

from inflection import underscore


def test_underscore_returns_empty_string_for_empty_input():
    """Empty input produces an empty result rather than raising."""
    assert underscore("") == ""


def test_underscore_leaves_whitespace_and_punctuation_intact():
    """Only case, camel boundaries and dashes are touched; spaces/periods remain."""
    assert underscore("Hello World") == "hello world"
    assert underscore("foo.bar") == "foo.bar"


def test_underscore_output_is_always_lowercase():
    """Regardless of input case, the returned string is lowercase."""
    assert underscore("ALLMixedCASE").islower()
    assert underscore("MixedCase").islower()

import pytest

from inflection import underscore


def test_underscore_raises_on_non_string_input():
    """Passing a non-string raises TypeError, since the function has no coercion step."""
    with pytest.raises(TypeError):
        underscore(None)


def test_underscore_raises_type_error_for_numeric_input():
    """Numbers are not accepted; the implementation calls re.sub directly on the argument."""
    with pytest.raises(TypeError):
        underscore(123)
