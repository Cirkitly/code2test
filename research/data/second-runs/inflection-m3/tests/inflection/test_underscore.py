import pytest
from inflection import underscore

@pytest.mark.parametrize("input_str, expected", [
    # Docstring examples
    ("DeviceType", "device_type"),
    ("IOError", "io_error"),
    # Standard camelCase / PascalCase
    ("camelCase", "camel_case"),
    ("PascalCase", "pascal_case"),
    # Acronym-prefixed identifiers
    ("HTMLParser", "html_parser"),
    # Already in target form
    ("already_snake_case", "already_snake_case"),
    # Empty string and single characters
    ("", ""),
    ("A", "a"),
    ("a", "a"),
    # All caps (no lowercase letter to anchor against)
    ("ALLCAPS", "allcaps"),
    # Hyphen handling
    ("some-xml-data", "some_xml_data"),
    ("foo_bar-baz", "foo_bar_baz"),
    # Digit handling
    ("Test123", "test123"),
    ("Test123Abc", "test123_abc"),
    ("V1Test", "v1_test"),
    ("version1Alpha", "version1_alpha"),
    # Consecutive-uppercase boundary cases (regex step 1)
    ("AAAb", "aa_ab"),
    ("ABc", "a_bc"),
])
def test_underscore_transforms_input_to_snake_case(input_str, expected):
    """underscore converts CamelCase/PascalCase to snake_case, replaces hyphens with underscores, and lowercases the result."""
    assert underscore(input_str) == expected

def test_underscore_returns_a_str_instance():
    """The function should always return a str, regardless of the input's content."""
    assert isinstance(underscore("AnyInput"), str)

def test_underscore_output_is_entirely_lowercase():
    """For any string input, the output of underscore must be entirely lowercase."""
    for test_input in [
        "DeviceType",
        "IOError",
        "HTMLParser",
        "ALLCAPS",
        "SomeMixedCASEString",
        "FOO_BAR-BAZ",
        "version1Alpha",
    ]:
        result = underscore(test_input)
        assert result == result.lower(), (
            f"Expected lowercase output for {test_input!r}, got {result!r}"
        )

def test_underscore_none_input_raises_type_error():
    """Passing None to underscore should raise TypeError because re.sub expects a string."""
    with pytest.raises(TypeError):
        underscore(None)

def test_underscore_int_input_raises_type_error():
    """Passing an int to underscore should raise TypeError because re.sub expects a string."""
    with pytest.raises(TypeError):
        underscore(123)
