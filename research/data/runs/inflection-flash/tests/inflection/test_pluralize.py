import pytest
import unicodedata
from inflection import pluralize

@pytest.fixture
def singular_word() -> str:
    """A plain singular noun used as the baseline input in several tests."""
    return "word"


@pytest.fixture
def uncountable_word() -> str:
    """A noun whose singular and plural forms are identical (taken from the pluralize docstring)."""
    return "sheep"

def test_pluralize_appends_s_to_a_regular_word(singular_word):
    """Happy path: a plain singular noun simply gains a trailing 's'."""
    result = pluralize(singular_word)

    assert result == "words"

@pytest.mark.parametrize(
    "word,expected",
    [
        ("apple", "apples"),
        ("dog", "dogs"),
        ("car", "cars"),
        ("table", "tables"),
    ],
)
def test_pluralize_appends_s_to_variety_of_simple_nouns(word, expected):
    """Regular nouns that match no special rule are pluralized with a trailing 's'."""
    assert pluralize(word) == expected

def test_pluralize_keeps_words_already_ending_in_s_unchanged():
    """Docstring example: pluralize("posts") == 'posts' (no double 's')."""
    assert pluralize("posts") == "posts"

def test_pluralize_returns_uncountable_words_unchanged(uncountable_word):
    """Uncountable nouns (like 'sheep') have no distinct plural form and are returned as-is."""
    result = pluralize(uncountable_word)

    assert result == uncountable_word
    assert result == "sheep"

@pytest.mark.parametrize("word", ["Sheep", "SHEEP", "sHeep"])
def test_pluralize_detects_uncountables_case_insensitively(word):
    """Uncountable lookup uses word.lower(), so casing must not change the result."""
    assert pluralize(word) == word

def test_pluralize_returns_empty_string_for_empty_word():
    """An empty string is falsy, so it is returned unchanged without raising."""
    result = pluralize("")

    assert result == ""
    assert isinstance(result, str)
    assert len(result) == 0

def test_pluralize_applies_irregular_rule_for_octopus():
    """Docstring example: pluralize("octopus") == 'octopi' via the specific octop|vir rule."""
    result = pluralize("octopus")

    assert result == "octopi"
    assert result != "octopuss"

def test_pluralize_preserves_capitalization_of_irregular_rule():
    """Docstring example: pluralize("CamelOctopus") == 'CamelOctopi' — only the stem is replaced."""
    result = pluralize("CamelOctopus")

    assert result == "CamelOctopi"
    assert result[0] == "C"
    assert result.startswith("CamelOctop")

def test_pluralize_keeps_already_plural_irregular_word_unchanged():
    """Already-plural irregular words are stable: pluralize("octopi") == 'octopi'."""
    result = pluralize("octopi")

    assert result == "octopi"
    assert pluralize(result) == result

def test_pluralize_is_idempotent_for_regular_words():
    """Applying pluralize twice must not stack suffixes: "word" -> "words" -> "words"."""
    once = pluralize("word")
    twice = pluralize(once)

    assert once == "words"
    assert twice == once

def test_pluralize_converts_consonant_plus_y_to_ies():
    """The consonant+'y' rule replaces the 'y' with 'ies'."""
    result = pluralize("company")

    assert result == "companies"
    assert result.endswith("ies")

def test_pluralize_appends_es_after_sibilant_endings():
    """Words ending in x/ch/ss/sh take '-es' rather than a bare 's'."""
    result = pluralize("church")

    assert result == "churches"
    assert result.endswith("es")

def test_pluralize_handles_camel_case_regular_word():
    """Camel-cased input is pluralized at the end, leaving the prefix untouched."""
    result = pluralize("CamelWord")

    assert result == "CamelWords"
    assert result.startswith("Camel")

def test_pluralize_returns_a_string_object(singular_word):
    """pluralize is annotated as str -> str, so the result must be a str instance."""
    result = pluralize(singular_word)

    assert isinstance(result, str)
    assert type(result) is str

@pytest.mark.parametrize("word", ["c++", "(", "a.b", "data[0]"])
def test_pluralize_handles_words_with_regex_metacharacters(word):
    """Regex metacharacters in the input must not break matching or substitution."""
    result = pluralize(word)

    assert isinstance(result, str)
    assert result.startswith(word)
    assert result.endswith("s")

def test_pluralize_handles_non_ascii_word():
    """A word with accented characters is pluralized without losing its letters."""
    result = pluralize("café")

    assert isinstance(result, str)
    assert result.startswith("caf")
    assert result.endswith("s")
    assert unicodedata.normalize("NFC", result) == result

def test_pluralize_raises_error_for_truthy_non_string_input():
    """A truthy non-string input has no .lower(), so an error surfaces instead of a bogus plural."""
    with pytest.raises((AttributeError, TypeError)):
        pluralize(42)

def test_pluralize_returns_falsy_non_string_input_unchanged():
    """Falsy inputs short-circuit the rule loop and are echoed back unchanged."""
    assert pluralize(None) is None
    assert pluralize(0) == 0
