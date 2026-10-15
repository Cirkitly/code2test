import pytest
from inflection import transliterate

from inflection import transliterate


def test_transliterate_replaces_accented_letters_with_ascii_approximation():
    """Umaluts decompose into a base ASCII vowel plus a combining diaeresis.

    NFKD turns 'ä' into 'a' + U+0308 COMBINING DIAERESIS. The base letter is
    ASCII and survives the ``encode('ascii', 'ignore')`` step, while the
    non-ASCII combining mark is dropped. The documented example therefore
    becomes 'alamolo'.
    """
    assert transliterate('älämölö') == 'alamolo'

from inflection import transliterate


def test_transliterate_ignores_characters_without_decomposition():
    """Characters with no NFKD decomposition are simply ignored.

    Neither U+00C6 LATIN CAPITAL LETTER AE nor U+00F8 LATIN SMALL LETTER O
    WITH STROKE has a canonical (NFKD) decomposition, so both are non-ASCII
    after normalization and get dropped by the 'ignore' error handler.
    """
    assert transliterate('Ærøskøbing') == 'rskbing'

from inflection import transliterate


def test_transliterate_handles_tilde_combining_marks():
    """Combining tilde is stripped, base letter kept.

    U+00F1 LATIN SMALL LETTER N WITH TILDE decomposes to 'n' + U+0303, so
    'mañana' becomes 'manana'.
    """
    assert transliterate('mañana') == 'manana'

from inflection import transliterate


def test_transliterate_handles_cedilla_combining_marks():
    """Combining cedilla is stripped, base letter kept.

    U+00E7 LATIN SMALL LETTER C WITH CEDILLA decomposes to 'c' + U+0327, so
    the accented word loses only the diacritic.
    """
    assert transliterate('Français') == 'Francais'

from inflection import transliterate


def test_transliterate_handles_acute_accent_combining_marks():
    """Combining acute accent is stripped, base letter kept.

    U+00FA LATIN SMALL LETTER U WITH ACUTE decomposes to 'u' + U+0301, so
    'ñandú' becomes 'nandu'.
    """
    assert transliterate('ñandú') == 'nandu'

from inflection import transliterate


def test_transliterate_leaves_pure_ascii_string_unchanged():
    """Pure ASCII input is an identity transform.

    No non-ASCII code points are present, so the ``encode(..., 'ignore')``
    step removes nothing and the original string is returned verbatim.
    """
    assert transliterate('plain_ascii 123!') == 'plain_ascii 123!'

from inflection import transliterate


def test_transliterate_returns_empty_string_for_fully_unsupported_characters():
    """A string of only non-decomposable characters collapses to ''.

    U+00DF LATIN SMALL LETTER SHARP S has no canonical decomposition, so the
    only character in the input is dropped and the result is empty.
    """
    assert transliterate('ß') == ''

from inflection import transliterate


def test_transliterate_drops_scripts_without_ascii_approximation():
    """Non-Latin scripts with no ASCII approximation vanish entirely.

    U+4F60 and U+597D have no NFKD decomposition, so both are removed by the
    'ignore' error handler and the function returns an empty string instead
    of raising or substituting a placeholder.
    """
    assert transliterate('你好') == ''

from inflection import transliterate


def test_transliterate_drops_emojis_and_symbols_without_error():
    """Emoji and symbols without decomposition are dropped, not rejected.

    U+00B0 DEGREE SIGN, U+1F600 GRINNING FACE and U+2764 HEAVY BLACK HEART
    all lack NFKD decompositions, so they are all removed.
    """
    assert transliterate('°😀❤') == ''

def test_transliterate_mixed_script_string_keeps_only_ascii_characters():
    """ASCII characters are preserved around dropped non-ASCII ones.

    Characters that decompose (e.g. ``ü`` -> ``u`` + combining diaeresis) keep
    their ASCII base letter, characters with no ASCII approximation (e.g.
    ``Æ``, ``ß``, CJK ideographs) are simply ignored and leave no placeholder
    marks behind -- only the surrounding whitespace remains, so the single
    space around the dropped CJK characters collapses into two spaces.
    """
    assert transliterate('Æbürger 你好 straße') == 'burger  strae'

from inflection import transliterate


def test_transliterate_is_idempotent_for_ascii_output():
    """Transliterating an already-transliterated value changes nothing.

    The first call returns pure ASCII; a second call therefore normalizes and
    encodes an all-ASCII string, which is an identity operation.
    """
    once = transliterate('älämölö')

    assert transliterate(once) == once == 'alamolo'

from inflection import transliterate


def test_transliterate_always_returns_a_string():
    """The function always returns a plain ``str``.

    This holds both for input that survives untouched and for input that is
    entirely non-ASCII, and the result always encodes to ASCII cleanly.
    """
    assert isinstance(transliterate('hello'), str)
    assert isinstance(transliterate('你好'), str)
    assert isinstance(transliterate(''), str)


def test_transliterate_result_is_encodable_as_ascii():
    """Whatever survives normalization is guaranteed ASCII-encodable."""
    result = transliterate('Ærøskøbing äpfel')

    assert result.encode('ascii') == b'rskbing apfel'

from inflection import transliterate


def test_transliterate_empty_string_returns_empty_string():
    """Empty input normalizes and encodes to empty output."""
    assert transliterate('') == ''

from inflection import transliterate


def test_transliterate_output_length_never_exceeds_input_length():
    """Transliteration only removes code points, so length cannot increase.

    NFKD can expand a single character into several, but every expansion that
    adds a non-ASCII combining mark is then dropped again by the ASCII encode,
    so the output is never longer than the input.
    """
    samples = ['älämölö', 'Ærøskøbing', 'mañana', '你好', 'ß', '']

    for sample in samples:
        assert len(transliterate(sample)) <= len(sample)

import pytest

from inflection import transliterate


def test_transliterate_raises_type_error_for_non_string_argument():
    """A non-string argument violates the 'must be unicode' contract.

    ``unicodedata.normalize`` is reached first and rejects anything that is
    not a ``str``.
    """
    with pytest.raises(TypeError):
        transliterate(123)

import pytest

from inflection import transliterate


def test_transliterate_raises_type_error_for_none_argument():
    """``None`` is rejected with a TypeError instead of returning ''. """
    with pytest.raises(TypeError):
        transliterate(None)

import pytest

from inflection import transliterate


def test_transliterate_raises_type_error_for_bytes_argument():
    """Bytes are not unicode, so they are rejected with a TypeError.

    The failure happens in ``unicodedata.normalize`` before any encoding
    step, matching the documented requirement that the string be unicode.
    """
    with pytest.raises(TypeError):
        transliterate(b'abc')

import pytest

from inflection import transliterate


def test_transliterate_raises_type_error_when_called_without_arguments():
    """The single required ``string`` argument cannot be omitted."""
    with pytest.raises(TypeError):
        transliterate()
