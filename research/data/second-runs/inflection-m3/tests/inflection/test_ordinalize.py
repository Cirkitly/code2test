import pytest
from inflection import ordinalize

def test_ordinalize_1_returns_1st_from_docstring():
    """1 should be ordinalized to '1st' (from the docstring example)."""
    assert ordinalize(1) == '1st'


def test_ordinalize_2_returns_2nd_from_docstring():
    """2 should be ordinalized to '2nd' (from the docstring example)."""
    assert ordinalize(2) == '2nd'


def test_ordinalize_1002_returns_1002nd_from_docstring():
    """1002 should be ordinalized to '1002nd' (from the docstring example)."""
    assert ordinalize(1002) == '1002nd'


def test_ordinalize_1003_returns_1003rd_from_docstring():
    """1003 should be ordinalized to '1003rd' (from the docstring example)."""
    assert ordinalize(1003) == '1003rd'


def test_ordinalize_neg_11_returns_neg_11th_from_docstring():
    """-11 should be ordinalized to '-11th' (from the docstring example)."""
    assert ordinalize(-11) == '-11th'


def test_ordinalize_neg_1021_returns_neg_1021st_from_docstring():
    """-1021 should be ordinalized to '-1021st' (from the docstring example)."""
    assert ordinalize(-1021) == '-1021st'


# ---------------------------------------------------------------------------
# Basic single-digit positive integers completing the 1-4 set
# ---------------------------------------------------------------------------

def test_ordinalize_3_returns_3rd():
    """3 should be ordinalized to '3rd' (basic 'rd' suffix case)."""
    assert ordinalize(3) == '3rd'


def test_ordinalize_4_returns_4th():
    """4 should be ordinalized to '4th' (basic default 'th' suffix case)."""
    assert ordinalize(4) == '4th'


# ---------------------------------------------------------------------------
# The teen number special case (11, 12, 13 always take 'th')
# ---------------------------------------------------------------------------

def test_ordinalize_11_returns_11th_not_11st():
    """11 should be ordinalized to '11th' (NOT '11st') because of the teen rule."""
    assert ordinalize(11) == '11th'


def test_ordinalize_12_returns_12th_not_12nd():
    """12 should be ordinalized to '12th' (NOT '12nd') because of the teen rule."""
    assert ordinalize(12) == '12th'


def test_ordinalize_13_returns_13th_not_13rd():
    """13 should be ordinalized to '13th' (NOT '13rd') because of the teen rule."""
    assert ordinalize(13) == '13th'


# ---------------------------------------------------------------------------
# Numbers whose last two digits end in 1/2/3 but are NOT teens
# ---------------------------------------------------------------------------

def test_ordinalize_21_returns_21st():
    """21 should be ordinalized to '21st' (last two digits 21, not a teen)."""
    assert ordinalize(21) == '21st'


def test_ordinalize_22_returns_22nd():
    """22 should be ordinalized to '22nd' (last two digits 22, not a teen)."""
    assert ordinalize(22) == '22nd'


def test_ordinalize_23_returns_23rd():
    """23 should be ordinalized to '23rd' (last two digits 23, not a teen)."""
    assert ordinalize(23) == '23rd'


# ---------------------------------------------------------------------------
# Hundreds: round hundred plus 101/102/103 (which mimic the 1/2/3 endings)
# ---------------------------------------------------------------------------

def test_ordinalize_100_returns_100th():
    """100 should be ordinalized to '100th' (round hundred uses 'th')."""
    assert ordinalize(100) == '100th'


def test_ordinalize_101_returns_101st():
    """101 should be ordinalized to '101st' (last two digits 01, ends in 1)."""
    assert ordinalize(101) == '101st'


def test_ordinalize_102_returns_102nd():
    """102 should be ordinalized to '102nd' (last two digits 02, ends in 2)."""
    assert ordinalize(102) == '102nd'


def test_ordinalize_103_returns_103rd():
    """103 should be ordinalized to '103rd' (last two digits 03, ends in 3)."""
    assert ordinalize(103) == '103rd'


# ---------------------------------------------------------------------------
# Teen-like endings in the hundreds place (111, 112, 113)
# ---------------------------------------------------------------------------

def test_ordinalize_111_returns_111th():
    """111 should be ordinalized to '111th' (last two digits are 11)."""
    assert ordinalize(111) == '111th'


def test_ordinalize_112_returns_112th():
    """112 should be ordinalized to '112th' (last two digits are 12)."""
    assert ordinalize(112) == '112th'


def test_ordinalize_113_returns_113th():
    """113 should be ordinalized to '113th' (last two digits are 13)."""
    assert ordinalize(113) == '113th'


# ---------------------------------------------------------------------------
# Edge case: zero
# ---------------------------------------------------------------------------

def test_ordinalize_0_produces_valid_ordinal_form():
    """0 must produce a string starting with '0' followed by a valid suffix."""
    result = ordinalize(0)
    assert result.startswith('0')
    valid_suffixes = {'st', 'nd', 'rd', 'th'}
    assert result[1:] in valid_suffixes


# ---------------------------------------------------------------------------
# Return type and structural contract tests
# ---------------------------------------------------------------------------

def test_ordinalize_returns_string_instance():
    """ord() must return a string instance (per its signature)."""
    assert isinstance(ordinalize(1), str)


def test_ordinalize_result_starts_with_string_form_of_input():
    """The output must begin with the str() representation of the input number."""
    test_inputs = [1, 2, 3, 11, 100, 1002, -11, -1021]
    for n in test_inputs:
        result = ordinalize(n)
        assert result.startswith(str(n)), (
            "ordinalize({0}) = {1!r} should start with {2!r}".format(
                n, result, str(n)
            )
        )


def test_ordinalize_suffix_is_among_valid_english_ordinal_suffixes():
    """The portion after the number must be one of 'st', 'nd', 'rd', or 'th'."""
    valid_suffixes = {'st', 'nd', 'rd', 'th'}
    # Cover boundary values and a variety of patterns
    test_inputs = [
        1, 2, 3, 4, 10, 11, 12, 13, 20, 21, 22, 23,
        100, 111, 121, 1002, -11, -100,
    ]
    for n in test_inputs:
        result = ordinalize(n)
        num_str = str(n)
        suffix = result[len(num_str):]
        assert suffix in valid_suffixes, (
            "ordinalize({0}) = {1!r} has invalid suffix {2!r}".format(
                n, result, suffix
            )
        )


def test_ordinalize_total_length_equals_digits_plus_two():
    """The total length of the result must equal len(str(number)) + 2."""
    for n in [1, 11, 100, 1002, -11, -1021]:
        result = ordinalize(n)
        assert len(result) == len(str(n)) + 2


def test_ordinalize_negative_inputs_produce_results_with_negative_prefix():
    """Negative inputs must produce results that begin with '-' (sign preserved)."""
    for n in [-1, -11, -21, -100, -1021]:
        result = ordinalize(n)
        assert result.startswith('-'), (
            "ordinalize({0}) = {1!r} should start with '-'".format(n, result)
        )


# ---------------------------------------------------------------------------
# Parametrized test for the suffix across many input values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("number,expected_suffix", [
    (1, 'st'),
    (2, 'nd'),
    (3, 'rd'),
    (4, 'th'),
    (11, 'th'),
    (12, 'th'),
    (13, 'th'),
    (21, 'st'),
    (22, 'nd'),
    (23, 'rd'),
    (100, 'th'),
    (101, 'st'),
    (102, 'nd'),
    (103, 'rd'),
    (111, 'th'),
    (112, 'th'),
    (113, 'th'),
    (121, 'st'),
    (122, 'nd'),
    (123, 'rd'),
    (1002, 'nd'),
    (1003, 'rd'),
    (1021, 'st'),
    (-11, 'th'),
    (-1021, 'st'),
])
def test_ordinalize_produces_correct_suffix_for_inputs(number, expected_suffix):
    """The suffix portion of ordinalize() should match the expected ordinal suffix."""
    result = ordinalize(number)
    num_str = str(number)
    actual_suffix = result[len(num_str):]
    assert actual_suffix == expected_suffix, (
        "ordinalize({0}) = {1!r}; got {2!r}, expected {3!r}".format(
            number, result, actual_suffix, expected_suffix
        )
    )
