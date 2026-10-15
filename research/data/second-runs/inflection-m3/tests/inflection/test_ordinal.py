import pytest
from inflection import ordinal

def test_ordinal_1_returns_st():
    """Primary happy path: ordinal(1) returns 'st' for the 1st position."""
    assert ordinal(1) == "st"


def test_ordinal_2_returns_nd():
    """Primary happy path: ordinal(2) returns 'nd' for the 2nd position."""
    assert ordinal(2) == "nd"


def test_ordinal_3_returns_rd():
    """Primary happy path: ordinal(3) returns 'rd' for the 3rd position."""
    assert ordinal(3) == "rd"


def test_ordinal_4_returns_th():
    """Primary happy path: ordinal(4) returns 'th' since 4 % 10 == 4 is not 1, 2, or 3."""
    assert ordinal(4) == "th"


def test_ordinal_1002_returns_nd():
    """Docstring example: ordinal(1002) returns 'nd' (1002 % 100 == 2, 1002 % 10 == 2)."""
    assert ordinal(1002) == "nd"


def test_ordinal_1003_returns_rd():
    """Docstring example: ordinal(1003) returns 'rd' (1003 % 100 == 3, 1003 % 10 == 3)."""
    assert ordinal(1003) == "rd"


def test_ordinal_negative_11_returns_th():
    """Docstring example: ordinal(-11) returns 'th' (abs(-11) % 100 == 11)."""
    assert ordinal(-11) == "th"


def test_ordinal_negative_1021_returns_st():
    """Docstring example: ordinal(-1021) returns 'st' (abs(-1021) % 100 == 21, 1021 % 10 == 1)."""
    assert ordinal(-1021) == "st"


@pytest.mark.parametrize("number", [11, 12, 13, 111, 112, 113, 211, 1011, 1012, 1013, 1111, 1112, 1113])
def test_ordinal_special_eleven_twelve_thirteen(number):
    """ordinal returns 'th' for any number whose last two digits are 11, 12, or 13."""
    assert ordinal(number) == "th"


@pytest.mark.parametrize("number,expected", [
    (21, "st"),
    (22, "nd"),
    (23, "rd"),
    (31, "st"),
    (32, "nd"),
    (33, "rd"),
    (101, "st"),
    (102, "nd"),
    (103, "rd"),
    (121, "st"),
    (122, "nd"),
    (123, "rd"),
    (1001, "st"),
    (1002, "nd"),
    (1003, "rd"),
])
def test_ordinal_ending_in_one_two_three(number, expected):
    """ordinal returns 'st', 'nd', 'rd' for numbers ending in 1, 2, 3 (not in 11, 12, 13)."""
    assert ordinal(number) == expected


@pytest.mark.parametrize("number", [0, 5, 6, 7, 8, 9, 10, 14, 15, 19, 20, 24, 25, 29, 30, 100, 1000])
def test_ordinal_returns_th_for_other_endings(number):
    """ordinal returns 'th' for numbers whose last digit is 0, 4, 5, 6, 7, 8, or 9."""
    assert ordinal(number) == "th"


@pytest.mark.parametrize("number,expected", [
    (10, "th"),
    (11, "th"),
    (12, "th"),
    (13, "th"),
    (14, "th"),
    (110, "th"),
    (111, "th"),
    (112, "th"),
    (113, "th"),
    (114, "th"),
])
def test_ordinal_boundary_around_eleven_thirteen(number, expected):
    """ordinal returns 'th' for 10-14 and 110-114 (the 11/12/13 special case applies)."""
    assert ordinal(number) == expected


@pytest.mark.parametrize("number,expected", [
    (-1, "st"),
    (-2, "nd"),
    (-3, "rd"),
    (-4, "th"),
    (-11, "th"),
    (-12, "th"),
    (-13, "th"),
    (-21, "st"),
    (-22, "nd"),
    (-23, "rd"),
    (-100, "th"),
    (-1021, "st"),
])
def test_ordinal_handles_negative_numbers(number, expected):
    """ordinal uses abs(number) to determine the suffix for negative inputs."""
    assert ordinal(number) == expected


@pytest.mark.parametrize("number", [0, 1, 2, 3, 4, 11, 12, 13, 100, 1002, -1, -11, -1021])
def test_ordinal_always_returns_string(number):
    """ordinal always returns a str instance for any valid numeric input."""
    result = ordinal(number)
    assert isinstance(result, str)
    assert result in ("st", "nd", "rd", "th")


@pytest.mark.parametrize("number,expected", [
    (1.0, "st"),
    (1.9, "st"),
    (2.5, "nd"),
    (3.99, "rd"),
    (11.1, "th"),
    (12.9, "th"),
    (-1.5, "st"),
])
def test_ordinal_accepts_float_input(number, expected):
    """ordinal accepts float input by truncating to int via int() before processing."""
    assert ordinal(number) == expected


@pytest.mark.parametrize("number,expected", [
    ("1", "st"),
    ("2", "nd"),
    ("3", "rd"),
    ("4", "th"),
    ("11", "th"),
    ("1002", "nd"),
    ("-11", "th"),
])
def test_ordinal_accepts_numeric_string_input(number, expected):
    """ordinal accepts string input that int() can parse, converting before processing."""
    assert ordinal(number) == expected


def test_ordinal_raises_value_error_for_non_numeric_string():
    """ordinal raises ValueError when given a string that cannot be parsed by int()."""
    with pytest.raises(ValueError):
        ordinal("not a number")


def test_ordinal_raises_type_error_for_none():
    """ordinal raises TypeError when given None (int(None) is not allowed)."""
    with pytest.raises(TypeError):
        ordinal(None)


@pytest.mark.parametrize("number,expected", [
    (1000000, "th"),
    (1000001, "st"),
    (1000002, "nd"),
    (1000003, "rd"),
    (1000011, "th"),
    (1000012, "th"),
    (1000013, "th"),
])
def test_ordinal_handles_very_large_numbers(number, expected):
    """ordinal works correctly for very large numbers based on their last two digits."""
    assert ordinal(number) == expected

