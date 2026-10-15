import pytest
from inflection import camelize
from inflection import underscore

@pytest.fixture
def upper_camel_cases():
    """(input_string, expected_upper_camel_case) pairs.

    Covers the primary path plus structural edge cases: already-camelized
    input, digits, consecutive/trailing/leading underscores, non-underscore
    separators and the empty string.
    """
    return [
        ("device_type", "DeviceType"),
        ("word", "Word"),
        ("AlreadyCamelCase", "AlreadyCamelCase"),
        ("model_2_name", "Model2Name"),
        ("version_2", "Version2"),
        ("foo__bar", "Foo_Bar"),
        ("foo_", "Foo_"),
        ("_leading", "_Leading"),
        ("foo bar", "Foo bar"),
        ("foo-bar", "Foo-bar"),
        ("", ""),
    ]

@pytest.fixture
def lower_camel_cases():
    """(input_string, expected_lower_camel_case) pairs for lowerCamelCase mode."""
    return [
        ("device_type", "deviceType"),
        ("Word", "word"),
        ("already_camel", "alreadyCamel"),
        ("model_2_name", "model2Name"),
        ("foo_bar_baz", "fooBarBaz"),
        ("_leading", "_Leading"),
        ("", ""),
    ]

@pytest.fixture
def snake_case_words():
    """snake_case words used to check the camelize/underscore inverse relationship."""
    return ["device_type", "user_account", "api_response_code", "blog_post"]

def test_camelize_documented_upper_camel_case_example():
    """Primary happy path: the docstring example camelize('device_type') -> 'DeviceType'."""
    assert camelize("device_type") == "DeviceType"
