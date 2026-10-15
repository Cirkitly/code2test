import pytest
from inflection import ordinal, ordinalize

def test_ordinalize_returns_ordinal_suffix_for_basic_numbers():
    assert ordinalize(1) == '1st'
    assert ordinalize(2) == '2nd'
    assert ordinalize(3) == '3rd'
    assert ordinalize(4) == '4th'

def test_ordinalize_result_is_a_string_containing_the_number_and_suffix():
    result = ordinalize(37)
    assert isinstance(result, str)
    assert result.startswith('37')
    # The remainder after the numeric prefix must be a non-empty, alphabetic suffix.
    suffix = result[len('37'):]
    assert suffix.isalpha()

def test_ordinalize_large_numbers_use_last_two_digits_for_teen_tens():
    assert ordinalize(1002) == '1002nd'
    assert ordinalize(1003) == '1003rd'
    assert ordinalize(1011) == '1011th'
    assert ordinalize(1012) == '1012th'
    assert ordinalize(1013) == '1013th'

def test_ordinalize_teens_always_use_th_suffix():
    assert ordinalize(11) == '11th'
    assert ordinalize(12) == '12th'
    assert ordinalize(13) == '13th'

def test_ordinalize_last_digit_determines_suffix():
    assert ordinalize(21) == '21st'
    assert ordinalize(32) == '32nd'
    assert ordinalize(43) == '43rd'
    assert ordinalize(54) == '54th'
    assert ordinalize(65) == '65th'
    assert ordinalize(9) == '9th'

def test_ordinalize_zero_uses_th_suffix():
    assert ordinalize(0) == '0th'

def test_ordinalize_negative_numbers_preserve_sign():
    assert ordinalize(-11) == '-11th'
    assert ordinalize(-1021) == '-1021st'
    assert ordinalize(-1) == '-1st'
    assert ordinalize(-2) == '-2nd'
    assert ordinalize(-3) == '-3rd'

def test_ordinalize_large_number_prefix_is_preserved_verbatim():
    number = 10 ** 18 + 3
    result = ordinalize(number)
    assert result == str(number) + 'rd'
    assert result.startswith('1000000000000000003')

def test_ordinalize_round_trips_the_string_form_of_the_number():
    for number in range(0, 40):
        assert ordinalize(number) == '{}{}'.format(number, ordinal(number))

def test_ordinalize_is_idempotent_against_ordinal_suffix_agreement():
    for number in [0, 1, 2, 3, 4, 10, 11, 12, 13, 14, 21, 22, 23, 100, 101, 111, 112, 113, 1000, 1002, 1003, -11, -21, -1021]:
        result = ordinalize(number)
        assert result.endswith(ordinal(number))

def test_ordinalize_returns_only_digits_sign_and_suffix():
    for number in [-1021, -13, -4, 0, 1, 12, 123, 4567]:
        result = ordinalize(number)
        body = result[1:] if result.startswith('-') else result
        digits = ''.join(char for char in body if char.isdigit())
        suffix = ''.join(char for char in body if not char.isdigit())
        assert digits == str(abs(number))
        assert suffix.isalpha()
        assert suffix.islower()

def test_ordinalize_raises_type_error_for_non_integer_input():
    with pytest.raises(TypeError):
        ordinalize([1, 2, 3])

def test_ordinalize_raises_type_error_for_none_input():
    with pytest.raises(TypeError):
        ordinalize(None)

def test_ordinalize_accepts_boolean_input_without_crashing():
    # bool is a subclass of int, so it flows through the numeric suffix lookup
    # (True % 100 == 1 -> "st") and is stringified as "True" rather than raising.
    result = ordinalize(True)  # must not raise

    assert isinstance(result, str)
    assert result == "Truest"

def test_ordinalize_does_not_mutate_or_require_external_state():
    first = ordinalize(23)
    other = ordinalize(23)
    assert first == other == '23rd'
