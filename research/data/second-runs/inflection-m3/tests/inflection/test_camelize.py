import pytest
from inflection import camelize
from inflection import underscore

def test_camelize_snake_to_uppercamel_primary():
    """Snake case converts to UpperCamelCase by default."""
    assert camelize("device_type") == "DeviceType"


def test_camelize_snake_to_lowercamel_with_false():
    """Snake case converts to lowerCamelCase when uppercase_first_letter=False."""
    assert camelize("device_type", False) == "deviceType"


def test_camelize_already_uppercamel_unchanged():
    """UpperCamelCase input is returned unchanged."""
    assert camelize("DeviceType") == "DeviceType"


def test_camelize_uppercamel_to_lowercamel():
    """UpperCamelCase becomes lowerCamelCase with uppercase_first_letter=False."""
    assert camelize("DeviceType", False) == "deviceType"


def test_camelize_single_lowercase_word():
    """Single lowercase word has its first letter capitalized."""
    assert camelize("word") == "Word"


def test_camelize_single_letter():
    """A single lowercase letter is uppercased."""
    assert camelize("a") == "A"


def test_camelize_multiple_words():
    """Multiple underscore-separated words all get their first letters uppercased."""
    assert camelize("test_string_here") == "TestStringHere"


def test_camelize_four_words():
    """Four snake_case segments become four PascalCase segments."""
    assert camelize("a_b_c_d") == "ABCD"


def test_camelize_empty_string_returns_empty():
    """Empty string is returned as-is when uppercase_first_letter is True."""
    assert camelize("") == ""


def test_camelize_leading_underscore_kept():
    """A leading underscore is preserved because '_'.upper() == '_' and no other matches occur."""
    assert camelize("_test") == "_test"


def test_camelize_trailing_underscore_kept():
    """A trailing underscore is preserved since (.) cannot match past the string end."""
    assert camelize("test_") == "Test_"


def test_camelize_preserves_existing_uppercase_letters():
    """Letters that are not at word boundaries are left untouched (uppercased or not)."""
    assert camelize("ABC_def") == "ABCDef"


def test_camelize_mixed_case_segments():
    """Mixed-case segments retain their internal casing; only word-boundary chars are uppercased."""
    assert camelize("device_Type") == "DeviceType"


def test_camelize_consecutive_underscores_preserved():
    """Consecutive underscores survive because the second '_' is captured and '_'.upper() == '_'."""
    assert camelize("test__string") == "Test_string"


def test_camelize_inverse_of_underscore_io_error():
    """The docstring promises camelize(underscore('IOError')) == 'IoError'."""
    assert camelize(underscore("IOError")) == "IoError"


def test_camelize_idempotent_on_snake_input():
    """camelize applied twice to snake_case yields the same result as once."""
    assert camelize(camelize("device_type")) == "DeviceType"


def test_camelize_idempotent_on_lowercamel_input():
    """lowerCamelCase input is preserved when uppercase_first_letter is False."""
    assert camelize("deviceType", False) == "deviceType"


def test_camelize_lowercase_first_raises_on_empty_string():
    """camelize('', False) raises IndexError because it tries to access string[0]."""
    with pytest.raises(IndexError):
        camelize("", False)


def test_camelize_preserves_non_ascii_letters():
    """Non-ASCII letters in the middle of words are preserved (no transliteration occurs)."""
    assert camelize("hello_wörld") == "HelloWörld"


def test_camelize_returns_str_type():
    """camelize always returns a str instance."""
    assert isinstance(camelize("foo_bar"), str)
    assert isinstance(camelize("FooBar", False), str)

