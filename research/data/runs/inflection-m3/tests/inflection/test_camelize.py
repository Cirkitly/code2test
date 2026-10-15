import pytest
from inflection import camelize, underscore

def test_snake_case_single_underscore_to_upper_camel():
    """device_type becomes DeviceType (per docstring example)."""
    assert camelize("device_type") == "DeviceType"

def test_snake_case_multiple_underscores_joined():
    """Multiple underscore-separated segments are joined into one CamelCase string."""
    assert camelize("device_type_string") == "DeviceTypeString"

def test_single_word_capitalizes_first_letter():
    """A single word gets its first letter uppercased; the rest is unchanged."""
    assert camelize("device") == "Device"

def test_single_character_is_uppercased():
    """A single lowercase character is uppercased."""
    assert camelize("a") == "A"

def test_already_upper_camel_unchanged():
    """An already UpperCamelCase string is unchanged (no underscores so nothing to merge)."""
    assert camelize("DeviceType") == "DeviceType"

def test_lower_camel_first_letter_uppercased():
    """In lowerCamelCase input, only the first character is uppercased; the rest is preserved."""
    assert camelize("deviceType") == "DeviceType"

def test_each_segment_uppercased():
    """Each underscore-separated single letter is uppercased."""
    assert camelize("a_b_c") == "ABC"

def test_first_segment_already_uppercase_unchanged():
    """When the first segment already starts uppercase, the rest of the segments are still capitalized."""
    assert camelize("Device_type") == "DeviceType"

def test_snake_case_to_lower_camel():
    """device_type becomes deviceType (per docstring example)."""
    assert camelize("device_type", False) == "deviceType"

def test_first_letter_lowered():
    """An initial uppercase letter is lowercased; the rest of UpperCamelCase is preserved."""
    assert camelize("DeviceType", False) == "deviceType"

def test_already_lower_camel_unchanged():
    """Already lowerCamelCase strings remain unchanged."""
    assert camelize("deviceType", False) == "deviceType"

def test_lowercase_word_unchanged():
    """An all-lowercase single word is unchanged."""
    assert camelize("device", False) == "device"

def test_capitalized_segment_lowered():
    """A leading CamelCase segment has its first letter lowered; subsequent segments are joined."""
    assert camelize("Test_test", False) == "testTest"

def test_lowercase_single_character_unchanged():
    """A lowercase single character is unchanged."""
    assert camelize("a", False) == "a"

def test_uppercase_single_character_lowered():
    """A uppercase single character is lowercased."""
    assert camelize("A", False) == "a"

def test_default_matches_explicit_true():
    """Calling without the flag is equivalent to passing True."""
    assert camelize("device_type") == camelize("device_type", True)

def test_default_differs_from_lowercase_variant():
    """The default (uppercase first) and lowercase variants produce different output for an uppercase-first input."""
    assert camelize("DeviceType") != camelize("DeviceType", False)

def test_empty_string_with_default_returns_empty():
    """An empty string with the default behavior returns an empty string."""
    assert camelize("") == ""

def test_empty_string_with_lowercase_raises_index_error():
    """An empty string with uppercase_first_letter=False raises IndexError.

    The lowercase-first branch indexes string[0], which doesn't exist for the empty string.
    """
    with pytest.raises(IndexError):
        camelize("", False)

def test_underscore_camelize_roundtrip_ioerror():
    """camelize(underscore('IOError')) returns 'IoError' as the docstring claims."""
    assert camelize(underscore("IOError")) == "IoError"

def test_returns_str_type():
    """camelize always returns a str instance for valid string inputs."""
    assert isinstance(camelize("device_type"), str)
    assert isinstance(camelize("device_type", False), str)
    assert isinstance(camelize(""), str)
