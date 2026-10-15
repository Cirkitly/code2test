import pytest
from inflection import dasherize

def test_dasherize_replaces_single_underscore_with_dash():
    """The documented example: a single underscore becomes a single dash."""
    assert dasherize("puni_puni") == "puni-puni"

def test_dasherize_leaves_string_without_underscores_unchanged():
    """A string with no underscores should be returned as-is."""
    assert dasherize("hello") == "hello"

def test_dasherize_returns_empty_string_for_empty_input():
    """dasherize('') should return '' with no errors."""
    assert dasherize("") == ""

def test_dasherize_replaces_multiple_underscores():
    """All underscores in the input should be replaced with dashes."""
    assert dasherize("a_b_c_d") == "a-b-c-d"

def test_dasherize_replaces_string_of_only_underscores():
    """A string made entirely of underscores should become entirely of dashes."""
    assert dasherize("___") == "---"

def test_dasherize_preserves_existing_dashes():
    """Existing dashes in the input must not be affected by the replacement."""
    assert dasherize("a-b") == "a-b"

def test_dasherize_replaces_mixed_underscores_and_preserves_dashes():
    """Underscores become dashes while existing dashes remain untouched."""
    assert dasherize("a_b-c_d") == "a-b-c-d"

def test_dasherize_replaces_leading_and_trailing_underscores():
    """Leading and trailing underscores should be turned into leading/trailing dashes."""
    assert dasherize("_hello_") == "-hello-"

def test_dasherize_replaces_single_underscore_character():
    """dasherize('_') should yield '-'."""
    assert dasherize("_") == "-"

def test_dasherize_returns_string_type():
    """dasherize must always return a str instance."""
    assert isinstance(dasherize("a_b"), str)
    assert isinstance(dasherize(""), str)
    assert isinstance(dasherize("no_under_scores"), str)

def test_dasherize_result_never_contains_underscore():
    """For any input string that contains an underscore, the result must not."""
    inputs = ["a_b", "a_b_c", "_leading", "trailing_", "_both_", "____"]
    for value in inputs:
        assert "_" not in dasherize(value)

def test_dasherize_preserves_character_count_for_underscores_only():
    """Swapping '_' for '-' is a 1-for-1 substitution so length must stay the same."""
    for value in ["a_b", "a_b_c", "_hello_", "___", "no_change"]:
        assert len(dasherize(value)) == len(value)

def test_dasherize_raises_attribute_error_on_none_input():
    """None has no .replace method, so dasherize(None) must raise AttributeError."""
    with pytest.raises(AttributeError):
        dasherize(None)

def test_dasherize_raises_attribute_error_on_integer_input():
    """An int has no .replace method, so AttributeError should be raised."""
    with pytest.raises(AttributeError):
        dasherize(123)

def test_dasherize_raises_attribute_error_on_list_input():
    """A list has no .replace method, so AttributeError should be raised."""
    with pytest.raises(AttributeError):
        dasherize(["a_b"])
