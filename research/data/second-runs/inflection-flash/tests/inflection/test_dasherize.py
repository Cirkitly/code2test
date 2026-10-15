import pytest
from inflection import dasherize, parameterize, underscore

def test_dasherize_replaces_single_underscore_with_dash():
    """The canonical example from the docstring: 'puni_puni' -> 'puni-puni'."""
    assert dasherize("puni_puni") == "puni-puni"

def test_dasherize_replaces_multiple_underscores_with_dashes():
    """Each '_' is replaced independently by str.replace, so all underscores become dashes."""
    assert dasherize("a_b_c_d") == "a-b-c-d"

def test_dasherize_leaves_string_without_underscores_unchanged():
    """Without underscores there is nothing to replace, so the original word is returned."""
    assert dasherize("puni") == "puni"

def test_dasherize_replaces_leading_underscore_with_dash():
    """A leading underscore is replaced just like any other, producing a leading dash."""
    assert dasherize("_leading") == "-leading"

def test_dasherize_replaces_trailing_underscore_with_dash():
    """A trailing underscore is replaced just like any other, producing a trailing dash."""
    assert dasherize("trailing_") == "trailing-"

def test_dasherize_replaces_consecutive_underscores_with_consecutive_dashes():
    """str.replace maps each underscore one-to-one; adjacent underscores yield adjacent dashes."""
    assert dasherize("foo__bar") == "foo--bar"

def test_dasherize_of_only_underscores_yields_only_dashes():
    """A string of two underscores becomes a string of two dashes."""
    assert dasherize("__") == "--"

def test_dasherize_returns_empty_string_for_empty_input():
    """Replacing characters in an empty string still yields an empty string."""
    assert dasherize("") == ""

def test_dasherize_preserves_non_underscore_characters_including_existing_dashes():
    """Only '_' is targeted; existing '-' characters and other symbols are left alone."""
    assert dasherize("Active-Record_Model.v2") == "Active-Record-Model.v2"

def test_dasherize_does_not_modify_whitespace_or_case():
    """The function performs no case conversion or whitespace stripping."""
    assert dasherize("Foo Bar_baz") == "Foo Bar-baz"

def test_dasherize_result_is_a_string_and_input_is_not_mutated():
    """A new str is produced and the original argument object is left untouched."""
    original = "some_word"
    result = dasherize(original)
    assert isinstance(result, str)
    assert result is not original
    assert original == "some_word"

def test_dasherize_preserves_string_length():
    """Each '_' maps to exactly one '-', so length never changes."""
    for word in ["a_b", "___", "plain", "", "_"]:
        assert len(dasherize(word)) == len(word)

def test_dasherize_result_contains_no_underscores_and_is_idempotent():
    """The output never contains '_' and applying dasherize again changes nothing."""
    result = dasherize("mixed_Case-With_underscore")
    assert "_" not in result
    assert dasherize(result) == result

def test_dasherize_is_inverse_of_underscore_replacement_for_simple_words():
    """dasherize and underscore convert in opposite directions for simple lowercase words."""
    assert dasherize(underscore("some-word")) == "some-word"
    assert underscore(dasherize("some_word")) == "some_word"

def test_dasherize_raises_attribute_error_for_non_string_input():
    """The function only accepts str; anything without .replace raises AttributeError."""
    with pytest.raises(AttributeError):
        dasherize(123)

def test_dasherize_raises_attribute_error_for_none_input():
    """None has no .replace method, so an AttributeError is raised."""
    with pytest.raises(AttributeError):
        dasherize(None)

def test_dasherize_is_the_default_separator_behavior_of_parameterize():
    """dasherize is what converts underscores to the dash separator used by parameterize."""
    word = "already_dasherized"
    assert dasherize(word) == "already-dasherized"
    # parameterize only replaces characters outside [a-z0-9-_], so it leaves underscores alone;
    # dasherize is the function responsible for underscore-to-dash conversion.
    assert parameterize(word, "-") == "already_dasherized"
