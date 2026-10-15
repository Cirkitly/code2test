import pytest
from inflection import ordinal

def test_ordinal_one_returns_st():
    """Verify ordinal(1) returns 'st' as documented in the docstring."""
    assert ordinal(1) == "st"

def test_ordinal_two_returns_nd():
    """Verify ordinal(2) returns 'nd' as documented in the docstring."""
    assert ordinal(2) == "nd"

def test_ordinal_three_returns_rd():
    """Verify ordinal(3) returns 'rd' (basic case for ending in 3 but not 13)."""
    assert ordinal(3) == "rd"

def test_ordinal_four_returns_th():
    """Verify ordinal(4) returns 'th' (default case for numbers not ending in 1/2/3)."""
    assert ordinal(4) == "th"

def test_ordinal_docstring_example_1002_returns_nd():
    """Verify ordinal(1002) returns 'nd' (docstring example: 1002 ends in 2)."""
    assert ordinal(1002) == "nd"

def test_ordinal_docstring_example_1003_returns_rd():
    """Verify ordinal(1003) returns 'rd' (docstring example: 1003 ends in 3)."""
    assert ordinal(1003) == "rd"

def test_ordinal_docstring_example_neg_11_returns_th():
    """Verify ordinal(-11) returns 'th' (docstring example: teens special case)."""
    assert ordinal(-11) == "th"

def test_ordinal_docstring_example_neg_1021_returns_st():
    """Verify ordinal(-1021) returns 'st' (docstring example: negative uses abs)."""
    assert ordinal(-1021) == "st"

def test_ordinal_eleven_returns_th():
    """Verify ordinal(11) returns 'th' (teens special case: 11, 12, 13 always get 'th')."""
    assert ordinal(11) == "th"

def test_ordinal_twelve_returns_th():
    """Verify ordinal(12) returns 'th' (teens special case)."""
    assert ordinal(12) == "th"

def test_ordinal_thirteen_returns_th():
    """Verify ordinal(13) returns 'th' (teens special case)."""
    assert ordinal(13) == "th"

@pytest.mark.parametrize("number,expected", [
    (111, "th"),  # 111 % 100 = 11
    (112, "th"),  # 112 % 100 = 12
    (113, "th"),  # 113 % 100 = 13
    (211, "th"),  # 211 % 100 = 11
    (212, "th"),  # 212 % 100 = 12
    (213, "th"),  # 213 % 100 = 13
    (1011, "th"),  # 1011 % 100 = 11
    (1012, "th"),  # 1012 % 100 = 12
    (1013, "th"),  # 1013 % 100 = 13
    (114, "th"),  # 114 % 10 = 4
    (121, "st"),  # 121 % 100 = 21, % 10 = 1
    (122, "nd"),  # 122 % 100 = 22, % 10 = 2
    (123, "rd"),  # 123 % 100 = 23, % 10 = 3
])
def test_ordinal_higher_teens_use_last_digit(number, expected):
    """Verify numbers like 111, 112, 113 (mod 100 in 11-13) get 'th', while 114+ use last digit."""
    assert ordinal(number) == expected

def test_ordinal_zero_returns_th():
    """Verify ordinal(0) returns 'th' (0 % 10 = 0 falls through to default)."""
    assert ordinal(0) == "th"

def test_ordinal_negative_one_returns_st():
    """Verify negative numbers use absolute value: ordinal(-1) returns 'st'."""
    assert ordinal(-1) == "st"

def test_ordinal_negative_two_returns_nd():
    """Verify negative numbers use absolute value: ordinal(-2) returns 'nd'."""
    assert ordinal(-2) == "nd"

def test_ordinal_negative_three_returns_rd():
    """Verify negative numbers use absolute value: ordinal(-3) returns 'rd'."""
    assert ordinal(-3) == "rd"

def test_ordinal_negative_four_returns_th():
    """Verify negative numbers use absolute value: ordinal(-4) returns 'th'."""
    assert ordinal(-4) == "th"

@pytest.mark.parametrize("value,expected", [
    ("1", "st"),
    ("2", "nd"),
    ("3", "rd"),
    ("4", "th"),
    ("11", "th"),
    ("21", "st"),
    ("-1", "st"),
])
def test_ordinal_string_number_is_accepted(value, expected):
    """Verify that numeric strings are accepted via int() coercion."""
    assert ordinal(value) == expected

@pytest.mark.parametrize("value,expected", [
    (1.9, "st"),
    (2.5, "nd"),
    (3.0, "rd"),
    (11.7, "th"),
])
def test_ordinal_float_is_truncated_via_int(value, expected):
    """Verify that floats are truncated to int (e.g., 1.9 -> 1 -> 'st')."""
    assert ordinal(value) == expected

@pytest.mark.parametrize("value", [0, 1, 2, 3, 4, 10, 11, 12, 13, 21, 100, 101, 111, -1, -11])
def test_ordinal_returns_string_type(value):
    """Verify that ordinal always returns a string type."""
    assert isinstance(ordinal(value), str)

@pytest.mark.parametrize("value", [0, 1, 2, 3, 4, 10, 11, 12, 13, 21, 100, 101, 111, 1002, 1003, -11, -1021])
def test_ordinal_return_is_one_of_valid_suffixes(value):
    """Verify that the returned suffix is always one of the four valid suffixes."""
    assert ordinal(value) in ("st", "nd", "rd", "th")

def test_ordinal_non_numeric_string_raises_value_error():
    """Verify that a non-numeric string raises ValueError from int() conversion."""
    with pytest.raises(ValueError):
        ordinal("abc")

def test_ordinal_none_raises_type_error():
    """Verify that None raises TypeError because int(None) is invalid."""
    with pytest.raises(TypeError):
        ordinal(None)

@pytest.mark.parametrize("value", [[], {}, set(), object()])
def test_ordinal_invalid_type_raises_type_error(value):
    """Verify that types that cannot be coerced (list, dict, set) raise TypeError."""
    with pytest.raises(TypeError):
        ordinal(value)

@pytest.mark.parametrize("number,expected", [
    (1000001, "st"),   # ends in 1, not teens
    (1000002, "nd"),   # ends in 2, not teens
    (1000003, "rd"),   # ends in 3, not teens
    (1000011, "th"),   # 11 in last two digits
    (1000012, "th"),   # 12 in last two digits
    (1000013, "th"),   # 13 in last two digits
    (1000021, "st"),   # 21 in last two digits, ends in 1
])
def test_ordinal_large_numbers_modulo_behavior(number, expected):
    """Verify that very large numbers follow the same modulo rules."""
    assert ordinal(number) == expected

def test_ordinal_ten_returns_th():
    """Verify ordinal(10) returns 'th' (10 ends in 0, default branch)."""
    assert ordinal(10) == "th"

def test_ordinal_twenty_returns_th():
    """Verify ordinal(20) returns 'th' (20 ends in 0, not teens, default branch)."""
    assert ordinal(20) == "th"

def test_ordinal_hundred_returns_th():
    """Verify ordinal(100) returns 'th' (100 ends in 0, not teens)."""
    assert ordinal(100) == "th"
