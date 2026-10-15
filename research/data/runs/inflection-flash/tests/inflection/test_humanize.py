import pytest
from inflection import humanize

def test_humanize_replaces_underscores_with_spaces_and_capitalizes_first_word():
    assert humanize("employee_salary") == "Employee salary"

def test_humanize_strips_trailing_id_suffix():
    assert humanize("author_id") == "Author"

def test_humanize_keeps_non_trailing_id_substring():
    assert humanize("id_card") == "Id card"

def test_humanize_keeps_id_substring_inside_a_word():
    assert humanize("identity") == "Identity"

def test_humanize_strips_trailing_id_after_underscore_replacement():
    assert humanize("employee_author_id") == "Employee author"

def test_humanize_lowercases_existing_capital_letters_before_capitalizing_first_word():
    assert humanize("EmployeeSalary") == "Employeesalary"

def test_humanize_lowercases_trailing_uppercase_id_before_stripping():
    assert humanize("employee_ID") == "Employee id"

def test_humanize_lowercases_standalone_uppercase_input():
    assert humanize("ID") == "Id"

def test_humanize_returns_empty_string_for_input_that_is_only_an_id_suffix():
    assert humanize("_id") == ""

def test_humanize_returns_empty_string_for_empty_input():
    assert humanize("") == ""

def test_humanize_returns_string_type():
    result = humanize("employee_salary")
    assert isinstance(result, str)

def test_humanize_leaves_non_word_punctuation_untouched():
    assert humanize("employee-id") == "Employee-id"

def test_humanize_does_not_strip_trailing_id_without_underscore():
    assert humanize("authorid") == "Authorid"

def test_humanize_capitalizes_first_word_and_keeps_later_words_lowercase():
    assert humanize("employee_Salary") == "Employee salary"

def test_humanize_handles_multiple_underscores_by_producing_multiple_spaces():
    assert humanize("employee__salary") == "Employee  salary"

def test_humanize_leaves_leading_whitespace_uncapitalized():
    assert humanize("  leading") == "  leading"

def test_humanize_capitalizes_input_starting_with_a_digit():
    assert humanize("123_ABC") == "123 abc"

def test_humanize_preserves_digits_within_words():
    assert humanize("address_Line2") == "Address line2"

def test_humanize_does_not_strip_id_when_followed_by_more_characters():
    assert humanize("author_ids") == "Author ids"

def test_humanize_is_idempotent():
    for word in ("employee_salary", "author_id", "Employee Salary", "_id", ""):
        once = humanize(word)
        assert humanize(once) == once

def test_humanize_does_not_mutate_input_string():
    word = "employee_salary"
    humanize(word)
    assert word == "employee_salary"

def test_humanize_never_contains_underscores():
    for word in ("employee_salary", "author_id", "_id", "a_b_c", "__"):
        assert "_" not in humanize(word)

def test_humanize_does_not_produce_trailing_id_after_underscore_removal():
    for word in ("author_id", "employee_author_id", "author_id_extra"):
        result = humanize(word)
        if result:
            assert not result.endswith("id")

def test_humanize_raises_type_error_for_none_input():
    with pytest.raises(TypeError):
        humanize(None)

def test_humanize_raises_type_error_for_non_string_input():
    with pytest.raises(TypeError):
        humanize(42)

def test_humanize_raises_type_error_for_list_input():
    with pytest.raises(TypeError):
        humanize(["a"])
