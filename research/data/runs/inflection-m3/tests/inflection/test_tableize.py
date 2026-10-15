import pytest
from inflection import tableize

def test_tableize_camel_case_to_plural_snake_case():
    """Validate the primary docstring example: CamelCase -> plural snake_case."""
    assert tableize('RawScaledScorer') == 'raw_scaled_scorers'


def test_tableize_already_snake_case_pluralizes_last_segment():
    """Validate the second docstring example: an underscore-separated string
    has only its last word pluralized, yielding 'egg_and_hams' from 'egg_and_ham'."""
    assert tableize('egg_and_ham') == 'egg_and_hams'


def test_tableize_two_word_camel_case_class_name():
    """Validate the third docstring example: a two-word mixed-case class name
    'fancyCategory' becomes the plural snake_case 'fancy_categories'."""
    assert tableize('fancyCategory') == 'fancy_categories'


def test_tableize_always_returns_string():
    """tableize must always return a str instance, never None or other types."""
    assert isinstance(tableize('RawScaledScorer'), str)


def test_tableize_output_is_all_lowercase():
    """tableize output must contain no uppercase characters: SQL table names
    are conventionally lowercase, so the result of underscore + pluralize
    must produce an all-lowercase string."""
    result = tableize('RawScaledScorer')
    assert result == result.lower()


def test_tableize_empty_string_returns_empty_string():
    """Edge case: an empty input string should produce an empty output string.
    Both underscore('') and pluralize('') must yield ''."""
    assert tableize('') == ''


def test_tableize_starts_with_lowercase_character():
    """Edge case: the first character of the output should be lowercase, which
    is required for a proper snake_case table identifier."""
    result = tableize('RawScaledScorer')
    assert result[0] == result[0].lower()
    assert result[0].islower()


def test_tableize_preserves_internal_underscores():
    """Contract: underscores already present in the input must remain in the output
    at the same internal positions. 'egg_and_ham' -> 'egg_and_hams' keeps '_and_'."""
    result = tableize('egg_and_ham')
    assert '_and_' in result


def test_tableize_only_pluralizes_the_final_word_of_underscored_input():
    """Contract: only the trailing word of an underscore-separated input gets
    pluralized; the leading words stay verbatim. This distinguishes tableize
    from a naive 'pluralize the whole string' implementation."""
    result = tableize('egg_and_ham')
    # Leading part (everything up to last segment) is preserved verbatim.
    assert result.startswith('egg_and_')
    # Final segment becomes its plural form: 'ham' -> 'hams'.
    assert result.endswith('hams')


def test_tableize_inserts_underscores_at_camel_case_boundaries():
    """Contract: PascalCase/CamelCase word boundaries become underscores in the
    output. 'RawScaledScorer' has two word boundaries and must yield exactly
    two underscores in the result."""
    result = tableize('RawScaledScorer')
    assert result.count('_') == 2


def test_tableize_does_not_raise_on_typical_class_names():
    """Sanity check: a variety of typical Ruby/Rails model-style class names
    must be processed without raising any exception."""
    # If the implementation regresses (e.g. breaks on consecutive capitals
    # or on short names), these calls will raise and the test will fail.
    tableize('Person')
    tableize('UserAccount')
    tableize('RawScaledScorer')
    tableize('A')

