import pytest
from inflection import transliterate

def test_transliterate_docstring_example_alamolo():
    """Verify the first docstring example: 'älämölö' becomes 'alamolo'.

    NFKD decomposes each accented character (e.g. 'ä' -> 'a' + combining
    diaeresis) and the subsequent ASCII encoding with 'ignore' drops the
    combining marks, leaving the base ASCII letters.
    """
    assert transliterate('älämölö') == 'alamolo'

def test_transliterate_returns_str_instance():
    """transliterate must always return a string instance, regardless of input."""
    result = transliterate('hello')
    assert isinstance(result, str)

def test_transliterate_empty_string_returns_empty():
    """An empty string input must yield an empty string output."""
    assert transliterate('') == ''

def test_transliterate_pure_ascii_passthrough():
    """A string consisting only of ASCII characters must be returned unchanged."""
    assert transliterate('hello world') == 'hello world'

def test_transliterate_cafe_strips_acute():
    """'café' (with combining acute accent) must become 'cafe'."""
    assert transliterate('café') == 'cafe'

def test_transliterate_naive_strips_diaeresis():
    """'naïve' (with diaeresis on the 'i') must become 'naive'."""
    assert transliterate('naïve') == 'naive'

def test_transliterate_resume_strips_both_accents():
    """'résumé' (with two acute accents) must become 'resume'."""
    assert transliterate('résumé') == 'resume'

def test_transliterate_uber_strips_diaeresis():
    """'über' (with diaeresis on the 'u') must become 'uber'."""
    assert transliterate('über') == 'uber'

def test_transliterate_uppercase_diacritics_stripped():
    """Uppercase accented letters must also be transliterated to base letters."""
    # 'É' -> 'E', 'Ö' -> 'O', 'Ü' -> 'U' via NFKD + ASCII ignore
    assert transliterate('É') == 'E'
    assert transliterate('Ö') == 'O'
    assert transliterate('Ü') == 'U'

def test_transliterate_cjk_ideographs_dropped():
    """CJK ideographs (no ASCII approximation) must be dropped entirely."""
    # Chinese characters have no ASCII decomposition, so they are removed.
    assert transliterate('你好') == ''

def test_transliterate_emoji_dropped_from_mixed_string():
    """Emoji (no ASCII approximation) must be dropped, leaving ASCII intact."""
    # The grinning face emoji has no ASCII decomposition, so it is removed.
    assert transliterate('hello 😀 world') == 'hello  world'

def test_transliterate_only_emoji_returns_empty():
    """A string consisting only of emoji (no ASCII approximation) returns ''."""
    assert transliterate('🎉🎊') == ''

def test_transliterate_preserves_ascii_around_non_ascii():
    """ASCII characters surrounding non-ASCII content must be preserved verbatim."""
    # 'hello ' and ' world' are pure ASCII and pass through; '你好' is dropped.
    assert transliterate('hello 你好 world') == 'hello  world'

def test_transliterate_preserves_ascii_punctuation():
    """ASCII punctuation must be preserved while diacritics are stripped."""
    assert transliterate('héllo, wörld!') == 'hello, world!'

def test_transliterate_preserves_ascii_digits():
    """ASCII digits must be preserved unchanged."""
    assert transliterate('123') == '123'

def test_transliterate_preserves_alphanumeric_structure():
    """Alphanumeric and dash structure is preserved through transliteration."""
    assert transliterate('test-123-abc') == 'test-123-abc'

def test_transliterate_preserves_ascii_whitespace():
    """ASCII whitespace such as newlines must be preserved."""
    assert transliterate('héllo\nwörld') == 'hello\nworld'

def test_transliterate_consecutive_diacritics_become_base_letters():
    """Every accented variant of 'a' must collapse to a plain 'a'."""
    # à á â ã ä å each decompose via NFKD to 'a' + a combining mark,
    # and the combining mark is dropped by the ASCII 'ignore' encoder.
    assert transliterate('aàáâãäå') == 'aaaaaaa'

def test_transliterate_standalone_combining_mark_is_dropped():
    """A combining mark with no base letter must be dropped during ASCII encoding."""
    # U+0308 is COMBINING DIAERESIS, which has no ASCII representation.
    assert transliterate('\u0308') == ''

def test_transliterate_combining_mark_with_base_letter():
    """A combining mark attached to a base letter must be dropped, keeping the base."""
    # 'a' + U+0308: NFKD keeps it as-is (already decomposed); ASCII encoding
    # drops the combining mark, leaving 'a'.
    assert transliterate('a\u0308') == 'a'

def test_transliterate_nordic_chars_produce_ascii_output():
    """The 'Ærøskøbing' example from the docstring must produce ASCII-only output.

    The exact literal output depends on whether 'Æ' is decomposed by NFKD
    (it has a compatibility decomposition to 'AE' per Unicode, but this is
    a property-based assertion to avoid depending on the specific Python
    combination decomposition implementation). What matters is that the result
    contains only ASCII characters and no longer contains the original
    non-ASCII characters.
    """
    result = transliterate('Ærøskøbing')
    assert isinstance(result, str)
    assert result.isascii()
    assert 'Æ' not in result
    assert 'ø' not in result
    # The 7 ASCII characters r, s, k, b, i, n, g must survive.
    assert len(result) >= 7
