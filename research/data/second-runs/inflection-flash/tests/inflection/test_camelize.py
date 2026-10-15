import pytest
from inflection import camelize, underscore

def test_camelize_converts_snake_case_to_upper_camel_case_by_default():
    """Default argument uppercase_first_letter=True gives UpperCamelCase."""
    assert camelize("device_type") == "DeviceType"

def test_camelize_with_uppercase_first_letter_false_produces_lower_camel_case():
    """camelize('device_type', False) -> 'deviceType'."""
    assert camelize("device_type", False) == "deviceType"

def test_camelize_with_keyword_argument_uppercase_first_letter_false():
    """The flag can be passed by keyword with the same lowerCamelCase result."""
    assert camelize("device_type", uppercase_first_letter=False) == "deviceType"

def test_camelize_single_word_uppercases_first_letter():
    """Without underscores camelize only uppercases the leading character."""
    assert camelize("word") == "Word"

def test_camelize_leaves_inner_word_characters_untouched():
    """Only the first character and post-underscore characters are capitalized."""
    assert camelize("active_record_errors") == "ActiveRecordErrors"
    assert camelize("lowercase") == "Lowercase"

def test_camelize_handles_multiple_consecutive_underscores():
    """'a__b' -> 'A_b'.

    ``^`` pairs with the first ``a`` (consumed, uppercased).  Then the first
    underscore pairs with the *second* underscore and is replaced by
    ``'_'.upper()`` which is still ``'_'``; the trailing ``b`` has no preceding
    underscore so it is left lowercase.
    """
    assert camelize("a__b") == "A_b"

def test_camelize_consumes_leading_underscore():
    """'_device' -> '_device'.

    At position 0 the ``^`` alternative matches first and consumes the leading
    underscore, uppercasing it to itself; the scan then resumes at index 1 where
    ``^`` no longer applies, so nothing else is capitalized.
    """
    assert camelize("_device") == "_device"

def test_camelize_ignores_non_underscore_separators():
    """Dashes and spaces are not separators, so they are preserved verbatim."""
    assert camelize("device-type") == "Device-type"
    assert camelize("device type") == "Device type"

def test_camelize_single_character_input_is_uppercased_by_default():
    """camelize('a') -> 'A'."""
    assert camelize("a") == "A"

def test_camelize_empty_string_returns_empty_string_when_uppercasing():
    """re.sub on an empty string matches nothing and returns an empty string."""
    assert camelize("") == ""

def test_camelize_empty_string_raises_index_error_when_lowercasing():
    """camelize('', False) -> IndexError because string[0] is evaluated eagerly."""
    with pytest.raises(IndexError):
        camelize("", False)

def test_camelize_is_imperfect_inverse_of_underscore_for_acronym_word():
    """camelize(underscore('IOError')) -> 'IoError' (documented imperfect inverse)."""
    assert underscore("IOError") == "io_error"
    assert camelize(underscore("IOError")) == "IoError"

def test_camelize_round_trips_with_underscore_for_normal_words():
    """For plain words, underscore(camelize(x)) == x and camelize(underscore(x)) == x."""
    assert underscore(camelize("device_type")) == "device_type"
    assert camelize(underscore("device_type")) == "DeviceType"

def test_camelize_preserves_already_camel_case_input():
    """camelize('DeviceType') == 'DeviceType'."""
    assert camelize("DeviceType") == "DeviceType"

def test_camelize_lowercasing_preserves_rest_of_camel_case_string():
    """camelize('DeviceType', False) -> 'deviceType'."""
    assert camelize("DeviceType", False) == "deviceType"

def test_camelize_lowercasing_single_word_stays_lowercase():
    """camelize('device', False) == 'device'."""
    assert camelize("device", False) == "device"

def test_camelize_lowercasing_already_capitalized_word_lowercases_it():
    """camelize('Device', False) -> 'device'."""
    assert camelize("Device", False) == "device"

@pytest.mark.parametrize("value", ["device_type", "a_b_c", "IOError", "_leading", "word"])
def test_camelize_lowercase_flag_equals_manual_first_character_lowercase(value):
    """camelize(s, False) == s[0].lower() + camelize(s)[1:] for every non-empty input."""
    assert camelize(value, False) == value[0].lower() + camelize(value)[1:]

@pytest.mark.parametrize("value", ["device_type", "a_b_c", "my_long_device_name"])
def test_camelize_uppercase_flag_removes_all_underscores(value):
    """Every underscore that is followed by a character is removed."""
    assert "_" not in camelize(value)

@pytest.mark.parametrize(
    "value,flag",
    [("device_type", True), ("device_type", False), ("", True), ("IOError", True)],
)
def test_camelize_returns_string_type(value, flag):
    """The annotated str return type holds for string inputs and both flag values."""
    result = camelize(value, flag)
    assert isinstance(result, str)

@pytest.mark.parametrize("bad_input", [123, None, ["a"], object()])
def test_camelize_raises_type_error_for_non_string_input(bad_input):
    """Non-string inputs are rejected instead of being silently accepted."""
    with pytest.raises((TypeError, IndexError)):
        camelize(bad_input)
