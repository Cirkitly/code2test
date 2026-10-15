from inflection import humanize
import pytest

def test_humanize_replaces_underscores_with_spaces_and_capitalizes_first_word():
    assert humanize("employee_salary") == "Employee salary"

def test_humanize_returns_a_string():
    result = humanize("employee_salary")

    assert isinstance(result, str)

def test_humanize_strips_trailing_id_suffix():
    assert humanize("author_id") == "Author"

def test_humanize_strips_id_suffix_after_converting_underscored_words():
    assert humanize("employee_salary_id") == "Employee salary"

def test_humanize_strips_only_the_last_id_suffix():
    assert humanize("id_value_id") == "Id value"

def test_humanize_does_not_strip_id_when_not_at_the_end():
    assert humanize("employee_id_salary") == "Employee id salary"

def test_humanize_does_not_strip_uppercase_id_suffix():
    assert humanize("employee_ID") == "Employee id"

def test_humanize_keeps_bare_id_word_intact():
    assert humanize("id") == "Id"

def test_humanize_lowercases_the_remaining_underscored_words():
    assert humanize("Employee_Salary") == "Employee salary"

def test_humanize_lowercases_camel_case_input():
    assert humanize("EmployeeSalary") == "Employeesalary"

def test_humanize_is_a_no_op_for_already_humanized_text():
    assert humanize("Employee salary") == "Employee salary"

def test_humanize_is_idempotent():
    once = humanize("employee_salary")

    assert humanize(once) == once

def test_humanize_returns_empty_string_for_empty_input():
    assert humanize("") == ""

def test_humanize_returns_empty_string_when_input_is_only_the_id_suffix():
    assert humanize("_id") == ""

def test_humanize_preserves_leading_and_trailing_spaces_when_first_character_is_not_a_word_character():
    assert humanize("_id_") == " id "

def test_humanize_does_not_capitalize_when_the_string_starts_with_a_space():
    result = humanize("_id_id")

    assert result == " id"
    assert result[0].isspace()

def test_humanize_preserves_the_number_of_spaces_created_by_consecutive_underscores():
    assert humanize("employee__salary") == "Employee  salary"

def test_humanize_maps_a_string_of_only_underscores_to_the_same_number_of_spaces():
    result = humanize("__")

    assert result == "  "
    assert result.strip() == ""

def test_humanize_keeps_digits_and_capitalizes_the_letter_before_them():
    assert humanize("user2_id") == "User2"

def test_humanize_leaves_a_leading_digit_unchanged():
    assert humanize("3_column_name") == "3 column name"

def test_humanize_preserves_non_ascii_letters():
    result = humanize("café_id")

    assert result == "Café"
    assert "é" in result

def test_humanize_keeps_trailing_underscore_after_the_id_word():
    assert humanize("author_id_") == "Author id "

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("employee_salary", "Employee salary"),
        ("author_id", "Author"),
        ("employee_id", "Employee"),
        ("employee", "Employee"),
        ("employee_salary_id", "Employee salary"),
        ("id_value_id", "Id value"),
        ("employee_id_salary", "Employee id salary"),
        ("employee_ID", "Employee id"),
        ("Employee_Salary", "Employee salary"),
        ("_id_id", " id"),
        ("user2_id", "User2"),
        ("", ""),
        ("_id", ""),
    ],
)
def test_humanize_matches_expected_values_for_a_range_of_inputs(value, expected):
    assert humanize(value) == expected

def test_humanize_raises_type_error_for_none_input():
    with pytest.raises(TypeError):
        humanize(None)

def test_humanize_raises_type_error_for_integer_input():
    with pytest.raises(TypeError):
        humanize(42)

def test_humanize_raises_type_error_for_list_input():
    with pytest.raises(TypeError):
        humanize(["employee_salary"])

def test_humanize_raises_type_error_for_bytes_input():
    with pytest.raises(TypeError):
        humanize(b"employee_salary")
