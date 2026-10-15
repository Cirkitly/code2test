import pytest
from inflection import underscore

def test_underscore_pascalcase_to_snake_case():
    """PascalCase input converts to snake_case lowercase output."""
    assert underscore("DeviceType") == "device_type"

def test_underscore_consecutive_uppercase_letters():
    """A short run of consecutive capitals should be split from a trailing Capital+lowercase suffix."""
    assert underscore("IOError") == "io_error"

def test_underscore_long_consecutive_uppercase_run():
    """A long run of consecutive capitals (HTTP) should be split before the next word (Response)."""
    assert underscore("HTTPResponse") == "http_response"

def test_underscore_multiple_camelcase_boundaries():
    """Every camelCase boundary should produce an underscore."""
    assert underscore("fooBarBaz") == "foo_bar_baz"

def test_underscore_already_snake_case_is_unchanged():
    """An input that is already snake_case lowercase should round-trip unchanged."""
    assert underscore("already_lower") == "already_lower"

def test_underscore_dashes_become_underscores():
    """Dashes should be replaced with underscores."""
    assert underscore("already-lower") == "already_lower"

def test_underscore_all_caps_with_underscore_lowercased():
    """ALL_CAPS contains no lowercase so neither regex triggers; only the lowercase step runs."""
    assert underscore("ALL_CAPS") == "all_caps"

def test_underscore_dashed_pascalcase_words():
    """Dashed PascalCase segments are not split across the dash; only the dash becomes an underscore.
    Trace: 'Some-Mixed-String' -> regex1 no match -> regex2 no match (no adj lowercase+upper) -> 'Some_Mixed_String' -> 'some_mixed_string'.
    """
    assert underscore("Some-Mixed-String") == "some_mixed_string"

def test_underscore_empty_string_returns_empty_string():
    """The empty string should be a fixed point of underscore."""
    assert underscore("") == ""

def test_underscore_single_capitalized_word_is_lowercased():
    """A single capitalized word should be lowercased without inserting any underscore."""
    assert underscore("Single") == "single"

def test_underscore_digit_before_capital_splits_at_digit():
    """Digits count as lowercase characters for the split boundary."""
    assert underscore("version1Beta") == "version1_beta"

def test_underscore_pascalcase_prefix_then_consecutive_caps():
    """TestHTTPResponse exercises both regex passes.
    Trace: regex1 splits 'HTTP' and 'Response' producing 'TestHTTP_Response';
    then regex2 splits 't' and 'H' producing 'Test_HTTP_Response';
    then lowercase gives 'test_http_response'.
    """
    assert underscore("TestHTTPResponse") == "test_http_response"

def test_underscore_lowercase_prefix_then_consecutive_caps():
    """userID: the lowercase r before the consecutive caps triggers regex 2, not regex 1."""
    assert underscore("userID") == "user_id"

def test_underscore_is_not_perfect_inverse_of_camelize_docstring_example():
    """The docstring demonstrates that underscore is not a perfect inverse of camelize.

    camelize(underscore('IOError')) yields 'IoError' rather than 'IOError'.
    """
    from inflection import camelize
    assert camelize(underscore("IOError")) == "IoError"

def test_underscore_leading_underscore_is_preserved():
    """Leading underscore is preserved; internal camelCase boundary still gets split.
    Trace: '_privateField' -> regex1 no match -> regex2 matches 'e'+'F' -> '_private_Field' -> '_private_field'.
    """
    assert underscore("_privateField") == "_private_field"

def test_underscore_only_dashes_become_only_underscores():
    """A string consisting only of dashes should consist only of underscores after the function."""
    assert underscore("---") == "___"

def test_underscore_idempotent_on_its_own_output():
    """underscore(underscore(x)) should equal underscore(x) for any string x.

    Demonstrated here with 'DeviceType': after one call the result is already
    lowercase snake_case with no dashes, so a second call must leave it alone.
    """
    once = underscore("DeviceType")
    twice = underscore(once)
    assert once == "device_type"
    assert twice == once

def test_underscore_non_string_input_raises_type_error():
    """Passing an integer must raise TypeError because re.sub requires a string-like input."""
    with pytest.raises(TypeError):
        underscore(123)

def test_underscore_none_input_raises_type_error():
    """Passing None must raise TypeError because re.sub requires a string-like input."""
    with pytest.raises(TypeError):
        underscore(None)
