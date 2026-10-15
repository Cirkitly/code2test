import pytest
from tinydb.queries import is_sequence

def test_is_sequence_returns_true_for_list():
    """A list exposes __iter__, so is_sequence returns True."""
    assert is_sequence([1, 2, 3]) is True

def test_is_sequence_returns_true_for_tuple():
    """A tuple exposes __iter__, so is_sequence returns True."""
    assert is_sequence(('a', 'b')) is True

def test_is_sequence_returns_true_for_string():
    """Strings are iterable, so is_sequence returns True."""
    assert is_sequence('hello') is True

def test_is_sequence_returns_true_for_empty_list():
    """An empty list still exposes __iter__, so is_sequence returns True."""
    assert is_sequence([]) is True

def test_is_sequence_returns_true_for_dict():
    """Dictionaries expose __iter__, so is_sequence returns True."""
    assert is_sequence({'a': 1}) is True

def test_is_sequence_returns_true_for_set():
    """Sets expose __iter__, so is_sequence returns True."""
    assert is_sequence({1, 2, 3}) is True

def test_is_sequence_returns_true_for_generator():
    """Generator objects expose __iter__, so is_sequence returns True."""
    assert is_sequence(x for x in range(3)) is True

def test_is_sequence_returns_true_for_bytes():
    """Bytes are iterable, so is_sequence returns True."""
    assert is_sequence(b'abc') is True

def test_is_sequence_returns_false_for_integer():
    """Integers have no __iter__, so is_sequence returns False."""
    assert is_sequence(5) is False

def test_is_sequence_returns_false_for_none():
    """None has no __iter__, so is_sequence returns False."""
    assert is_sequence(None) is False

def test_is_sequence_returns_false_for_float():
    """Floats have no __iter__, so is_sequence returns False."""
    assert is_sequence(1.5) is False

def test_is_sequence_returns_false_for_bool():
    """Booleans have no __iter__, so is_sequence returns False."""
    assert is_sequence(True) is False

def test_is_sequence_returns_false_for_plain_object():
    """A plain object() instance has no __iter__, so is_sequence returns False."""
    assert is_sequence(object()) is False

def test_is_sequence_ignores_getitem_only_iteration_protocol():
    """Only __iter__ counts; __getitem__ alone does not make a sequence."""
    class GetItemOnly:
        def __getitem__(self, key):
            raise KeyError(key)

    assert is_sequence(GetItemOnly()) is False

def test_is_sequence_depends_on_explicit_dunder_iter_definition():
    """Custom classes are sequences only when they define __iter__ themselves."""
    class WithIter:
        def __iter__(self):
            return iter([1, 2])

    class WithoutIter:
        pass

    assert is_sequence(WithIter()) is True
    assert is_sequence(WithoutIter()) is False

def test_is_sequence_always_returns_a_real_boolean():
    """The result is always a bool, never a truthy/falsy proxy object."""
    for candidate in ([1], 'a', {'k': 1}, 7, None, object()):
        assert isinstance(is_sequence(candidate), bool)

def test_is_sequence_does_not_consume_an_iterator():
    """The check only inspects attributes and does not exhaust an iterator."""
    iterator = iter([1, 2, 3])
    assert is_sequence(iterator) is True
    assert list(iterator) == [1, 2, 3]

def test_is_sequence_propagates_non_attribute_errors_from_lookup():
    """hasattr only swallows AttributeError; other lookup errors propagate."""

    class Boom:
        @property
        def __iter__(self):
            raise RuntimeError('boom')

    with pytest.raises(RuntimeError):
        is_sequence(Boom())
