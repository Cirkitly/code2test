import re
import pytest
from inflection import parameterize

@pytest.fixture
def pretty_url_cases():
    """(raw string, separator, expected 'pretty URL' fragment) triples.

    Each expectation is obtained by tracing ``parameterize``: transliterate the
    input, replace every run of characters outside ``[a-z0-9-_]`` with the
    separator, collapse repeated separators, strip a leading/trailing separator
    and lowercase the result.
    """
    return [
        # docstring example, default and custom separators
        ("Donald E. Knuth", "-", "donald-e-knuth"),
        ("Donald E. Knuth", "_", "donald_e_knuth"),
        ("Donald E. Knuth", "", "donaldeknuth"),
        # runs of special characters collapse, boundaries are stripped
        ("Hello, World!", "-", "hello-world"),
        ("$100 (approx)", "-", "100-approx"),
        ("  padded  ", "-", "padded"),
        ("!!!", "-", ""),
        ("", "-", ""),
        # letters, digits, dashes and underscores survive
        ("foo-bar_baz", "-", "foo-bar_baz"),
        ("snake_case name", "-", "snake_case-name"),
        ("-already-dashed-", "-", "already-dashed"),
        ("Chapter 1: Part 2", "-", "chapter-1-part-2"),
        ("foo123 bar456", "-", "foo123-bar456"),
        ("MiXeD123", "-", "mixed123"),
        # punctuation of every kind
        ("C++ & Python: A Comparison", "-", "c-python-a-comparison"),
        ("mixed???  ###chars", "-", "mixed-chars"),
        ("a -- b", "-", "a-b"),
        ("Tab\tseparated", "-", "tab-separated"),
        ("Line\nbreak", "-", "line-break"),
        # custom separators, including regex metacharacters and multi-char ones
        ("Hello World", ".", "hello.world"),
        ("Hello World", "+", "hello+world"),
        ("a b", "--", "a--b"),
        ("_private", "_", "private"),
        ("  spaced out  ", "_", "spaced_out"),
        # transliteration to ASCII
        ("café au lait", "-", "cafe-au-lait"),
        ("M\xfcller", "-", "muller"),
        ("\xdcber cool", "-", "uber-cool"),
        # already parameterized input is stable
        ("hello-world-2024", "-", "hello-world-2024"),
    ]

def test_documented_example_produces_a_pretty_url_slug():
    assert parameterize(u"Donald E. Knuth") == 'donald-e-knuth'

def test_special_characters_are_replaced_by_the_default_dash():
    # ',' and the following space form one run -> one dash
    assert parameterize("Hello, World!") == 'hello-world'
    # '$', ' ' and '(' are separate runs, the trailing ')' is stripped
    assert parameterize("$100 (approx)") == '100-approx'
    # '&' and ':' are punctuation that must not survive
    assert parameterize("C++ & Python: A Comparison") == 'c-python-a-comparison'

def test_custom_separator_is_used_instead_of_a_dash():
    assert parameterize("Donald E. Knuth", "_") == 'donald_e_knuth'
    assert parameterize("a b", separator="~") == 'a~b'

def test_custom_separator_that_is_a_regex_metacharacter():
    assert parameterize("Hello World", ".") == 'hello.world'
    assert parameterize("Hello World", "+") == 'hello+world'

def test_multi_character_separator_is_inserted_verbatim():
    assert parameterize("a b", "--") == 'a--b'

def test_runs_of_special_characters_collapse_into_one_separator():
    assert parameterize("a   b") == 'a-b'
    assert parameterize("a -- b") == 'a-b'
    assert parameterize("mixed???  ###chars") == 'mixed-chars'

def test_leading_and_trailing_separators_are_removed():
    assert parameterize("  padded  ") == 'padded'
    assert parameterize("!!!") == ''
    assert parameterize("-already-dashed-") == 'already-dashed'

def test_input_made_only_of_special_characters_yields_empty_string():
    result = parameterize("!!!???")
    assert result == ''
    assert isinstance(result, str)

def test_empty_string_returns_empty_string():
    assert parameterize("") == ''

def test_hyphens_and_underscores_of_the_input_are_preserved():
    assert parameterize("foo-bar_baz") == 'foo-bar_baz'
    assert parameterize("snake_case name") == 'snake_case-name'

def test_digits_are_preserved_together_with_surrounding_words():
    assert parameterize("Chapter 1: Part 2") == 'chapter-1-part-2'
    assert parameterize("foo123 bar456") == 'foo123-bar456'

def test_result_is_lowercased_and_uppercase_is_not_removed():
    assert parameterize("UPPER Case STRING") == 'upper-case-string'
    assert parameterize("MiXeD123") == 'mixed123'
    assert parameterize("ABC DEF") == 'abc-def'

def test_tabs_and_newlines_are_treated_as_separators():
    assert parameterize("Tab\tseparated") == 'tab-separated'
    assert parameterize("Line\nbreak") == 'line-break'

def test_accented_characters_are_folded_to_ascii():
    assert parameterize("café au lait") == 'cafe-au-lait'
    assert parameterize("Müller") == 'muller'
    assert parameterize("Über cool") == 'uber-cool'

def test_non_ascii_characters_without_approximation_are_dropped():
    result = parameterize("Bjørn")
    assert isinstance(result, str)
    assert 'ø' not in result
    assert result.isascii()

def test_empty_separator_removes_characters_without_inserting_anything():
    assert parameterize("Donald E. Knuth", "") == 'donaldeknuth'
    assert parameterize("Hello, World!", "") == 'helloworld'

def test_leading_and_trailing_separator_removed_for_custom_separator():
    assert parameterize("_private", "_") == 'private'
    assert parameterize("  spaced out  ", "_") == 'spaced_out'

def test_parameterizing_an_already_parameterized_string_is_a_no_op():
    once = parameterize("Hello,   World! -- 2024")
    assert once == 'hello-world-2024'
    assert parameterize(once) == once

def test_returns_a_string_type():
    assert isinstance(parameterize("Hello World"), str)
    assert isinstance(parameterize("Hello World", "_"), str)

def test_expected_pretty_url_fragments_for_a_range_of_inputs(pretty_url_cases):
    for raw, separator, expected in pretty_url_cases:
        assert parameterize(raw, separator) == expected, \
            "parameterize({!r}, {!r}) != {!r}".format(raw, separator, expected)

@pytest.mark.parametrize("raw", [
    "Donald E. Knuth",
    "  Mixed/CASE input?  ",
    "100% pure!",
    "R&D costs: 50%",
    "Ünïcödé têxt",
    "Tab\tand\nnewline",
    "a--b",
    "!!!",
    "",
])
def test_result_only_contains_url_safe_characters(raw):
    result = parameterize(raw)
    assert isinstance(result, str)
    assert re.fullmatch(r"[a-z0-9\-_]*", result) is not None

@pytest.mark.parametrize("raw", [
    "a   b",
    "a -- b",
    "a...b",
    "  a  b  ",
    "a - b - c",
])
def test_never_contains_repeated_dashes_for_the_default_separator(raw):
    result = parameterize(raw)
    assert '--' not in result
    assert not result.startswith('-')
    assert not result.endswith('-')

@pytest.mark.parametrize("invalid", [123, None, b"bytes", ["list"], 4.2])
def test_non_string_input_raises_type_error(invalid):
    with pytest.raises(TypeError):
        parameterize(invalid)

def test_non_string_separator_raises_type_error():
    with pytest.raises(TypeError):
        parameterize("a b", None)
