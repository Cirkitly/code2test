import pytest
from inflection import ordinalize

def test_ordinalize_returns_string():
    """The signature advertises ``str``; ordinalize must always return a string."""
    assert isinstance(ordinalize(1), str)
    assert isinstance(ordinalize(0), str)
    assert isinstance(ordinalize(-1021), str)

@pytest.mark.parametrize("number,expected", [
    (1, '1st'),
    (2, '2nd'),
    (3, '3rd'),
    (4, '4th'),
])
def test_ordinalize_first_four_use_documented_suffixes(number, expected):
    """The intent explicitly cites 1st, 2nd, 3rd, 4th as the canonical examples."""
    assert ordinalize(number) == expected

@pytest.mark.parametrize("number,expected", [
    (1, '1st'),
    (2, '2nd'),
    (1002, '1002nd'),
    (1003, '1003rd'),
    (-11, '-11th'),
    (-1021, '-1021st'),
])
def test_ordinalize_matches_all_documented_examples(number, expected):
    """Replicate each example from the source docstring and check the exact return value."""
    assert ordinalize(number) == expected

@pytest.mark.parametrize("number,expected", [
    (11, '11th'),
    (12, '12th'),
    (13, '13th'),
    (111, '111th'),
    (112, '112th'),
    (113, '113th'),
])
def test_ordinalize_teens_use_th_suffix(number, expected):
    """The docstring's -11 -> '-11th' confirms the standard English teen-exception rule."""
    assert ordinalize(number) == expected

@pytest.mark.parametrize("number,expected", [
    (21, '21st'),
    (22, '22nd'),
    (23, '23rd'),
    (101, '101st'),
    (102, '102nd'),
    (103, '103rd'),
])
def test_ordinalize_non_teen_endings_use_st_nd_rd(number, expected):
    """The 1002nd/1003rd docstring examples establish this pattern for non-teen endings."""
    assert ordinalize(number) == expected

def test_ordinalize_result_starts_with_number_string():
    """The implementation does str(number) + ordinal(number), so the prefix is the number."""
    assert ordinalize(42).startswith('42')
    assert ordinalize(100).startswith('100')
    assert ordinalize(-42).startswith('-42')
    assert ordinalize(-1021).startswith('-1021')

def test_ordinalize_negative_number_preserves_minus_sign():
    """str.format preserves the sign, and the -11 / -1021 docstring examples confirm it."""
    for n in [-1, -2, -3, -4, -11, -21, -100, -1021]:
        result = ordinalize(n)
        assert result.startswith('-'), f"ordinalize({n}) = {result!r} should start with '-'"

def test_ordinalize_always_ends_with_valid_suffix():
    """A valid English ordinal result is always suffixed by exactly one of these four endings."""
    sample = [1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 20, 21, 22, 23,
              100, 101, 102, 103, 111, 121, 1000, 1001,
              -11, -1021]
    for n in sample:
        result = ordinalize(n)
        assert result.endswith(('st', 'nd', 'rd', 'th')), (
            f"ordinalize({n}) = {result!r} does not end with a valid ordinal suffix"
        )
