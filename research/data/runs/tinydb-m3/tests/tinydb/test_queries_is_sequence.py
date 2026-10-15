import pytest
from tinydb.queries import is_sequence

def test_is_sequence_with_list_returns_true():
    """Lists have __iter__ so is_sequence must return True."""
    assert is_sequence([1, 2, 3]) is True

def test_is_sequence_with_tuple_returns_true():
    """Tuples have __iter__ so is_sequence must return True."""
    assert is_sequence((1, 2, 3)) is True

def test_is_sequence_with_empty_list_returns_true():
    """An empty list still has __iter__, so it must be classified as a sequence."""
    assert is_sequence([]) is True

def test_is_sequence_with_string_returns_true():
    """Strings are iterable, so is_sequence must return True."""
    assert is_sequence("hello") is True

def test_is_sequence_with_dict_returns_true():
    """Dicts are iterable mappings, so is_sequence must return True."""
    assert is_sequence({"a": 1, "b": 2}) is True

def test_is_sequence_with_set_returns_true():
    """Sets are iterable, so is_sequence must return True."""
    assert is_sequence({1, 2, 3}) is True

def test_is_sequence_with_generator_returns_true():
    """Generators expose __iter__, so is_sequence must return True."""
    def gen():
        yield 1
        yield 2
    assert is_sequence(gen()) is True

def test_is_sequence_with_custom_iterable_returns_true():
    """A user-defined class that defines __iter__ must be classified as a sequence."""

    class MyIterable:
        def __iter__(self):
            return iter([1, 2, 3])

    assert is_sequence(MyIterable()) is True

def test_is_sequence_with_int_returns_false():
    """Integers are not iterable, so is_sequence must return False."""
    assert is_sequence(42) is False

def test_is_sequence_with_float_returns_false():
    """Floats are not iterable, so is_sequence must return False."""
    assert is_sequence(3.14) is False

def test_is_sequence_with_none_returns_false():
    """None is not iterable, so is_sequence must return False."""
    assert is_sequence(None) is False

def test_is_sequence_with_bool_returns_false():
    """Booleans are not iterable, so is_sequence must return False."""
    assert is_sequence(True) is False
    assert is_sequence(False) is False

def test_is_sequence_with_plain_object_returns_false():
    """A custom class without __iter__ must not be classified as a sequence."""

    class Plain:
        pass

    assert is_sequence(Plain()) is False

def test_is_sequence_returns_boolean_type():
    """The function must return a real bool, since it performs a boolean check."""
    positive_result = is_sequence([1, 2])
    negative_result = is_sequence(42)

    assert isinstance(positive_result, bool)
    assert isinstance(negative_result, bool)
    assert positive_result is True
    assert negative_result is False

def test_is_sequence_missing_argument_raises_type_error():
    """Calling is_sequence with no arguments must raise TypeError because obj is required."""
    with pytest.raises(TypeError):
        is_sequence()
