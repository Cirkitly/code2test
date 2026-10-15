import pytest
from tinydb.queries import is_sequence

def test_is_sequence_returns_true_for_list():
    """Lists have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence([1, 2, 3]) is True

def test_is_sequence_returns_true_for_tuple():
    """Tuples have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence((1, 2, 3)) is True

def test_is_sequence_returns_true_for_string():
    """Strings have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence("hello") is True

def test_is_sequence_returns_true_for_dict():
    """Dicts have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence({"a": 1, "b": 2}) is True

def test_is_sequence_returns_true_for_set():
    """Sets have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence({1, 2, 3}) is True

def test_is_sequence_returns_true_for_frozenset():
    """Frozensets have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence(frozenset([1, 2, 3])) is True

def test_is_sequence_returns_true_for_generator():
    """Generator objects have an __iter__ attribute, so is_sequence must return True."""
    gen = (x for x in range(5))
    assert is_sequence(gen) is True

def test_is_sequence_returns_true_for_range():
    """Range objects have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence(range(5)) is True

def test_is_sequence_returns_true_for_bytes():
    """Bytes have an __iter__ attribute, so is_sequence must return True."""
    assert is_sequence(b"hello") is True

def test_is_sequence_returns_true_for_empty_containers():
    """Empty iterables still expose __iter__, so is_sequence must return True for them."""
    assert is_sequence([]) is True
    assert is_sequence(()) is True
    assert is_sequence("") is True
    assert is_sequence({}) is True
    assert is_sequence(set()) is True

def test_is_sequence_returns_true_for_custom_iterable():
    """Custom classes that implement __iter__ are recognized as sequences."""
    class MyIterable:
        def __iter__(self):
            return iter([1, 2, 3])

    assert is_sequence(MyIterable()) is True

def test_is_sequence_returns_true_when_iter_attribute_is_none():
    """hasattr only tests attribute existence; a __iter__ attribute set to None still matches."""
    class WithNoneIter:
        __iter__ = None

    assert is_sequence(WithNoneIter()) is True

def test_is_sequence_returns_false_for_integer():
    """Integers do not expose __iter__, so is_sequence must return False."""
    assert is_sequence(42) is False

def test_is_sequence_returns_false_for_float():
    """Floats do not expose __iter__, so is_sequence must return False."""
    assert is_sequence(3.14) is False

def test_is_sequence_returns_false_for_boolean():
    """Booleans do not expose __iter__, so is_sequence must return False."""
    assert is_sequence(True) is False
    assert is_sequence(False) is False

def test_is_sequence_returns_false_for_none():
    """None does not expose __iter__, so is_sequence must return False."""
    assert is_sequence(None) is False

def test_is_sequence_returns_false_for_bare_object():
    """A plain object() has no __iter__, so is_sequence must return False."""
    assert is_sequence(object()) is False

def test_is_sequence_returns_false_for_custom_non_iterable():
    """Custom classes without __iter__ are correctly rejected by is_sequence."""
    class NotIterable:
        pass

    assert is_sequence(NotIterable()) is False

def test_is_sequence_returns_false_for_function():
    """Function objects do not expose __iter__, so is_sequence must return False."""
    assert is_sequence(lambda x: x) is False

def test_is_sequence_returns_bool_type_for_iterable_input():
    """The result of is_sequence must be a bool instance, not just truthy."""
    result = is_sequence([1, 2, 3])
    assert isinstance(result, bool)

def test_is_sequence_returns_bool_type_for_non_iterable_input():
    """The result of is_sequence must be a bool instance even when the answer is False."""
    result = is_sequence(42)
    assert isinstance(result, bool)
