import pytest
from inflection import titleize

@pytest.fixture
def assert_titled():
    """Return a helper that checks an exact titleize result plus invariants."""

    def _assert(word, expected):
        result = titleize(word)
        assert isinstance(result, str), "titleize must always return a str"
        assert result == expected
        return result

    return _assert

@pytest.fixture
def phrase_samples():
    """Return (raw, expected) pairs spanning the main separator styles."""
    return [
        ("man from the boondocks", "Man From The Boondocks"),
        ("x-men: the last stand", "X Men: The Last Stand"),
        ("TheManWithoutAPast", "The Man Without A Past"),
        ("raiders_of_the_lost_ark", "Raiders Of The Lost Ark"),
    ]

def test_titleize_capitalizes_every_word_of_a_plain_phrase():
    """A space separated phrase has every word capitalized."""
    assert titleize("man from the boondocks") == "Man From The Boondocks"

def test_titleize_converts_hyphens_into_word_separators():
    """Dashes act as word separators (dash -> underscore -> space)."""
    assert titleize("x-men: the last stand") == "X Men: The Last Stand"

def test_titleize_splits_camel_case_into_separate_words():
    """Camel cased input is split on case boundaries before capitalizing."""
    assert titleize("TheManWithoutAPast") == "The Man Without A Past"

def test_titleize_converts_underscores_into_spaces():
    """Underscores act as word separators."""
    assert titleize("raiders_of_the_lost_ark") == "Raiders Of The Lost Ark"

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("man from the boondocks", "Man From The Boondocks"),
        ("x-men: the last stand", "X Men: The Last Stand"),
        ("TheManWithoutAPast", "The Man Without A Past"),
        ("raiders_of_the_lost_ark", "Raiders Of The Lost Ark"),
        ("it happened on the first of june", "It Happened On The First Of June"),
    ],
)
def test_titleize_matches_documented_examples(raw, expected):
    """Every example shown in the titleize docstring is reproduced exactly."""
    assert titleize(raw) == expected

def test_titleize_normalizes_mixed_separators_at_once():
    """Dashes, underscores and spaces are all normalized in a single pass."""
    samples = [
        ("raiders-of-the_lost ark", "Raiders Of The Lost Ark"),
        ("star-wars: episode iv", "Star Wars: Episode Iv"),
    ]
    for raw, expected in samples:
        assert titleize(raw) == expected

def test_titleize_normalizes_all_caps_input():
    """SHOUTED input is lowercased and then title cased."""
    assert titleize("HELLO WORLD") == "Hello World"

def test_titleize_lowercases_an_embedded_acronym():
    """An acronym glued to a lowercase word is split: 'the HTML parser'."""
    assert titleize("the HTML parser") == "The Html Parser"

def test_titleize_splits_acronym_prefixed_camel_case():
    """'XMLHttpRequest' splits into xml/http/request and title cases them."""
    assert titleize("XMLHttpRequest") == "Xml Http Request"

def test_titleize_keeps_digits_and_capitalizes_around_them():
    """Digits are preserved and words around them are still capitalized."""
    assert titleize("chapter 1 of the book") == "Chapter 1 Of The Book"

def test_titleize_handles_hyphenated_numbered_titles():
    """A hyphenated rank stays attached to its digits: 'top-10 list'."""
    assert titleize("top-10 list") == "Top 10 List"

def test_titleize_preserves_punctuation_while_capitalizing():
    """Punctuation is preserved while the following word is capitalized."""
    assert titleize("hello, world!") == "Hello, World!"
    assert titleize("!hello world!") == "!Hello World!"

def test_titleize_keeps_dotted_abbreviations_intact():
    """Dotted abbreviations keep their dots but every letter is capitalized."""
    assert titleize("the m.i.t.") == "The M.I.T."

def test_titleize_keeps_non_ascii_letters_untouched(assert_titled):
    """Accented characters are preserved (no transliteration happens)."""
    assert_titled("café au lait", "Café Au Lait")

def test_titleize_returns_a_plain_string():
    """The return value is a built-in ``str``."""
    result = titleize("a tale of two cities")
    assert type(result) is str

def test_titleize_of_a_single_word():
    """A one word string is simply capitalized."""
    assert titleize("hello") == "Hello"

def test_titleize_of_a_single_letter_word():
    """Even a single letter word is capitalized."""
    assert titleize("i") == "I"

def test_titleize_of_empty_string_returns_empty_string():
    """Empty input produces empty output rather than an error."""
    assert titleize("") == ""

def test_titleize_of_whitespace_only_string_returns_empty_string():
    """Whitespace-only input has no words, so it is returned unchanged.

    ``titleize`` never strips (neither ``underscore`` nor ``humanize``
    strips), and there is no ``\\w`` character for the final regular
    expression to capitalize.
    """
    assert titleize("   ") == "   "

def test_titleize_of_underscore_only_string_returns_empty_string():
    """Underscores become spaces which are then returned unchanged.

    ``humanize`` turns every ``_`` into a space; with no word characters
    left there is nothing to capitalize and nothing is stripped.
    """
    assert titleize("___") == "   "

def test_titleize_strips_outer_whitespace_but_keeps_inner_spacing():
    """Only the words are title-cased; surrounding/inner spacing is kept.

    ``titleize("  hello   world  ")`` capitalizes each word start but keeps
    the original runs of spaces exactly as they were supplied.
    """
    result = titleize("  hello   world  ")
    assert result == "  Hello   World  "

def test_titleize_drops_a_trailing_id_suffix_inherited_from_humanize():
    """A trailing '_id' is removed before the title casing is applied."""
    assert titleize("author_id") == "Author"
    assert titleize("the_matrix_id") == "The Matrix"

def test_titleize_handles_apostrophes_inside_words():
    """Internal apostrophes are kept and the following letter is lower-cased.

    The final ``re.sub(r"\\b('?\\w)", ...)`` captures the apostrophe together
    with the next character and calls ``str.capitalize()`` on that whole
    match, so ``"O'Brien"`` becomes ``"O'brien"``.
    """
    assert titleize("o'brien") == "O'brien"

def test_titleize_handles_possessive_contractions():
    """``str.title()`` upper-cases after an apostrophe; that outcome is kept.

    ``"the dog's life"`` title-cases to ``"The Dog'S Life"`` and the final
    substitution lowers the ``S`` back, yielding ``"The Dog's Life"``.
    """
    assert titleize("the dog's life") == "The Dog's Life"

def test_titleize_handles_leading_apostrophe_before_a_word():
    """A leading apostrophe is preserved and the word is still capitalized."""
    assert titleize("'em") == "'Em"

def test_titleize_handles_quoted_words():
    """Single quotes around a word do not break capitalization."""
    assert titleize("the 'quoted' word") == "The 'Quoted' Word"

def test_titleize_is_stable_on_already_titled_input():
    """Running titleize on its own output changes nothing."""
    titled = titleize("The Man Without A Past")
    assert titled == "The Man Without A Past"
    assert titleize(titled) == titled

def test_titleize_is_idempotent_for_plain_phrases():
    """titleize(titleize(x)) == titleize(x) for a normal phrase."""
    once = titleize("the quick brown fox")
    assert once == "The Quick Brown Fox"
    assert titleize(once) == once

def test_titleize_output_is_already_title_cased(phrase_samples):
    """For separator-only phrases the output already equals ``str.title()``."""
    for raw, _expected in phrase_samples:
        result = titleize(raw)
        assert result == result.title()

def test_titleize_raises_type_error_for_none():
    """``None`` is not a valid argument and raises ``TypeError``."""
    with pytest.raises(TypeError):
        titleize(None)

@pytest.mark.parametrize(
    "value",
    [123, 4.5, True, ["a"], {"a": 1}, object()],
    ids=["int", "float", "bool", "list", "dict", "object"],
)
def test_titleize_raises_type_error_for_non_string_input(value):
    """Any non-str input raises ``TypeError`` instead of failing obscurely."""
    with pytest.raises(TypeError):
        titleize(value)

def test_titleize_raises_type_error_for_bytes_input():
    """Bytes are rejected: the internal re patterns are ``str`` patterns."""
    with pytest.raises(TypeError):
        titleize(b"hello world")
