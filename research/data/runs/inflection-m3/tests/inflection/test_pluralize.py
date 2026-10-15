import pytest
from inflection import pluralize

import pytest
from inflection import pluralize


def test_pluralize_octopus_to_octopi():
    """Latin-style pluralization: 'octopus' is pluralized to 'octopi'.

    Validates that the function applies irregular plural rules.
    """
    assert pluralize("octopus") == "octopi"


def test_pluralize_already_plural_word_unchanged():
    """A word that is already in plural form ('posts') is returned unchanged.

    Validates the documented docstring example and that the function does not
    over-pluralize.
    """
    assert pluralize("posts") == "posts"


def test_pluralize_uncountable_sheep_unchanged():
    """Uncountable noun 'sheep' is returned unchanged.

    Validates the UNCOUNTABLES short-circuit branch.
    """
    assert pluralize("sheep") == "sheep"


def test_pluralize_camelcase_octopus_to_camel_octopi():
    """Pluralization is applied to the trailing word while preserving a CamelCase prefix.

    Validates the documented docstring example 'CamelOctopus' -> 'CamelOctopi'.
    """
    assert pluralize("CamelOctopus") == "CamelOctopi"


def test_pluralize_empty_string_returns_empty():
    """An empty string short-circuits the function and is returned unchanged.

    The 'not word' branch in the source guarantees this.
    """
    assert pluralize("") == ""


def test_pluralize_uppercase_uncountable_preserves_case():
    """The UNCOUNTABLES lookup is case-insensitive (word.lower()) but the original
    word is returned unchanged, so casing is preserved on the way out.
    """
    assert pluralize("SHEEP") == "SHEEP"


def test_pluralize_mixed_case_uncountable_preserves_case():
    """A mixed-case uncountable like 'Sheep' is returned with its original casing."""
    assert pluralize("Sheep") == "Sheep"


def test_pluralize_always_returns_str_type():
    """For any str input, the function must return a str (per the signature)."""
    for word in ("post", "octopus", "sheep", "CamelOctopus", ""):
        assert isinstance(pluralize(word), str)


def test_pluralize_idempotent_on_uncountable():
    """Pluralizing an uncountable noun yields the same result when applied repeatedly.

    Because the UNCOUNTABLES branch returns the input unchanged, applying the
    function again is a no-op.
    """
    first = pluralize("sheep")
    second = pluralize(first)
    assert first == second
    assert first == "sheep"


def test_pluralize_camelcase_prefix_is_preserved():
    """When pluralizing a CamelCase compound, the leading prefix word is preserved
    and the trailing word receives the plural suffix.
    """
    result = pluralize("CamelOctopus")
    assert result.startswith("Camel")
    assert result.endswith("i")
    assert result == "CamelOctopi"


def test_pluralize_does_not_mutate_uncountable_input_value():
    """Uncountable handling returns the input object/value unchanged (no transformation)."""
    word = "sheep"
    assert pluralize(word) == word


def test_pluralize_empty_string_result_is_empty_string_type():
    """The empty-string branch returns the literal '', not None or anything else."""
    result = pluralize("")
    assert result == ""
    assert isinstance(result, str)
