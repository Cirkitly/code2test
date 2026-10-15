import pytest
from inflection import underscore

def test_underscore_converts_camel_case_to_snake_case():
    """The documented primary example: DeviceType becomes device_type."""
    assert underscore("DeviceType") == "device_type"

def test_underscore_leaves_already_underscored_lowercase_word_unchanged():
    """An already underscored, lowercase word passes through unchanged."""
    assert underscore("foo_bar") == "foo_bar"

def test_underscore_returns_empty_string_for_empty_input():
    """An empty string is a valid expression and yields an empty string."""
    assert underscore("") == ""

def test_underscore_lowercases_a_single_uppercase_word():
    """A single capitalized word only gets lowercased, not split."""
    assert underscore("Device") == "device"

def test_underscore_lowercases_an_all_caps_word_without_inserting_underscore():
    """'FOO' has no lowercase/digit-to-uppercase boundary, so it just lowercases."""
    assert underscore("FOO") == "foo"

def test_underscore_splits_consecutive_capitals_followed_by_a_capitalized_word():
    """The first regex separates an acronym run from a following capitalized word."""
    assert underscore("IOError") == "io_error"

def test_underscore_splits_http_prefix_in_compound_acronym_word():
    """'SomeHTTPServer' => 'SomeHTTP_Server' => 'Some_HTTP_Server' => 'some_http_server'."""
    assert underscore("SomeHTTPServer") == "some_http_server"

def test_underscore_converts_dashes_to_underscores():
    """'Foo-Bar' => 'Foo_Bar' (from the dash replacement) => 'foo_bar'."""
    assert underscore("Foo-Bar") == "foo_bar"

def test_underscore_replaces_every_dash_occurrence():
    """str.replace applies to all occurrences of '-', so 'a-b-c' becomes 'a_b_c'."""
    assert underscore("a-b-c") == "a_b_c"

def test_underscore_is_idempotent():
    """Underscore twice equals underscore once."""
    once = underscore("SomeHTTPServer")
    assert underscore(once) == once

@pytest.mark.parametrize(
    "value",
    ["DeviceType", "IOError", "SomeHTTPServer", "FOO_BAR", "MiXeD-CaSe", "ActiveRecord::Base"],
)
def test_underscore_output_is_always_lowercase(value):
    """Whatever the input casing, the result contains no uppercase characters."""
    result = underscore(value)
    assert result == result.lower()
    assert result.islower() or result == ""

def test_underscore_returns_a_string():
    """The function is a str -> str transformation."""
    result = underscore("DeviceType")
    assert isinstance(result, str)

def test_underscore_handles_namespaced_expressions_by_keeping_separators():
    """'ActiveRecord::Base' => 'Active_Record::Base' => 'active_record::base'."""
    assert underscore("ActiveRecord::Base") == "active_record::base"

def test_underscore_splits_between_digits_and_uppercase_letters():
    """'123ABC' => '123_ABC' => '123_abc' because \\d is in the boundary class."""
    assert underscore("123ABC") == "123_abc"

def test_underscore_splits_multiple_word_boundaries():
    """A long CamelCase string yields one underscored word per capitalised segment."""
    assert underscore("OneTwoThreeFour") == "one_two_three_four"

def test_underscore_lowercases_input_with_spaces_and_punctuation():
    """Unrecognised characters are left in place; only case is normalised."""
    assert underscore("Hello World!") == "hello world!"

def test_underscore_lowercases_non_ascii_input_without_raising():
    """Non-ASCII letters are untouched by the ASCII regexes but still lowercased."""
    result = underscore("ÜberTröpf")
    assert isinstance(result, str)
    assert result == "über_tröpf"

def test_underscore_raises_type_error_for_none_input():
    """Passing None surfaces the TypeError raised by re.sub."""
    with pytest.raises(TypeError):
        underscore(None)

def test_underscore_raises_type_error_for_integer_input():
    """An int argument is invalid because the parameter is typed as str."""
    with pytest.raises(TypeError):
        underscore(123)
