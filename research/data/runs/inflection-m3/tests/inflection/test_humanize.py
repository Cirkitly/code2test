import pytest
from inflection import humanize

def test_humanize_simple_snake_case_to_titlecase():
    """employee_salary -> Employee salary (primary happy path from docstring)."""
    assert humanize("employee_salary") == "Employee salary"


def test_humanize_strips_trailing_underscore_id():
    """author_id -> Author (docstring example: trailing _id is stripped)."""
    assert humanize("author_id") == "Author"


def test_humanize_uppercase_word_becomes_titlecase():
    """All-uppercase input is lowercased word-by-word and only the first letter capitalized."""
    assert humanize("EMPLOYEE_SALARY") == "Employee salary"


def test_humanize_mixed_case_words_become_titlecase():
    """Each word in mixed case is lowercased individually; only the first char is uppercased."""
    assert humanize("MiXeD_CaSe_Word") == "Mixed case word"


def test_humanize_already_lowercase_only_first_letter_capitalized():
    """Already-lowercase text only has its first character uppercased."""
    assert humanize("already lowercase words") == "Already lowercase words"


def test_humanize_id_in_middle_is_not_stripped():
    """An internal _id substring is preserved; the regex only removes a trailing _id."""
    assert humanize("user_id_42") == "User id 42"


def test_humanize_trailing_id_strip_is_case_sensitive():
    """The trailing-strip regex has no IGNORECASE flag, so '_ID' (uppercase) is NOT removed."""
    assert humanize("foo_ID") == "Foo id"


def test_humanize_empty_string_returns_empty():
    """Empty input produces empty output (no leading \\w to capitalize)."""
    assert humanize("") == ""


def test_humanize_standalone_id_is_not_stripped():
    """The word 'id' without a leading underscore is not considered a trailing _id suffix."""
    assert humanize("id") == "Id"


def test_humanize_only_underscore_id_yields_empty():
    """A bare '_id' is fully consumed by the trailing-strip step, resulting in ''."""
    assert humanize("_id") == ""


def test_humanize_camelcase_input_is_fully_lowercased():
    """camelCase input has the entire string lowercased; the capital mid-word is not preserved."""
    assert humanize("helloWorld") == "Helloworld"


def test_humanize_consecutive_underscores_become_consecutive_spaces():
    """Each underscore is replaced independently, so two underscores yield two spaces."""
    assert humanize("hello__world") == "Hello  world"


def test_humanize_trailing_underscore_becomes_trailing_space():
    """A trailing underscore is replaced with a trailing space and only the first letter is then capped."""
    assert humanize("foo_") == "Foo "


def test_humanize_non_string_input_raises_type_error():
    """Passing a non-string value (e.g. an int) causes re.sub to raise TypeError."""
    with pytest.raises(TypeError):
        humanize(123)
