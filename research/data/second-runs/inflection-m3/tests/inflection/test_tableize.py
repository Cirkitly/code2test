import pytest
from inflection import tableize, underscore, pluralize

def test_tableize_camel_case_produces_plural_snake_case():
    """A CamelCase class name is converted to a plural snake_case table name (docstring example)."""
    assert tableize('RawScaledScorer') == 'raw_scaled_scorers'


def test_tableize_snake_case_pluralizes_last_word():
    """An already snake_case input has its final word pluralized (docstring example)."""
    assert tableize('egg_and_ham') == 'egg_and_hams'


def test_tableize_lower_camel_case_produces_plural_snake_case():
    """A lowerCamelCase input is underscored and pluralized (docstring example)."""
    assert tableize('fancyCategory') == 'fancy_categories'


def test_tableize_single_lowercase_word_is_pluralized():
    """A single lowercase word gets pluralized."""
    assert tableize('user') == 'users'


def test_tableize_single_capitalized_word_is_pluralized():
    """A single capitalized word is lowercased by underscore and then pluralized."""
    assert tableize('User') == 'users'


def test_tableize_multi_word_pascal_case():
    """Multi-word PascalCase is split into snake_case words then pluralized."""
    assert tableize('UserAccount') == 'user_accounts'


def test_tableize_returns_string_type():
    """The return value of tableize is always a str instance, regardless of input casing."""
    result = tableize('AnythingYouGiveIt')
    assert isinstance(result, str)


def test_tableize_result_is_all_lowercase():
    """Rails table names are conventionally lowercase; tableize preserves that invariant."""
    result = tableize('SomeFancyClassName')
    assert result == result.lower()


def test_tableize_multi_word_result_uses_underscore_separators():
    """Multi-word class names produce underscores between words, never spaces or capitals."""
    result = tableize('UserAccount')
    assert '_' in result
    assert ' ' not in result
    assert result == result.lower()


def test_tableize_equivalent_to_underscore_then_pluralize():
    """tableize is defined as pluralize(underscore(word)); verify this contract."""
    assert tableize('SomeClassName') == pluralize(underscore('SomeClassName'))
    assert tableize('AnotherExample') == pluralize(underscore('AnotherExample'))


def test_tableize_with_none_raises_type_error():
    """Passing None is invalid because the function expects a string and raises TypeError."""
    with pytest.raises(TypeError):
        tableize(None)


def test_tableize_with_integer_raises_type_error():
    """Passing a non-string value such as an integer raises TypeError."""
    with pytest.raises(TypeError):
        tableize(42)
