import pytest
from inflection import transliterate

def test_transliterate_replaces_accented_letters_with_ascii_approximation():
    """Accented Latin characters map to their unaccented ASCII counterparts.

    NFKD decomposes 'älämölö' into base letters plus combining diaeresis
    marks; those marks are not ASCII and are therefore dropped by the
    'ignore' error handler, leaving the ASCII approximations.
    """
    assert transliterate('älämölö') == 'alamolo'

def test_transliterate_ignores_characters_without_ascii_approximation():
    """Characters lacking an ASCII approximation are silently ignored.

    'Æ' and 'ø' have no canonical/compatibility decomposition under NFKD,
    so they survive normalization but cannot be ASCII-encoded and are dropped
    by the 'ignore' error handler.
    """
    result = transliterate('Ærøskøbing')

    assert result == 'rskbing'
    assert 'Æ' not in result
    assert 'ø' not in result

def test_transliterate_strips_diacritics_from_mixed_accented_phrase():
    """Combining accent marks are removed; base letters and layout are kept.

    NFKD turns 'è' into 'e' + U+0300 combining grave accent. Only the 'e'
    is ASCII, so the output is the ASCII base letters with the original
    spacing and capitalization intact.
    """
    assert transliterate('Crème Brûlée') == 'Creme Brulee'

def test_transliterate_removes_characters_that_have_no_ascii_form():
    """A character with no ASCII approximation is removed, not substituted.

    'ß' has no decomposition under NFKD and no ASCII equivalent, so the
    'ignore' handler removes it; the ASCII letters around it are preserved.
    """
    assert transliterate('Straße') == 'Strae'

def test_transliterate_returns_empty_string_for_pure_non_ascii_input():
    """Input consisting only of untransliterable characters yields ''.

    All three characters are non-ASCII and have no NFKD decomposition, so
    normalization cannot introduce ASCII characters and the ASCII encoder
    ignores all of them.
    """
    result = transliterate('日本語')

    assert result == ''
    assert len(result) == 0

def test_transliterate_leaves_pure_ascii_string_unchanged():
    """ASCII-only input is returned unchanged.

    NFKD leaves ASCII characters untouched and every ASCII character can be
    encoded with the 'ascii' codec, so the string round-trips identically.
    """
    assert transliterate('Hello, World 123!') == 'Hello, World 123!'

def test_transliterate_returns_empty_string_for_empty_input():
    """The empty string is a valid input and maps to the empty string."""
    assert transliterate('') == ''

def test_transliterate_output_always_contains_only_ascii_characters():
    """The returned string never contains any non-ASCII character.

    Every produced character must satisfy ord(char) < 128, since the result is
    decoded from an 'ascii' encoded byte string.
    """
    samples = [
        'älämölö',
        'Ærøskøbing',
        'Crème Brûlée',
        'Straße',
        'Ελλάδα',
        'Ру́сский',
        'naïve café',
    ]

    for sample in samples:
        result = transliterate(sample)
        assert isinstance(result, str)
        assert all(ord(character) < 128 for character in result), (
            f'transliterate({sample!r}) produced non-ASCII characters: {result!r}'
        )

def test_transliterate_is_idempotent():
    """Applying transliterate twice equals applying it once.

    Because the first call already returns a pure-ASCII string, the second
    call has nothing left to change.
    """
    once = transliterate('Crème Brûlée')

    assert transliterate(once) == once == 'Creme Brulee'

def test_transliterate_removes_diacritics_but_keeps_ascii_punctuation():
    """ASCII punctuation and spacing survive; only diacritics are stripped."""
    result = transliterate('Ünïcôdé--Tèst_Case!')

    assert result == 'Unicode--Test_Case!'

def test_transliterate_raises_type_error_for_non_string_input():
    """Passing a non-string raises TypeError from unicodedata.normalize.

    The function normalizes its argument directly, so types lacking a
    string representation accepted by the unicodedata module fail fast.
    """
    with pytest.raises(TypeError):
        transliterate(12345)

def test_transliterate_raises_type_error_for_none_input():
    """None is not a valid argument and raises TypeError."""
    with pytest.raises(TypeError):
        transliterate(None)

def test_transliterate_raises_type_error_for_bytes_input():
    """Bytes are not accepted; the function requires a unicode string."""
    with pytest.raises(TypeError):
        transliterate(b'abc')

def test_transliterate_produces_url_safe_slug_from_accented_text():
    """The result can be embedded in a URL/identifier without further escaping.

    Every character of the transliterated slug must be ASCII and the original
    letters must be preserved in order (only diacritics removed), which is
    exactly what makes it usable as a URL slug.
    """
    result = transliterate('Über Café')

    assert result == 'Uber Cafe'
    assert result.replace(' ', '').isalnum()

def test_transliterate_preserves_ascii_letters_of_non_latin_script_text():
    """Non-Latin scripts are removed; surrounding ASCII text is preserved.

    Cyrillic characters are non-ASCII with no ASCII representation, so they
    are ignored; the ASCII portions of the string remain in order.
    """
    assert transliterate('Hello мир World') == 'Hello  World'
