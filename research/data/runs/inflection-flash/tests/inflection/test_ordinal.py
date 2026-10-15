import pytest
from inflection import ordinal

@pytest.fixture
def expected_suffix_by_number():
    """Representative numbers paired with the suffix ``ordinal`` must return.

    The mapping covers the zero and single digit cases, the 11/12/13 teen
    exception, ordinary teens rows (21, 22, ...), round hundreds, thousands
    and millions so that both the "last digit" rule and the "last two digits"
    rule are exercised.
    """
    return {
        0: "th",
        1: "st",
        2: "nd",
        3: "rd",
        4: "th",
        5: "th",
        9: "th",
        10: "th",
        11: "th",
        12: "th",
        13: "th",
        14: "th",
        20: "th",
        21: "st",
        22: "nd",
        23: "rd",
        24: "th",
        100: "th",
        101: "st",
        102: "nd",
        103: "rd",
        111: "th",
        112: "th",
        113: "th",
        121: "st",
        1000: "th",
        1001: "st",
        1002: "nd",
        1003: "rd",
        10011: "th",
        10021: "st",
        999999: "th",
        1000000: "th",
        1000001: "st",
        1000002: "nd",
        1000003: "rd",
        1000011: "th",
    }

def test_ordinal_returns_st_for_one():
    """The number 1 denotes the first position, so its suffix is 'st'."""
    assert ordinal(1) == "st"

def test_ordinal_returns_nd_for_two():
    """The number 2 denotes the second position, so its suffix is 'nd'."""
    assert ordinal(2) == "nd"

def test_ordinal_returns_rd_for_three():
    """The number 3 denotes the third position, so its suffix is 'rd'."""
    assert ordinal(3) == "rd"

def test_ordinal_returns_th_for_four():
    """4th does not end in 1, 2 or 3, so the generic suffix 'th' is returned."""
    assert ordinal(4) == "th"

def test_ordinal_matches_expected_suffix_table(expected_suffix_by_number):
    """Every representative number maps to its documented ordinal suffix."""
    for number, expected in expected_suffix_by_number.items():
        assert ordinal(number) == expected, f"unexpected suffix for {number!r}"

@pytest.mark.parametrize(
    "number",
    [
        11, 12, 13,
        111, 112, 113,
        211, 212, 213,
        1011, 1012, 1013,
        1111, 1112, 1113,
        10011, 10012, 10013,
        1000011, 1000012, 1000013,
    ],
)
def test_ordinal_returns_th_for_teen_lookalikes(number):
    """Numbers ending in 11, 12 or 13 are 'th' regardless of their last digit."""
    assert ordinal(number) == "th"

@pytest.mark.parametrize(
    "number, expected",
    [
        (21, "st"),
        (22, "nd"),
        (23, "rd"),
        (24, "th"),
        (31, "st"),
        (42, "nd"),
        (53, "rd"),
        (101, "st"),
        (102, "nd"),
        (103, "rd"),
        (104, "th"),
        (10021, "st"),
        (10022, "nd"),
        (10023, "rd"),
    ],
)
def test_ordinal_uses_last_digit_outside_the_teens(number, expected):
    """Outside 11-13 the suffix follows the final digit of the number."""
    assert ordinal(number) == expected

@pytest.mark.parametrize(
    "number",
    [0, 10, 20, 30, 40, 100, 110, 200, 1000, 10_000, 1_000_000],
)
def test_ordinal_returns_th_for_numbers_ending_in_zero(number):
    """Numbers whose last digit is 0 get the generic 'th' suffix."""
    assert ordinal(number) == "th"

@pytest.mark.parametrize(
    "number, expected",
    [
        (1, "st"),
        (2, "nd"),
        (1002, "nd"),
        (1003, "rd"),
        (-11, "th"),
        (-1021, "st"),
    ],
)
def test_ordinal_matches_documented_examples(number, expected):
    """Every example from the component's documentation holds true."""
    assert ordinal(number) == expected

@pytest.mark.parametrize(
    "number, expected",
    [
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
        (-101, "st"),
        (-111, "th"),
        (-1021, "st"),
        (-1002, "nd"),
        (-1003, "rd"),
    ],
)
def test_ordinal_uses_absolute_value_for_negative_numbers(number, expected):
    """Negative inputs yield the same suffix as their absolute value."""
    assert ordinal(number) == expected

@pytest.mark.parametrize("base", [1, 2, 3, 4])
def test_ordinal_same_suffix_for_same_final_digit_across_tens(base):
    """A suffix depends only on the last two digits, so +20/+100 do not matter."""
    assert ordinal(base + 20) == ordinal(base)
    assert ordinal(base + 100) == ordinal(base)
    assert ordinal(base + 10_000) == ordinal(base)

@pytest.mark.parametrize("teen, unit", [(11, 1), (12, 2), (13, 3)])
def test_ordinal_treats_teens_as_an_exception_to_the_last_digit_rule(teen, unit):
    """11-13 are 'th' while 1-3 are 'st'/'nd'/'rd' despite the same last digit."""
    assert ordinal(teen) == "th"
    assert ordinal(teen + 100) == "th"
    assert ordinal(teen) != ordinal(unit)

def test_ordinal_returns_lowercase_two_letter_string():
    """Whatever the input, the returned suffix is a lowercase 2-letter string."""
    allowed_suffixes = {"st", "nd", "rd", "th"}
    for number in [0, 1, 2, 3, 4, 11, 13, 21, 100, 111, 1002, -1021]:
        suffix = ordinal(number)
        assert isinstance(suffix, str)
        assert suffix in allowed_suffixes
        assert suffix == suffix.lower()
        assert len(suffix) == 2

def test_ordinal_never_returns_an_empty_suffix_over_a_wide_sweep():
    """No number in a wide range yields an empty or unexpected suffix."""
    allowed_suffixes = {"st", "nd", "rd", "th"}
    for number in range(0, 1500):
        suffix = ordinal(number)
        assert suffix in allowed_suffixes, f"unexpected suffix {suffix!r} for {number}"

@pytest.mark.parametrize(
    "number, expected",
    [
        (10, "th"),
        (14, "th"),
        (19, "th"),
        (99, "th"),
        (100, "th"),
        (101, "st"),
        (102, "nd"),
        (103, "rd"),
        (1002, "nd"),
        (1003, "rd"),
        (1001, "st"),
        (1_000_000, "th"),
        (12_345_678, "th"),
        (1_234_561, "st"),
        (1_234_562, "nd"),
        (1_234_563, "rd"),
    ],
)
def test_ordinal_handles_multi_digit_and_large_numbers(number, expected):
    """Large numbers get the suffix implied by their final one or two digits."""
    assert ordinal(number) == expected

@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", "st"),
        ("2", "nd"),
        ("3", "rd"),
        ("4", "th"),
        ("11", "th"),
        ("12", "th"),
        ("13", "th"),
        ("21", "st"),
        ("-1021", "st"),
        ("+3", "rd"),
        (" 5 ", "th"),
        (" 21 ", "st"),
        ("0012", "th"),
    ],
)
def test_ordinal_accepts_numeric_strings(value, expected):
    """String inputs are converted with int() before the suffix is derived."""
    assert ordinal(value) == expected

@pytest.mark.parametrize(
    "value, expected",
    [
        (1.9, "st"),
        (2.7, "nd"),
        (3.99, "rd"),
        (4.5, "th"),
        (11.5, "th"),
        (13.9, "th"),
        (22.99, "nd"),
        (-1.9, "st"),
        (-2.9, "nd"),
        (-3.9, "rd"),
        (-13.9, "th"),
    ],
)
def test_ordinal_truncates_floats_towards_zero(value, expected):
    """Float inputs are truncated towards zero before the suffix is computed."""
    assert ordinal(value) == expected

def test_ordinal_accepts_booleans():
    """Booleans behave like the integers they are (1 and 0)."""
    assert ordinal(True) == "st"
    assert ordinal(False) == "th"

@pytest.mark.parametrize(
    "value, expected",
    [(b"1", "st"), (b"2", "nd"), (b"3", "rd"), (b"11", "th"), (b"21", "st")],
)
def test_ordinal_accepts_bytes_input(value, expected):
    """Bytes that represent digits are converted by int() like strings."""
    assert ordinal(value) == expected

@pytest.mark.parametrize(
    "value",
    ["abc", "", "   ", "st", "1.5", "1,000", "1st", "two", "0x10"],
)
def test_ordinal_raises_value_error_for_non_numeric_strings(value):
    """Strings that int() cannot parse raise ValueError mentioning int()."""
    with pytest.raises(ValueError) as excinfo:
        ordinal(value)
    assert "int()" in str(excinfo.value)

def test_ordinal_raises_type_error_for_none():
    """None cannot be converted with int() and therefore raises TypeError."""
    with pytest.raises(TypeError) as excinfo:
        ordinal(None)
    assert "int()" in str(excinfo.value)

@pytest.mark.parametrize(
    "value",
    [[1], (1,), {1: 2}, {"1": 2}, object(), 3 + 4j, ...],
)
def test_ordinal_raises_type_error_for_non_numeric_objects(value):
    """Objects without an int conversion protocol raise TypeError."""
    with pytest.raises(TypeError) as excinfo:
        ordinal(value)
    assert "int()" in str(excinfo.value)

def test_ordinal_is_pure_and_repeatable():
    """Repeated invocations with the same input return the same suffix."""
    first = ordinal(21)
    second = ordinal(21)
    third = ordinal(21)
    assert first == second == third == "st"
