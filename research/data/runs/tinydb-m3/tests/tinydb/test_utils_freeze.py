import pytest
from tinydb.utils import freeze, FrozenDict

import pytest
from tinydb.utils import freeze, FrozenDict


def test_freeze_dict_returns_frozendict():
    """A dict becomes a FrozenDict whose contents equal the original mapping."""
    result = freeze({"a": 1, "b": 2})

    assert isinstance(result, FrozenDict)
    assert dict(result) == {"a": 1, "b": 2}
    assert result["a"] == 1
    assert result["b"] == 2


def test_freeze_empty_dict_returns_empty_frozendict():
    """An empty dict is converted into an empty FrozenDict."""
    result = freeze({})

    assert isinstance(result, FrozenDict)
    assert len(result) == 0


def test_freeze_list_returns_tuple():
    """A list is converted into a tuple and its elements are preserved in order."""
    result = freeze([1, 2, 3])

    assert isinstance(result, tuple)
    assert not isinstance(result, list)
    assert result == (1, 2, 3)


def test_freeze_empty_list_returns_empty_tuple():
    """An empty list is converted into an empty tuple."""
    result = freeze([])

    assert isinstance(result, tuple)
    assert len(result) == 0


def test_freeze_set_returns_frozenset():
    """A set is converted into a frozenset with the same members."""
    result = freeze({1, 2, 3})

    assert isinstance(result, frozenset)
    assert not isinstance(result, set)
    assert result == frozenset({1, 2, 3})
    assert set(result) == {1, 2, 3}


def test_freeze_empty_set_returns_empty_frozenset():
    """An empty set is converted into an empty frozenset."""
    result = freeze(set())

    assert isinstance(result, frozenset)
    assert len(result) == 0


def test_freeze_int_unchanged():
    """Integers fall into the default branch and are returned unchanged."""
    result = freeze(42)

    assert result == 42
    assert isinstance(result, int)


def test_freeze_string_unchanged():
    """Strings fall into the default branch and are returned unchanged."""
    result = freeze("hello")

    assert result == "hello"
    assert isinstance(result, str)


def test_freeze_none_unchanged():
    """None falls into the default branch and is returned unchanged."""
    result = freeze(None)

    assert result is None


def test_freeze_tuple_unchanged():
    """Tuples are not lists, so they fall into the default branch unchanged."""
    original = (1, 2, 3)
    returned = freeze(original)

    assert returned is original
    assert isinstance(returned, tuple)
    assert returned == (1, 2, 3)


def test_freeze_frozenset_unchanged():
    """Frozensets are not sets (they are a distinct built-in type), so they are
    returned unchanged by the default branch."""
    original = frozenset({1, 2, 3})
    returned = freeze(original)

    assert returned is original
    assert isinstance(returned, frozenset)


def test_freeze_nested_dict_in_dict():
    """Nested dicts are recursively converted into FrozenDicts."""
    result = freeze({"outer": {"inner": 1}})

    assert isinstance(result, FrozenDict)
    assert isinstance(result["outer"], FrozenDict)
    assert result["outer"]["inner"] == 1


def test_freeze_list_containing_dict():
    """A dict inside a list is converted into a FrozenDict and the list becomes
    a tuple."""
    result = freeze([{"a": 1}])

    assert isinstance(result, tuple)
    assert isinstance(result[0], FrozenDict)
    assert dict(result[0]) == {"a": 1}


def test_freeze_dict_containing_list():
    """A list value inside a dict is converted into a tuple."""
    result = freeze({"items": [1, 2, 3]})

    assert isinstance(result, FrozenDict)
    assert isinstance(result["items"], tuple)
    assert not isinstance(result["items"], list)
    assert result["items"] == (1, 2, 3)


def test_freeze_dict_containing_set():
    """A set value inside a dict is converted into a frozenset."""
    result = freeze({"items": {1, 2, 3}})

    assert isinstance(result, FrozenDict)
    assert isinstance(result["items"], frozenset)
    assert result["items"] == frozenset({1, 2, 3})


def test_freeze_nested_lists():
    """Nested lists are recursively converted into tuples at every level."""
    result = freeze([[1, 2], [3, 4]])

    assert isinstance(result, tuple)
    assert isinstance(result[0], tuple)
    assert isinstance(result[1], tuple)
    assert result == ((1, 2), (3, 4))


def test_freeze_deeply_nested_structure():
    """All nested containers are converted to their frozen equivalents."""
    data = {"a": [{"b": {1, 2}}, [3, 4]]}
    result = freeze(data)

    # Top-level dict -> FrozenDict
    assert isinstance(result, FrozenDict)
    # The list value -> tuple
    assert isinstance(result["a"], tuple)
    # The dict inside the list -> FrozenDict
    assert isinstance(result["a"][0], FrozenDict)
    # The set inside the dict -> frozenset
    assert isinstance(result["a"][0]["b"], frozenset)
    assert result["a"][0]["b"] == frozenset({1, 2})
    # The inner list -> tuple
    assert isinstance(result["a"][1], tuple)
    assert result["a"][1] == (3, 4)


def test_freeze_frozendict_returns_frozendict():
    """A FrozenDict is a dict subclass, so it is converted into a new FrozenDict
    whose contents equal the original."""
    original = FrozenDict({"a": 1, "b": 2})
    result = freeze(original)

    assert isinstance(result, FrozenDict)
    assert dict(result) == {"a": 1, "b": 2}


def test_freeze_dict_with_none_value():
    """None values inside a dict are returned unchanged."""
    result = freeze({"a": None})

    assert isinstance(result, FrozenDict)
    assert "a" in result
    assert result["a"] is None


def test_freeze_list_with_none_elements():
    """None elements inside a list are preserved (returned as-is)."""
    result = freeze([None, 1, None])

    assert isinstance(result, tuple)
    assert result == (None, 1, None)
