import pytest
from inflection import tableize
from inflection import pluralize
from inflection import underscore

@pytest.fixture
def docstring_examples():
    """The (model name, table name) pairs taken from the ``tableize`` docstring."""
    return [
        ("RawScaledScorer", "raw_scaled_scorers"),
        ("egg_and_ham", "egg_and_hams"),
        ("fancyCategory", "fancy_categories"),
    ]


@pytest.fixture
def uncountable_model_names():
    """Model names whose tableized form is unchanged because the noun is uncountable."""
    return ["Sheep", "Series", "Fish"]

import pytest

from inflection import tableize
from inflection import pluralize
from inflection import underscore


@pytest.fixture
def docstring_examples():
    """The (model name, table name) pairs taken from the ``tableize`` docstring."""
    return [
        ("RawScaledScorer", "raw_scaled_scorers"),
        ("egg_and_ham", "egg_and_hams"),
        ("fancyCategory", "fancy_categories"),
    ]


@pytest.fixture
def uncountable_model_names():
    """Model names whose tableized form is unchanged because the noun is uncountable."""
    return ["Sheep", "Series", "Fish"]


@pytest.mark.parametrize("word,expected", [
    ("RawScaledScorer", "raw_scaled_scorers"),
    ("egg_and_ham", "egg_and_hams"),
    ("fancyCategory", "fancy_categories"),
])
def test_tableize_matches_documented_examples(word, expected):
    """The examples in the docstring are reproduced exactly.

    A CamelCase model name is underscored and pluralized, a snake_case name keeps
    its underscores and only its final word is pluralized, and a lower camel case
    name is split, underscored and pluralized.
    """
    assert tableize(word) == expected


def test_tableize_documented_examples_fixture_is_consistent(docstring_examples):
    """The same three documented examples are verified through the fixture."""
    for word, expected in docstring_examples:
        assert tableize(word) == expected


def test_tableize_underscores_and_pluralizes_single_camel_case_word():
    """A single CamelCase word becomes an underscored, plural, lowercase table name."""
    # underscore('Parser') == 'parser' and pluralize('parser') == 'parsers'
    assert tableize("Parser") == "parsers"


def test_tableize_converts_simple_camel_case_model_name_to_lowercase_plural_table():
    """A simple CamelCase model name is lowercased and pluralized."""
    assert tableize("Category") == "categories"


def test_tableize_pluralizes_word_ending_in_sibilant_with_ves():
    """A noun ending in a sibilant consonant takes the ``-es`` plural form."""
    assert tableize("Box") == "boxes"


def test_tableize_keeps_consecutive_capitals_together_as_one_word():
    """An initialism followed by a regular word is split between the acronym and the word.

    'HTMLParser' -> 'HTML_Parser' (underscore) -> 'html_parsers'.
    """
    assert tableize("HTMLParser") == "html_parsers"


def test_tableize_only_pluralizes_the_last_word_of_a_multi_word_name():
    """Earlier words are merely underscored; only the final word is pluralized."""
    assert tableize("CategoryProduct") == "category_products"


def test_tableize_replaces_dashes_with_underscores():
    """Dashed names are normalized to underscored table names before pluralizing."""
    assert tableize("foo-bar") == "foo_bars"


def test_tableize_dashed_camel_case_name_combines_both_normalizations():
    """A dashed CamelCase name is underscored, then pluralized."""
    assert tableize("raw-scaled-scorer") == "raw_scaled_scorers"


def test_tableize_preserves_digits_and_underscores():
    """Digits are kept and the name is still pluralized at the end."""
    assert tableize("order_2") == "order_2s"


def test_tableize_underscores_non_ascii_names_without_stripping_characters():
    """Non-ASCII letters survive the underscoring and are simply pluralized."""
    assert tableize("Naïve") == "naïves"


def test_tableize_returns_empty_string_for_empty_input():
    """An empty model name yields an empty table name instead of raising."""
    assert tableize("") == ""


def test_tableize_returns_a_string():
    """tableize always returns a string value."""
    assert isinstance(tableize("RawScaledScorer"), str)


def test_tableize_always_returns_a_lowercase_name():
    """The produced table name is always lowercase, even for mixed-case input."""
    assert tableize("fancyCategory").islower()
    assert tableize("HTMLParser").islower()


def test_tableize_does_not_mutate_its_argument():
    """Strings are immutable; the caller's model name is left untouched."""
    model_name = "RawScaledScorer"
    tableize(model_name)
    assert model_name == "RawScaledScorer"


def test_tableize_is_idempotent_for_an_already_plural_table_name():
    """Feeding an already pluralized table name back in does not double the suffix."""
    once = tableize("RawScaledScorer")
    assert tableize(once) == once


def test_tableize_leaves_uncountable_words_unchanged(uncountable_model_names):
    """Uncountable nouns are not pluralized, so the table name equals the underscored word."""
    for word in uncountable_model_names:
        result = tableize(word)
        assert result == underscore(word)


def test_tableize_equals_pluralize_of_underscore_for_a_range_of_words():
    """tableize is exactly the pluralized, underscored form of the model name."""
    words = [
        "RawScaledScorer",
        "egg_and_ham",
        "fancyCategory",
        "Person",
        "OrderItem",
        "HTMLParser",
        "foo-bar",
    ]
    for word in words:
        assert tableize(word) == pluralize(underscore(word))


@pytest.mark.parametrize("bad_input", [None, 123, 4.5, [], {}, b"Bytes"])
def test_tableize_raises_type_error_for_non_string_input(bad_input):
    """Non-string input is rejected with a TypeError rather than silently coerced."""
    with pytest.raises(TypeError):
        tableize(bad_input)
