import pytest
from inflection import titleize

def test_titleize_simple_sentence():
    """Titleize a simple lowercase space-separated sentence (primary happy path).

    This is the first example from the function's docstring.
    """
    assert titleize("man from the boondocks") == "Man From The Boondocks"

def test_titleize_hyphen_and_colon():
    """Titleize a string with hyphenated words and a colon.

    Hyphens are replaced with spaces; the colon is preserved.
    This is the second docstring example.
    """
    assert titleize("x-men: the last stand") == "X Men: The Last Stand"

def test_titleize_camelcase_input():
    """Titleize a CamelCase input by recognizing word boundaries at case changes.

    This is the third docstring example.
    """
    assert titleize("TheManWithoutAPast") == "The Man Without A Past"

def test_titleize_snake_case_input():
    """Titleize a snake_case input by replacing underscores with spaces.

    This is the fourth docstring example.
    """
    assert titleize("raiders_of_the_lost_ark") == "Raiders Of The Lost Ark"

def test_titleize_returns_str_type():
    """Verify that titleize returns a str for valid string input."""
    assert isinstance(titleize("hello"), str)

def test_titleize_empty_string_returns_empty():
    """Titleize of an empty string returns an empty string."""
    assert titleize("") == ""

def test_titleize_single_lowercase_word():
    """A single lowercase word has its first letter capitalized."""
    assert titleize("hello") == "Hello"

def test_titleize_single_uppercase_word():
    """A single all-uppercase word is normalized to title case."""
    assert titleize("HELLO") == "Hello"

def test_titleize_already_titlecased_is_unchanged():
    """Titleize does not change a string that is already in title case."""
    assert titleize("Man From The Boondocks") == "Man From The Boondocks"

def test_titleize_is_idempotent():
    """Titleize is idempotent: applying it twice yields the same result as once."""
    once = titleize("the_lord_of_the_rings")
    twice = titleize(once)
    assert once == twice
    assert once == "The Lord Of The Rings"

def test_titleize_with_numbers_between_words():
    """Titleize preserves digits in the middle of a phrase."""
    assert titleize("version 2 release") == "Version 2 Release"

def test_titleize_mixed_case_input():
    """Titleize normalizes mixed-case input to consistent title case."""
    assert titleize("MAN from boondocks") == "Man From Boondocks"

def test_titleize_hyphenated_single_word():
    """Titleize splits a hyphenated word into separate words."""
    assert titleize("x-men") == "X Men"

def test_titleize_preserves_consecutive_spaces():
    """Multiple consecutive spaces between words are preserved in the output."""
    assert titleize("hello   world") == "Hello   World"

def test_titleize_preserves_leading_and_trailing_spaces():
    """Leading and trailing whitespace is preserved in the output."""
    assert titleize("  hello  ") == "  Hello  "

def test_titleize_with_apostrophe_in_word():
    """Titleize handles an apostrophe in a contraction.

    Documents the function's behavior with apostrophes: the letter
    after the apostrophe is NOT capitalized. The regex captures the
    apostrophe along with the following letter in the match group,
    and Python's str.capitalize on a string starting with an
    apostrophe ("'t") leaves the following letter unchanged.
    """
    assert titleize("don't stop") == "Don't Stop"


def test_titleize_preserves_trailing_punctuation():
    """Titleize preserves trailing punctuation such as exclamation marks."""
    assert titleize("hello world!") == "Hello World!"

def test_titleize_with_integer_input_raises_type_error():
    """Titleize raises TypeError when given a non-string integer input."""
    with pytest.raises(TypeError):
        titleize(123)

def test_titleize_with_none_input_raises_type_error():
    """Titleize raises TypeError when given None as input."""
    with pytest.raises(TypeError):
        titleize(None)
