import pytest
from inflection import ordinal

def test_ordinal_returns_suffix_for_basic_single_digits():
    """The four canonical suffixes: 1st, 2nd, 3rd, then 'th' for everything else."""
    assert ordinal(1) == "st"
    assert ordinal(2) == "nd"
    assert ordinal(3) == "rd"
    assert ordinal(4) == "th"

def test_ordinal_cycles_st_nd_rd_th_over_each_ten():
    """Units digit drives the suffix: 1->st, 2->nd, 3->rd, other->th."""
    # Bases chosen so that base+0..base+9 never land on 11, 12 or 13
    for base in (0, 20, 30, 100, 1000, 100000):
        assert ordinal(base + 1) == "st"
        assert ordinal(base + 2) == "nd"
        assert ordinal(base + 3) == "rd"
        assert ordinal(base + 4) == "th"
        assert ordinal(base + 5) == "th"
        assert ordinal(base + 9) == "th"
        assert ordinal(base + 0) == "th"


def test_ordinal_teens_always_end_in_th():
    """Numbers whose last two digits are 11, 12 or 13 take 'th', not st/nd/rd."""
    assert ordinal(11) == "th"
    assert ordinal(12) == "th"
    assert ordinal(13) == "th"
    assert ordinal(111) == "th"
    assert ordinal(112) == "th"
    assert ordinal(113) == "th"
    assert ordinal(1011) == "th"
    assert ordinal(1012) == "th"
    assert ordinal(1013) == "th"
    assert ordinal(10011) == "th"

def test_ordinal_twenty_one_and_friends_use_st_nd_rd():
    """Only 11-13 (mod 100) are special; 21/22/23 revert to the normal pattern."""
    assert ordinal(21) == "st"
    assert ordinal(22) == "nd"
    assert ordinal(23) == "rd"
    assert ordinal(31) == "st"
    assert ordinal(32) == "nd"
    assert ordinal(33) == "rd"
    assert ordinal(41) == "st"
    assert ordinal(43) == "rd"
    assert ordinal(99) == "th"
    assert ordinal(100) == "th"

def test_ordinal_large_numbers_use_only_last_two_digits():
    """Documented examples plus huge values; only the trailing digits matter."""
    assert ordinal(1002) == "nd"
    assert ordinal(1003) == "rd"
    assert ordinal(1001) == "st"
    assert ordinal(1004) == "th"
    assert ordinal(10013) == "th"
    assert ordinal(10021) == "st"
    assert ordinal(10 ** 20 + 3) == "rd"
    assert ordinal(10 ** 30 + 11) == "th"

def test_ordinal_zero_is_th():
    """0 has no st/nd/rd ending, so it falls through to the default suffix."""
    assert ordinal(0) == "th"

def test_ordinal_negative_numbers_mirror_positive_equivalents():
    """ordinal(-n) == ordinal(n) because abs() is applied first."""
    for n in range(1, 130):
        assert ordinal(-n) == ordinal(n), f"mismatch for -{-n}"

def test_ordinal_documented_negative_examples():
    """Reproduce the negative examples from the function docstring."""
    assert ordinal(-11) == "th"
    assert ordinal(-1021) == "st"
    assert ordinal(-1) == "st"
    assert ordinal(-2) == "nd"
    assert ordinal(-3) == "rd"
    assert ordinal(-13) == "th"

@pytest.mark.parametrize("number", [0, 1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101, 111, 1002, -11, -1021])
def test_ordinal_returns_a_two_character_suffix(number):
    """The function returns only the suffix, so it is always two characters long."""
    result = ordinal(number)
    assert isinstance(result, str)
    assert len(result) == 2

@pytest.mark.parametrize("number", [-130, -25, -3, -1, 0, 1, 2, 3, 4, 11, 13, 21, 23, 111, 1003, 999999])
def test_ordinal_suffix_is_always_one_of_four_values(number):
    """Only 'st', 'nd', 'rd' and 'th' are ever produced."""
    assert ordinal(number) in {"st", "nd", "rd", "th"}

def test_ordinal_accepts_integer_like_values():
    """int() coercion means numeric strings and floats are usable inputs."""
    assert ordinal("1") == "st"
    assert ordinal("2") == "nd"
    assert ordinal("3") == "rd"
    assert ordinal("21") == "st"
    assert ordinal("13") == "th"
    assert ordinal(True) == "st"

def test_ordinal_float_input_is_truncated_toward_zero():
    """int() truncates toward zero, so the suffix follows the truncated whole number."""
    assert ordinal(1.9) == "st"
    assert ordinal(2.99) == "nd"
    assert ordinal(3.0) == "rd"
    assert ordinal(-3.5) == "rd"
    assert ordinal(11.7) == "th"
    assert ordinal(21.4) == "st"

@pytest.mark.parametrize("value", ["abc", "st", "", "1st", "1.2.3", "--1"])
def test_ordinal_raises_value_error_for_non_numeric_string(value):
    """Non-numeric strings cannot be converted by int() and propagate ValueError."""
    with pytest.raises(ValueError):
        ordinal(value)

def test_ordinal_raises_type_error_for_none():
    """int(None) raises TypeError, which the function does not swallow."""
    with pytest.raises(TypeError):
        ordinal(None)

@pytest.mark.parametrize("value", [[1], {"n": 1}, {1, 2}, object()])
def test_ordinal_raises_type_error_for_unconvertible_types(value):
    """int() raises TypeError for containers and arbitrary objects."""
    with pytest.raises(TypeError):
        ordinal(value)

@pytest.mark.parametrize(
    "number, expected",
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
        (101, "101st"),
        (111, "111th"),
        (1002, "1002nd"),
        (1003, "1003rd"),
    ],
)
def test_ordinal_suffix_can_be_appended_to_form_a_readable_ordinal(number, expected):
    """str(number) + ordinal(number) produces the expected ordinal string."""
    assert f"{number}{ordinal(number)}" == expected

def test_ordinal_is_consistent_across_the_whole_small_range():
    """Exhaustive check of the teen exception and the units-digit mapping for 0..999."""
    expected = {
        1: "st",
        2: "nd",
        3: "rd",
    }
    for number in range(0, 1000):
        result = ordinal(number)
        if number % 100 in (11, 12, 13):
            assert result == "th", f"expected 'th' for {number}"
        else:
            assert result == expected.get(number % 10, "th"), f"wrong suffix for {number}"
