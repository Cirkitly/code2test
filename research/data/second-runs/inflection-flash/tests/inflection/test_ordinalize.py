import pytest
from inflection import ordinal
from inflection import ordinalize

@pytest.fixture
def small_numbers():
    """A short ascending sequence (1..40) used to exercise the ordinal suffix rules broadly."""
    return list(range(1, 41))

from inflection import ordinalize


def test_ordinalize_one_returns_first():
    """A number ending in 1 (without the 'teen' exception) gets the 'st' suffix."""
    assert ordinalize(1) == "1st"

from inflection import ordinalize


def test_ordinalize_two_returns_second():
    """A number ending in 2 (without the 'teen' exception) gets the 'nd' suffix."""
    assert ordinalize(2) == "2nd"

from inflection import ordinalize


def test_ordinalize_three_returns_third():
    """A number ending in 3 (without the 'teen' exception) gets the 'rd' suffix."""
    assert ordinalize(3) == "3rd"

from inflection import ordinalize


def test_ordinalize_four_returns_fourth():
    """Any other last digit yields the generic 'th' suffix, e.g. 4 -> '4th'."""
    assert ordinalize(4) == "4th"

import pytest

from inflection import ordinalize


@pytest.mark.parametrize(
    "number, expected",
    [
        (1, "1st"),
        (2, "2nd"),
        (1002, "1002nd"),
        (1003, "1003rd"),
        (-11, "-11th"),
        (-1021, "-1021st"),
    ],
)
def test_ordinalize_matches_documented_examples(number, expected):
    """The documented examples of ordinalize are reproduced exactly."""
    assert ordinalize(number) == expected

from inflection import ordinalize


def test_ordinalize_zero_has_generic_suffix():
    """Zero is not in the 1/2/3 or 11/12/13 exception lists, so it gets 'th'."""
    assert ordinalize(0) == "0th"

import pytest

from inflection import ordinalize


@pytest.mark.parametrize("number, expected", [(11, "11th"), (12, "12th"), (13, "13th")])
def test_ordinalize_teens_always_end_in_th(number, expected):
    """11/12/13 are the 'teen' exceptions and always take the 'th' suffix."""
    assert ordinalize(number) == expected

import pytest

from inflection import ordinalize


@pytest.mark.parametrize(
    "number, expected",
    [
        (111, "111th"),
        (112, "112th"),
        (113, "113th"),
        (211, "211th"),
        (1011, "1011th"),
        (1013, "1013th"),
        (1113, "1113th"),
        (10111, "10111th"),
        (10013, "10013th"),
    ],
)
def test_ordinalize_numbers_ending_in_teen_suffix_use_th(number, expected):
    """The 'teen' exception is driven by the last two digits, not the last one."""
    assert ordinalize(number) == expected

import pytest

from inflection import ordinalize


@pytest.mark.parametrize(
    "number, expected",
    [
        (1001, "1001st"),
        (1002, "1002nd"),
        (1003, "1003rd"),
        (1004, "1004th"),
        (100, "100th"),
        (1021, "1021st"),
        (1022, "1022nd"),
        (1023, "1023rd"),
    ],
)
def test_ordinalize_large_numbers_follow_last_two_digits(number, expected):
    """Large numbers keep all of their digits and pick the suffix from the tail."""
    assert ordinalize(number) == expected

import pytest

from inflection import ordinalize


@pytest.mark.parametrize(
    "number, expected",
    [
        (-1, "-1st"),
        (-2, "-2nd"),
        (-3, "-3rd"),
        (-4, "-4th"),
        (-11, "-11th"),
        (-12, "-12th"),
        (-13, "-13th"),
        (-21, "-21st"),
        (-1021, "-1021st"),
        (-111, "-111th"),
    ],
)
def test_ordinalize_negative_numbers_use_absolute_value_for_suffix(number, expected):
    """Negative numbers keep their sign while the suffix comes from |number|."""
    assert ordinalize(number) == expected

from inflection import ordinalize


def test_ordinalize_very_large_numbers_are_not_truncated():
    """Huge integers keep every digit and only gain a two letter suffix."""
    result = ordinalize(10**15)
    assert isinstance(result, str)
    assert result.endswith("th")  # 10**15 ends in 00 -> generic suffix
    assert result == "1000000000000000th"

from inflection import ordinalize


def test_ordinalize_returns_string_instance():
    """The function returns a new string, not an int or any other type."""
    assert isinstance(ordinalize(1), str)
    assert isinstance(ordinalize(42), str)
    assert isinstance(ordinalize(-7), str)

from inflection import ordinalize


def test_ordinalize_only_appends_a_two_character_suffix():
    """The digits of the input are preserved verbatim and 2 chars are appended."""
    for number in (0, 5, 17, 123, 4567, -9, -250):
        result = ordinalize(number)
        assert len(result) == len(str(number)) + 2
        assert result[:-2] == str(number)
        assert result[-2:] in ("st", "nd", "rd", "th")

from inflection import ordinalize


@pytest.fixture
def small_numbers():
    """A short ascending sequence used to exercise the suffix rules broadly."""
    return list(range(1, 41))


def test_ordinalize_suffix_matches_english_ordinal_rules(small_numbers):
    """For a whole sequence the suffix follows the last-two-digits rule."""
    last_digit_suffixes = {1: "st", 2: "nd", 3: "rd"}
    for number in small_numbers:
        if number % 100 in (11, 12, 13):
            suffix = "th"
        else:
            suffix = last_digit_suffixes.get(number % 10, "th")
        assert ordinalize(number) == f"{number}{suffix}"

from inflection import ordinalize


def test_ordinalize_produces_an_ordered_sequence_of_ordinals():
    """Consecutive positions read naturally: 1st, 2nd, 3rd, then 4th .. 20th."""
    ordinals = [ordinalize(number) for number in range(1, 21)]
    assert ordinals[:3] == ["1st", "2nd", "3rd"]
    assert ordinals[3] == "4th"
    assert ordinals[-1] == "20th"
    assert all(ordinal.startswith(str(number)) for number, ordinal in zip(range(1, 21), ordinals))

import pytest

from inflection import ordinal, ordinalize


@pytest.mark.parametrize(
    "number", [0, 1, 2, 3, 4, 11, 12, 13, 19, 21, 22, 23, 100, 101, 111, 1002, 1003, -11, -1021]
)
def test_ordinalize_appends_the_suffix_returned_by_ordinal(number):
    """ordinalize delegates the suffix decision to the ordinal() helper."""
    assert ordinalize(number) == f"{number}{ordinal(number)}"

import pytest

from inflection import ordinalize


@pytest.mark.parametrize("value", [None, [1], {"n": 1}, {1, 2}, (1,), object()])
def test_ordinalize_rejects_non_integer_arguments(value):
    """Values that abs() cannot handle fail loudly instead of being guessed at."""
    with pytest.raises(TypeError):
        ordinalize(value)

from inflection import ordinalize


def test_ordinalize_accepts_integer_subclasses_without_crashing():
    """bool is an int subclass: it must not crash and True behaves like 1."""
    result = ordinalize(True)
    assert isinstance(result, str)
    assert result.endswith("st")  # True == 1 -> 'st' suffix
