import pytest
from inflection import singularize

@pytest.mark.parametrize("plural,expected_singular", [
    ("posts", "post"),
    ("octopi", "octopus"),
    ("sheep", "sheep"),
    ("word", "word"),
    ("CamelOctopi", "CamelOctopus"),
])
def test_singularize_documented_examples(plural, expected_singular):
    """All examples shown in singularize's docstring should produce stated output."""
    assert singularize(plural) == expected_singular


def test_singularize_returns_str_type():
    """singularize must always return a str value."""
    assert isinstance(singularize("posts"), str)
    assert isinstance(singularize("sheep"), str)
    assert isinstance(singularize(""), str)
    assert isinstance(singularize("word"), str)


def test_singularize_empty_string_returns_empty_string():
    """Empty input must yield empty output - no rule applies to ''."""
    # No uncountable matches \b(...)\Z against empty string, and no singular
    # rule applies, so word is returned unchanged.
    assert singularize("") == ""


def test_singularize_leaves_already_singular_word_unchanged():
    """singularize should be idempotent: applying it to a singular word leaves it alone when no rule matches."""
    # 'post' has no SINGULARS rule that matches (rules expect plural endings like 's'),
    # and isn't in UNCOUNTABLES, so it is returned unchanged.
    assert singularize("post") == "post"
    assert singularize("dog") == "dog"
    assert singularize("apple") == "apple"


def test_singularize_does_not_modify_uncountable_ending_match():
    """Words ending with an uncountable noun (word-boundary match) are returned untouched."""
    # 'sheep' is in UNCOUNTABLES; the regex r'\b(sheep)\Z' matches 'sheep'.
    assert singularize("sheep") == "sheep"
    # 'infosheep' would not match because '\b' requires a word boundary before 'sheep',
    # but 'sheep' on its own does match.
    assert singularize("fish") == "fish"


def test_singularize_is_reverse_of_pluralize_for_regular_words():
    """The docstring states singularize is the reverse of pluralize; verify round-trip for common nouns."""
    from inflection import pluralize
    assert singularize(pluralize("post")) == "post"
    assert singularize(pluralize("dog")) == "dog"
    assert singularize(pluralize("box")) == "box"


def test_singularize_strips_trailing_s_from_regular_plural():
    """General SINGULARS rule handles everyday plurals ending in 's'."""
    # 'posts' matches a SINGULARS rule and 's' is removed.
    assert singularize("posts") == "post"
    # 'cats' -> 'cat'
    assert singularize("cats") == "cat"


def test_singularize_preserves_capitalization_for_irregular():
    """CamelCase forms of irregular plurals are correctly singularized while preserving casing."""
    assert singularize("CamelOctopi") == "CamelOctopus"
