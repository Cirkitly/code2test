import pytest
from collections import OrderedDict
from tinydb.utils import freeze, FrozenDict

def test_freeze_dict_returns_frozendict_instance():
    """A dict should be transformed into a FrozenDict instance (traced from the dict branch)."""
    result = freeze({"a": 1})
    assert isinstance(result, FrozenDict)


def test_freeze_dict_preserves_keys_and_values():
    """Freezing a dict should preserve the keys and values."""
    result = freeze({"a": 1, "b": 2})
    assert dict(result) == {"a": 1, "b": 2}


def test_freeze_dict_returns_new_object_not_original():
    """freeze should return a new object rather than the original dict instance."""
    original = {"a": 1}
    result = freeze(original)
    assert result is not original


def test_freeze_dict_result_is_still_a_dict():
    """A FrozenDict subclasses dict, so freeze(dict) result must remain a dict instance."""
    result = freeze({"a": 1})
    assert isinstance(result, dict)


def test_freeze_dict_recursively_freezes_list_values():
    """List values inside a dict should be recursively frozen into tuples."""
    result = freeze({"items": [1, 2, 3]})
    assert isinstance(result["items"], tuple)
    assert result["items"] == (1, 2, 3)


def test_freeze_dict_recursively_freezes_nested_dict_values():
    """Nested dict values should themselves be frozen into FrozenDicts."""
    result = freeze({"outer": {"inner": 1}})
    assert isinstance(result["outer"], FrozenDict)
    assert result["outer"]["inner"] == 1


def test_freeze_dict_recursively_freezes_set_values():
    """Set values inside a dict should be recursively frozen into frozensets."""
    result = freeze({"items": {1, 2, 3}})
    assert isinstance(result["items"], frozenset)
    assert result["items"] == frozenset({1, 2, 3})


def test_freeze_ordereddict_returns_frozendict():
    """An OrderedDict should also be frozen to a FrozenDict (since it is a dict subclass)."""
    data = OrderedDict([("a", 1), ("b", 2)])
    result = freeze(data)
    assert isinstance(result, FrozenDict)
    assert dict(result) == {"a": 1, "b": 2}


def test_freeze_list_returns_tuple():
    """A list should be transformed into a tuple (traced from the list branch)."""
    result = freeze([1, 2, 3])
    assert isinstance(result, tuple)


def test_freeze_list_preserves_elements_in_order():
    """Freezing a list should keep the elements in the same order."""
    result = freeze([1, 2, 3])
    assert result == (1, 2, 3)


def test_freeze_list_returns_new_object_not_original():
    """Freezing a list should return a new tuple, not the original list object."""
    original = [1, 2, 3]
    result = freeze(original)
    assert result is not original


def test_freeze_list_remains_indexable():
    """A list frozen into a tuple should still support indexing."""
    result = freeze([10, 20, 30])
    assert result[0] == 10
    assert result[2] == 30


def test_freeze_list_recursively_freezes_dict_elements():
    """Dict elements inside a list should also be frozen."""
    result = freeze([{"a": 1}])
    assert isinstance(result, tuple)
    assert isinstance(result[0], FrozenDict)


def test_freeze_list_recursively_freezes_nested_lists():
    """Nested lists inside a list should be recursively frozen to tuples."""
    result = freeze([[1, 2], [3, 4]])
    assert isinstance(result, tuple)
    assert all(isinstance(item, tuple) for item in result)
    assert result == ((1, 2), (3, 4))


def test_freeze_list_recursively_freezes_set_elements():
    """Set elements inside a list should be frozen to frozensets."""
    result = freeze([{1, 2}])
    assert isinstance(result[0], frozenset)


def test_freeze_set_returns_frozenset():
    """A set should be transformed into a frozenset (traced from the set branch)."""
    result = freeze({1, 2, 3})
    assert isinstance(result, frozenset)


def test_freeze_set_preserves_elements():
    """Freezing a set should preserve its elements."""
    result = freeze({1, 2, 3})
    assert result == frozenset({1, 2, 3})


def test_freeze_set_returns_new_object_not_original():
    """Freezing a set should return a new frozenset, not the original set object."""
    original = {1, 2, 3}
    result = freeze(original)
    assert result is not original


def test_freeze_int_is_returned_unchanged():
    """An int is already immutable and should be returned as-is via the else branch."""
    result = freeze(42)
    assert result == 42
    assert isinstance(result, int)


def test_freeze_string_is_returned_unchanged():
    """A string is already immutable and should be returned as-is via the else branch."""
    result = freeze("hello")
    assert result == "hello"
    assert isinstance(result, str)


def test_freeze_none_is_returned_unchanged():
    """None should be returned as-is via the else branch."""
    assert freeze(None) is None


def test_freeze_float_is_returned_unchanged():
    """A float is already immutable and should be returned as-is via the else branch."""
    result = freeze(3.14)
    assert result == 3.14
    assert isinstance(result, float)


def test_freeze_tuple_is_returned_unchanged():
    """A tuple is not a list, so it should hit the else branch and be returned as-is."""
    original = (1, 2, 3)
    result = freeze(original)
    assert result == (1, 2, 3)


def test_freeze_frozenset_is_returned_unchanged():
    """A frozenset is not a set, so it should hit the else branch and be returned as-is."""
    original = frozenset({1, 2})
    result = freeze(original)
    assert result is original


def test_freeze_empty_dict_returns_empty_frozendict():
    """An empty dict should be frozen to an empty FrozenDict."""
    result = freeze({})
    assert isinstance(result, FrozenDict)
    assert dict(result) == {}


def test_freeze_empty_list_returns_empty_tuple():
    """An empty list should be frozen to an empty tuple."""
    result = freeze([])
    assert isinstance(result, tuple)
    assert result == ()


def test_freeze_empty_set_returns_empty_frozenset():
    """An empty set should be frozen to an empty frozenset."""
    result = freeze(set())
    assert isinstance(result, frozenset)
    assert result == frozenset()


def test_frozen_tuple_does_not_support_item_assignment():
    """A list frozen into a tuple should not be mutable via item assignment."""
    result = freeze([1, 2, 3])
    with pytest.raises(TypeError):
        result[0] = 99


def test_frozen_frozenset_does_not_support_add():
    """A set frozen into a frozenset should not support add (frozensets are immutable)."""
    result = freeze({1, 2, 3})
    with pytest.raises(AttributeError):
        result.add(99)


def test_frozen_dict_is_hashable():
    """A frozen dict should be hashable (one of the stated intents of freezing)."""
    result = freeze({"a": 1})
    # Calling hash should not raise
    hash_value = hash(result)
    # And the hash should be consistent across calls
    assert hash(result) == hash_value


def test_frozen_tuple_is_hashable():
    """A tuple (result of freezing a list) should be hashable."""
    result = freeze([1, 2, 3])
    hash_value = hash(result)
    assert hash(result) == hash_value


def test_frozen_frozenset_is_hashable():
    """A frozenset (result of freezing a set) should be hashable."""
    result = freeze({1, 2, 3})
    hash_value = hash(result)
    assert hash(result) == hash_value


def test_frozen_dict_can_be_used_as_dict_key():
    """A frozen dict should be usable as a dict key because it is hashable."""
    frozen = freeze({"a": 1})
    container = {frozen: "stored_value"}
    assert container[frozen] == "stored_value"


def test_frozen_objects_can_be_combined_in_a_set():
    """Frozen immutable objects should be combinable in a set, validating hashability."""
    frozen_dict = freeze({"a": 1})
    frozen_list = freeze([1, 2, 3])
    frozen_set = freeze({1, 2, 3})
    container = {frozen_dict, frozen_list, frozen_set}
    assert len(container) == 3


def test_freeze_complex_nested_structure_fully_freezes():
    """A complex nested structure should be fully frozen with the appropriate types at every level."""
    data = {
        "list_value": [1, 2, {"nested_key": "nested_value"}],
        "dict_value": {"inner_list": [3, 4]},
        "set_value": {5, 6},
    }
    result = freeze(data)

    assert isinstance(result, FrozenDict)
    assert isinstance(result["list_value"], tuple)
    assert isinstance(result["list_value"][2], FrozenDict)
    assert result["list_value"][2]["nested_key"] == "nested_value"
    assert isinstance(result["dict_value"], FrozenDict)
    assert isinstance(result["dict_value"]["inner_list"], tuple)
    assert result["dict_value"]["inner_list"] == (3, 4)
    assert isinstance(result["set_value"], frozenset)


def test_freeze_deeply_nested_dicts_all_become_frozendicts():
    """Multiple levels of nested dicts should all become FrozenDict instances."""
    data = {"a": {"b": {"c": {"d": 1}}}}
    result = freeze(data)

    assert isinstance(result, FrozenDict)
    assert isinstance(result["a"], FrozenDict)
    assert isinstance(result["a"]["b"], FrozenDict)
    assert isinstance(result["a"]["b"]["c"], FrozenDict)
    assert result["a"]["b"]["c"]["d"] == 1


def test_freeze_deeply_nested_lists_all_become_tuples():
    """Multiple levels of nested lists should all become tuples."""
    data = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
    result = freeze(data)

    assert isinstance(result, tuple)
    assert isinstance(result[0], tuple)
    assert isinstance(result[0][0], tuple)
    assert result[0][0] == (1, 2)


def test_freeze_produces_equal_objects_for_equal_inputs():
    """Two freeze() calls on equal inputs should produce equal results."""
    assert freeze({"a": 1}) == freeze({"a": 1})
    assert freeze([1, 2, 3]) == freeze([1, 2, 3])
    assert freeze({1, 2, 3}) == freeze({1, 2, 3})
