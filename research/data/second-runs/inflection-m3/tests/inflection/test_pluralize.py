import pytest
from inflection import pluralize

def test_pluralize_empty_string_returns_empty() -> None:
    """An empty string is returned unchanged via the falsy guard at the top of pluralize."""
    assert pluralize("") == ""


def test_pluralize_uncountable_lowercase_unchanged() -> None:
    """Lowercase uncountable nouns return unchanged because word.lower() is in UNCOUNTABLES."""
    assert pluralize("sheep") == "sheep"


def test_pluralize_uncountable_uppercase_unchanged() -> None:
    """Uppercase form of an uncountable word is matched and returned unchanged (case preserved)."""
    assert pluralize("SHEEP") == "SHEEP"


def test_pluralize_uncountable_titlecase_unchanged() -> None:
    """Title-cased uncountable is matched and returned unchanged because the source uses word.lower()."""
    assert pluralize("Sheep") == "Sheep"


def test_pluralize_irregular_octopus_to_octopi() -> None:
    """Irregular plural rules in PLURALS convert 'octopus' to 'octopi' via re.sub."""
    assert pluralize("octopus") == "octopi"


def test_pluralize_already_plural_posts_unchanged() -> None:
    """A word that is already in plural form is returned unchanged by the rules."""
    assert pluralize("posts") == "posts"


def test_pluralize_camelcase_octopus_to_octopi() -> None:
    """The same irregular rule that turns 'octopus' into 'octopi' inflects the CamelCase suffix while leaving 'Camel' intact."""
    assert pluralize("CamelOctopus") == "CamelOctopi"


def test_pluralize_preserves_camel_prefix_for_irregular() -> None:
    """The CamelCase prefix must remain at the start of the inflected result."""
    assert pluralize("CamelOctopus").startswith("Camel")


def test_pluralize_returns_str_for_irregular_rule() -> None:
    """Result is a string instance after re.sub applies an irregular rule."""
    assert isinstance(pluralize("octopus"), str)


def test_pluralize_returns_str_for_empty_input() -> None:
    """Result is a string instance even when the input triggers the falsy short-circuit."""
    assert isinstance(pluralize(""), str)


def test_pluralize_returns_str_for_uncountable() -> None:
    """Result is a string instance when an uncountable word short-circuits the function."""
    assert isinstance(pluralize("sheep"), str)


def test_pluralize_idempotent_on_uncountable() -> None:
    """Pluralize of an uncountable is a fixed point: pluralize(pluralize(x)) == pluralize(x)."""
    once = pluralize("sheep")
    twice = pluralize(once)
    assert once == twice == "sheep"


def test_pluralize_idempotent_on_already_plural() -> None:
    """Pluralize of an already-plural word is a fixed point: pluralize(pluralize(x)) == pluralize(x)."""
    once = pluralize("posts")
    twice = pluralize(once)
    assert once == twice == "posts"

