import pytest
from inflection import titleize

def test_titleize_documented_example_man_from_the_boondocks():
    """'man from the boondocks' -> 'Man From The Boondocks' (docstring example)."""
    from inflection import titleize

    assert titleize("man from the boondocks") == "Man From The Boondocks"

def test_titleize_documented_example_x_men_colon_the_last_stand():
    """'x-men: the last stand' -> 'X Men: The Last Stand' (docstring example)."""
    from inflection import titleize

    assert titleize("x-men: the last stand") == "X Men: The Last Stand"

def test_titleize_documented_example_the_man_without_a_past():
    """'TheManWithoutAPast' -> 'The Man Without A Past' (docstring example)."""
    from inflection import titleize

    assert titleize("TheManWithoutAPast") == "The Man Without A Past"

def test_titleize_documented_example_raiders_of_the_lost_ark():
    """'raiders_of_the_lost_ark' -> 'Raiders Of The Lost Ark' (docstring example)."""
    from inflection import titleize

    assert titleize("raiders_of_the_lost_ark") == "Raiders Of The Lost Ark"

def test_titleize_returns_a_string():
    """titleize always returns a str for a str input."""
    from inflection import titleize

    assert isinstance(titleize("hello world"), str)

def test_titleize_empty_string_returns_empty_string():
    """An empty string has no words to capitalize, so it stays empty."""
    from inflection import titleize

    assert titleize("") == ""

def test_titleize_single_word_is_capitalized():
    """A lone word is capitalized without any separator processing."""
    from inflection import titleize

    assert titleize("hello") == "Hello"

def test_titleize_keeps_existing_capitalization_of_acronyms():
    """Fully capitalized tokens such as 'NASA' stay uppercase in the title."""
    from inflection import titleize

    assert titleize("nasa and nasa") == "Nasa And Nasa"

def test_titleize_preserves_leading_apostrophes_on_capitalized_words():
    """A leading apostrophe is kept and the following letter is capitalized."""
    from inflection import titleize

    assert titleize("o'clock") == "O'clock"

def test_titleize_leaves_non_alphabetic_characters_untouched():
    """Punctuation that is not a word character is passed through unchanged."""
    from inflection import titleize

    result = titleize("hello!")

    assert isinstance(result, str)
    assert result.endswith("!")
    assert result.startswith("Hello")

def test_titleize_does_not_mutate_input_string():
    """The original string object passed in is unchanged after titleization."""
    from inflection import titleize

    original = "the man without a past"
    result = titleize(original)

    assert original == "the man without a past"
    assert result == "The Man Without A Past"

def test_titleize_replaces_hyphens_with_spaces():
    """Hyphens become spaces, producing individual capitalized words."""
    from inflection import titleize

    assert titleize("state-of-the-art") == "State Of The Art"

def test_titleize_replaces_underscores_with_spaces():
    """Underscores become spaces and each resulting word is capitalized."""
    from inflection import titleize

    assert titleize("hello_world") == "Hello World"

import pytest


@pytest.mark.parametrize(
    "value,expected",
    [
        ("man from the boondocks", "Man From The Boondocks"),
        ("x-men: the last stand", "X Men: The Last Stand"),
        ("TheManWithoutAPast", "The Man Without A Past"),
        ("raiders_of_the_lost_ark", "Raiders Of The Lost Ark"),
    ],
)
def test_titleize_all_documented_examples_together(value, expected):
    """Every example in the docstring behaves exactly as advertised."""
    from inflection import titleize

    assert titleize(value) == expected
