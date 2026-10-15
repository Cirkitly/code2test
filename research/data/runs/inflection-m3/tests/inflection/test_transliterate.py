import pytest
from inflection import transliterate

def test_transliterate_replaces_diacritics_with_ascii_approximation():
    """Each accented Latin character is approximated by its base letter."""
    assert transliterate('älämölö') == 'alamolo'


def test_transliterate_drops_characters_without_ascii_approximation():
    """Characters lacking an ASCII approximation are dropped, matching the docstring example."""
    assert transliterate('Ærøskøbing') == 'rskbing'


def test_transliterate_pure_ascii_string_is_unchanged():
    """Strings already in ASCII are returned without modification."""
    assert transliterate('hello world') == 'hello world'


def test_transliterate_empty_string_returns_empty_string():
    """Empty input yields empty output."""
    assert transliterate('') == ''


def test_transliterate_e_with_acute_becomes_e():
    """The character 'é' is approximated as 'e' (combining acute accent dropped)."""
    assert transliterate('café') == 'cafe'


def test_transliterate_a_with_diaeresis_becomes_a():
    """The character 'ä' is approximated as 'a' (combining diaeresis dropped)."""
    assert transliterate('später') == 'spater'


def test_transliterate_u_with_diaeresis_becomes_u():
    """The character 'ü' is approximated as 'u' (combining diaeresis dropped)."""
    assert transliterate('über') == 'uber'


def test_transliterate_n_with_tilde_becomes_n():
    """The character 'ñ' is approximated as 'n' (combining tilde dropped)."""
    assert transliterate('mañana') == 'manana'


def test_transliterate_chinese_characters_completely_dropped():
    """CJK characters with no ASCII approximation are dropped entirely."""
    assert transliterate('你好') == ''


def test_transliterate_ascii_preserved_between_dropped_cjk():
    """ASCII characters survive even when surrounded by dropped non-ASCII characters."""
    assert transliterate('abc中文def') == 'abcdef'


def test_transliterate_returns_a_str():
    """The returned value is always of Python's str type."""
    assert isinstance(transliterate('café'), str)
    assert isinstance(transliterate('你好'), str)
    assert isinstance(transliterate('hello'), str)


@pytest.mark.parametrize(
    'non_string_input',
    [123, 12.5, None, ['hello'], b'hello'],
    ids=['int', 'float', 'None', 'list', 'bytes'],
)
def test_transliterate_non_string_input_raises_type_error(non_string_input):
    """Non-string inputs cause unicodedata.normalize to raise TypeError, which propagates out."""
    with pytest.raises(TypeError):
        transliterate(non_string_input)

