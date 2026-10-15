import pytest
from inflection import humanize

def test_humanize_replaces_underscores_with_spaces():
    """Test that underscores are replaced with spaces and the first character is capitalized."""
    # employee_salary -> "employee salary" -> "Employee salary"
    assert humanize("employee_salary") == "Employee salary"


def test_humanize_strips_trailing_id():
    """Test that a trailing '_id' is stripped from the string."""
    # author_id -> strip "_id" -> "author" -> "Author"
    assert humanize("author_id") == "Author"


def test_humanize_capitalizes_single_word():
    """Test that a single lowercase word is capitalized."""
    # "user" -> "user" -> "user" -> "User"
    assert humanize("user") == "User"


def test_humanize_lowercases_uppercase_input():
    """Test that uppercase input has all but the first character lowercased."""
    # "USER_NAME" -> "USER NAME" -> "user name" -> "User name"
    assert humanize("USER_NAME") == "User name"


def test_humanize_does_not_strip_id_when_not_at_end():
    """Test that '_id' is only stripped when at the end of the string."""
    # "user_id_123" -> "_id$" does not match (ends with "123") -> "user_id_123"
    # -> "user id 123" -> "user id 123" -> "User id 123"
    assert humanize("user_id_123") == "User id 123"


def test_humanize_does_not_strip_id_in_middle():
    """Test that '_id' in the middle of the string is not stripped."""
    # "foo_id_bar" -> "_id$" does not match (ends with "bar") -> "foo_id_bar"
    # -> "foo id bar" -> "foo id bar" -> "Foo id bar"
    assert humanize("foo_id_bar") == "Foo id bar"


def test_humanize_does_not_strip_id_when_case_differs():
    """Test that '_id' is only stripped when lowercase (case-sensitive regex)."""
    # "author_ID" -> "_id$" does not match (case-sensitive) -> "author_ID"
    # -> "author ID" -> "author id" (via (?i) lowercase) -> "Author id"
    assert humanize("author_ID") == "Author id"


def test_humanize_id_substring_at_start():
    """Test that 'id' at the start of the string is preserved and capitalized normally."""
    # "id_author" -> "_id$" does not match (ends with "hor") -> "id_author"
    # -> "id author" -> "id author" -> "Id author"
    assert humanize("id_author") == "Id author"


def test_humanize_handles_empty_string():
    """Test that an empty string returns an empty string."""
    assert humanize("") == ""


def test_humanize_handles_string_that_is_only_id():
    """Test that a string which is only '_id' returns an empty string."""
    # "_id" -> strip "_id" -> "" -> "" -> "" -> ""
    assert humanize("_id") == ""


def test_humanize_double_underscore_id_at_end():
    """Test that '__id' at the end strips the trailing '_id'."""
    # "user__id" -> strip "_id" -> "user_" -> "user " -> "user " -> "User "
    assert humanize("user__id") == "User "


def test_humanize_leading_underscore_preserved_as_space():
    """Test that a leading underscore becomes a leading space; first char is space, not \w."""
    # "_foo" -> no _id strip -> " foo" -> " foo" -> " foo" (space is not \w, no upper)
    assert humanize("_foo") == " foo"


def test_humanize_preserves_numbers():
    """Test that numbers in the string are preserved unchanged."""
    # "foo123" -> "foo123" -> "foo123" -> "Foo123" (\w uppercase on 'F')
    assert humanize("foo123") == "Foo123"


def test_humanize_already_humanized_string():
    """Test that an already humanized string is normalized to its title-cased form."""
    # "Employee salary" -> "Employee salary" -> "employee salary" -> "Employee salary"
    assert humanize("Employee salary") == "Employee salary"


def test_humanize_combined_underscore_and_id_strip():
    """Test that underscores are replaced and trailing _id is stripped together."""
    # "user_account_id" -> strip "_id" -> "user_account" -> "user account"
    # -> "user account" -> "User account"
    assert humanize("user_account_id") == "User account"


def test_humanize_raises_for_non_string_input():
    """Test that passing a non-string input raises TypeError or AttributeError."""
    # re.sub expects a string; passing an int triggers TypeError before .replace
    with pytest.raises((TypeError, AttributeError)):
        humanize(123)

