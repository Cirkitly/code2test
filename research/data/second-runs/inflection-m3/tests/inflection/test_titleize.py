import pytest
from inflection import titleize

def test_titleize_simple_lowercase_phrase():
    """A lowercase phrase becomes title-cased.

    Tracing titleize('man from the boondocks'):
      - underscore -> 'man_from_the_boondocks'
      - humanize -> 'Man from the boondocks'
      - .title()  -> 'Man From The Boondocks'
      - re.sub:   no change (already capitalized)
    """
    assert titleize("man from the boondocks") == "Man From The Boondocks"

def test_titleize_handles_hyphens_and_colons():
    """Hyphens become spaces; colons are preserved.

    Tracing titleize('x-men: the last stand'):
      - underscore: replace '-' with '_' and ' ' with '_'
                    -> 'x_men:_the_last_stand'
      - humanize: replace '_' with ' ', capitalize first
                  -> 'X men: the last stand'
      - .title(): -> 'X Men: The Last Stand'
      - re.sub:    no change
    """
    result = titleize("x-men: the last stand")
    assert result == "X Men: The Last Stand"
    assert ":" in result
    assert "x-men" not in result
    assert "X-Men" not in result

def test_titleize_camelcase_input_is_split():
    """CamelCase input is split on case boundaries.

    Tracing titleize('TheManWithoutAPast'):
      - underscore: inject '_' at [a-z][A-Z] boundaries and lowercase
                    -> 'the_man_without_a_past'
      - humanize -> 'The man without a past'
      - .title() -> 'The Man Without A Past'
    """
    assert titleize("TheManWithoutAPast") == "The Man Without A Past"

def test_titleize_snake_case_input():
    """snake_case underscores become spaces.

    Tracing titleize('raiders_of_the_lost_ark'):
      - underscore leaves underscores in place but lowercases
      - humanize replaces '_' with ' ' and capitalizes first word
                    -> 'Raiders of the lost ark'
      - .title() -> 'Raiders Of The Lost Ark'
    """
    result = titleize("raiders_of_the_lost_ark")
    assert result == "Raiders Of The Lost Ark"
    assert "_" not in result

def test_titleize_empty_string_returns_empty_string():
    """Empty input yields empty output.

    Tracing titleize(''):
      - underscore('') -> ''
      - humanize('')   -> ''
      - ''.title()     -> ''
      - re.sub(..., '') -> ''
    """
    assert titleize("") == ""

def test_titleize_returns_a_string():
    """Return type is always ``str``."""
    for sample in ("hello world", "", "HELLO_WORLD", "ManFromNowhere"):
        result = titleize(sample)
        assert isinstance(result, str)

def test_titleize_uppercase_input_is_normalized():
    """ALL CAPS input is normalized to title case, not preserved.

    Tracing titleize('HELLO WORLD'):
      - underscore('HELLO WORLD') -> 'hello_world'
      - humanize -> 'Hello world'
      - .title() -> 'Hello World'
    """
    result = titleize("HELLO WORLD")
    assert result == "Hello World"
    # Ensure the result is NOT the same as the (lowercased) input.
    assert result != "hello world"
    # Each word's first letter is uppercase, the rest are not all upper.
    words = result.split()
    for word in words:
        assert word[0].isupper()
        assert not word.isupper() or len(word) == 1

def test_titleize_hyphen_separated_words_become_separate_words():
    """Hyphens act as word separators that become spaces.

    Tracing titleize('hello-world'):
      - underscore: replace '-' with '_' -> 'hello_world'
      - humanize -> 'Hello world'
      - .title() -> 'Hello World'
    """
    result = titleize("hello-world")
    assert result == "Hello World"
    assert "-" not in result
    # Two distinct words, both capitalized.
    parts = result.split()
    assert len(parts) == 2
    assert parts[0] == "Hello"
    assert parts[1] == "World"

def test_titleize_is_idempotent_on_already_titlecased_output():
    """titleize(titleize(x)) == titleize(x).

    Tracing titleize('Man From The Boondocks'):
      - underscore: replace ' ' with '_' and lowercase
                    -> 'man_from_the_boondocks'
      - humanize -> 'Man from the boondocks'
      - .title() -> 'Man From The Boondocks'
    """
    once = titleize("man from the boondocks")
    twice = titleize(once)
    assert once == twice
    assert twice == "Man From The Boondocks"
    # Also confirm idempotency for the CamelCase-derived output.
    camel_once = titleize("TheManWithoutAPast")
    camel_twice = titleize(camel_once)
    assert camel_once == camel_twice

def test_titleize_first_letter_is_capitalized():
    """The first letter of the result is always uppercase."""
    for sample in ("a", "hello", "foo bar", "HELLO WORLD", "snake_case", "ALSO_CAPS"):
        result = titleize(sample)
        assert result and result[0].isupper(), (
            f"Expected first char upper for input {sample!r}, got {result!r}"
        )

def test_titleize_preserves_word_count():
    """The output has the same number of whitespace-separated words.

    For 'man from the boondocks' the underscore pass yields
    'man_from_the_boondocks' (4 word fragments); after humanize and
    .title() we still have 4 space-separated words.
    """
    input_str = "man from the boondocks"
    output = titleize(input_str)
    assert len(output.split()) == len(input_str.split())
    assert len(output.split()) == 4
