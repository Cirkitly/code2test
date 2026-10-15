import pytest
from tinydb.queries import is_sequence

def test_is_sequence_returns_true_for_builtin_sequences():
    """Lists, tuples, sets, frozensets and strings all expose __iter__ and are sequences."""
    assert is_sequence([1, 2, 3]) is True
    assert is_sequence((1, 2, 3)) is True
    assert is_sequence({1, 2, 3}) is True
    assert is_sequence(frozenset({1, 2, 3})) is True
    assert is_sequence('abc') is True

def test_is_sequence_returns_true_for_empty_containers():
    """Empty iterables are still sequences -- the check is on the type, not the content."""
    assert is_sequence([]) is True
    assert is_sequence(()) is True
    assert is_sequence(set()) is True
    assert is_sequence('') is True

def test_is_sequence_returns_true_for_dicts_and_mappings():
    """Mappings iterate over their keys and therefore count as sequences."""
    assert is_sequence({}) is True
    assert is_sequence({'a': 1, 'b': 2}) is True

def test_is_sequence_returns_true_for_iterators_and_generators():
    """Iterators and generator objects support __iter__ and count as sequences."""
    assert is_sequence(iter([1, 2, 3])) is True
    assert is_sequence(iter({})) is True
    assert is_sequence(x for x in range(3)) is True

def test_is_sequence_returns_true_for_range_and_bytes():
    """range and bytes both provide __iter__ and must be classified as sequences."""
    assert is_sequence(range(5)) is True
    assert is_sequence(b'abc') is True

def test_is_sequence_returns_true_for_custom_class_defining_dunder_iter():
    """Duck typing: any object defining __iter__ is treated as a sequence."""

    class Sequence(object):
        def __init__(self, values):
            self.values = values

        def __iter__(self):
            return iter(self.values)

    assert is_sequence(Sequence([1, 2, 3])) is True

def test_is_sequence_returns_true_when_dunder_iter_attribute_exists_even_if_not_callable():
    """The implementation only checks attribute presence, not callability."""

    class Weird(object):
        __iter__ = None

    assert is_sequence(Weird()) is True

def test_is_sequence_returns_false_for_none():
    """None is not iterable."""
    assert is_sequence(None) is False

def test_is_sequence_returns_false_for_numeric_and_bool_values():
    """Ints, floats, complex numbers and booleans are not iterable."""
    assert is_sequence(1) is False
    assert is_sequence(3.14) is False
    assert is_sequence(2 + 3j) is False
    assert is_sequence(True) is False
    assert is_sequence(False) is False

def test_is_sequence_returns_false_for_custom_object_without_dunder_iter():
    """A class that does not define __iter__ is not a sequence."""

    class Plain(object):
        def __init__(self, value):
            self.value = value

    assert is_sequence(Plain(1)) is False

def test_is_sequence_returns_false_for_object_with_only_getitem():
    """Old-style sequence protocol (__getitem__ only) does not define __iter__."""

    class Legacy(object):
        def __init__(self, values):
            self.values = values

        def __getitem__(self, index):
            return self.values[index]

    assert is_sequence(Legacy([1, 2, 3])) is False

def test_is_sequence_returns_false_for_function_and_type_objects():
    """Callables are not sequences."""

    def some_function():
        pass

    assert is_sequence(some_function) is False
    assert is_sequence(len) is False
    assert is_sequence(int) is False

def test_is_sequence_always_returns_a_real_boolean():
    """is_sequence must return a genuine bool, not a truthy proxy value."""
    assert isinstance(is_sequence([1]), bool)
    assert isinstance(is_sequence(1), bool)
    assert isinstance(is_sequence('x'), bool)
    assert isinstance(is_sequence(None), bool)

def test_is_sequence_accepts_an_arbitrary_object_and_does_not_raise():
    """Passing an arbitrary instance must not raise, it simply reports a boolean."""

    class Anything(object):
        pass

    obj = Anything()
    result = is_sequence(obj)

    assert result is False

def test_is_sequence_is_pure_and_does_not_consume_the_iterable():
    """The check must be side-effect free: a generator stays usable afterwards."""
    gen = (x for x in range(3))

    assert is_sequence(gen) is True

    # The generator must not have been consumed by the check.
    assert list(gen) == [0, 1, 2]

def test_is_sequence_handles_inherited_dunder_iter_from_base_class():
    """hasattr also sees inherited attributes, so subclasses of iterable types pass."""

    class IterableBase(object):
        def __iter__(self):
            return iter([])

    class Derived(IterableBase):
        pass

    assert is_sequence(IterableBase()) is True
    assert is_sequence(Derived()) is True
