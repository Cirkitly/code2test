import pytest
from collections import OrderedDict
from tinydb.utils import freeze, FrozenDict

def test_freeze_dict_returns_frozendict():
    result = freeze({'a': 1, 'b': 2})

    assert isinstance(result, FrozenDict)
    assert dict(result) == {'a': 1, 'b': 2}
    assert len(result) == 2

def test_freeze_dict_is_immutable():
    frozen = freeze({'a': 1})

    with pytest.raises(TypeError):
        frozen['a'] = 2

    with pytest.raises(TypeError):
        frozen.update({'a': 2})

    with pytest.raises(TypeError):
        frozen.pop('a')

def test_freeze_list_returns_tuple():
    result = freeze(['a', 'b', 1])

    assert isinstance(result, tuple)
    assert result == ('a', 'b', 1)
    assert len(result) == 3

def test_freeze_set_returns_frozenset():
    result = freeze({1, 2, 3})

    assert isinstance(result, frozenset)
    assert result == frozenset({1, 2, 3})
    assert len(result) == 3

def test_freeze_returns_non_container_objects_unchanged():
    sentinel = object()

    assert freeze(42) == 42
    assert freeze('text') == 'text'
    assert freeze(None) is None
    assert freeze(True) is True
    assert freeze(sentinel) is sentinel

def test_freeze_nested_dict_values_are_frozen():
    result = freeze({'a': {'b': [1, {'c': 2}]}})

    assert isinstance(result, FrozenDict)
    assert isinstance(result['a'], FrozenDict)
    assert isinstance(result['a']['b'], tuple)
    assert result['a']['b'][0] == 1
    assert isinstance(result['a']['b'][1], FrozenDict)
    assert result == {'a': {'b': (1, {'c': 2})}}

def test_freeze_nested_list_elements_are_frozen():
    result = freeze([{'a': 1}, [2, 3]])

    assert isinstance(result, tuple)
    assert isinstance(result[0], FrozenDict)
    assert result[0] == {'a': 1}
    assert result[1] == (2, 3)

def test_freeze_deeply_nested_structure_matches_original_contents():
    original = {'list': [1, 2], 'dict': {'set': {1, 2}}, 'plain': 'value'}
    result = freeze(original)

    assert result == {'list': (1, 2), 'dict': {'set': {1, 2}}, 'plain': 'value'}
    assert result['dict']['set'] == frozenset({1, 2})

def test_freeze_nested_dict_keys_are_not_converted():
    key = ('key', 'tuple')
    result = freeze({key: 'value'})

    assert list(result.keys()) == [key]
    assert result[key] == 'value'

def test_freeze_dict_result_is_hashable():
    frozen = freeze({'a': 1, 'b': [2, 3]})

    assert isinstance(hash(frozen), int)
    assert frozen == freeze({'a': 1, 'b': [2, 3]})
    assert hash(frozen) == hash(freeze({'a': 1, 'b': [2, 3]}))
    assert len({frozen, freeze({'a': 1, 'b': [2, 3]})}) == 1

def test_freeze_nested_frozen_structure_is_hashable():
    frozen = freeze({'a': {'b': [1, 2]}, 'c': {3, 4}})

    assert isinstance(hash(frozen), int)
    assert len({frozen, frozen}) == 1

def test_freeze_mutating_the_original_list_does_not_affect_frozen_result():
    original = [1, 2]
    frozen = freeze(original)

    original.append(3)

    assert frozen == (1, 2)
    assert len(frozen) == 2

def test_freeze_mutating_the_original_dict_does_not_affect_frozen_result():
    original = {'a': 1}
    frozen = freeze(original)

    original['b'] = 2
    del original['a']

    assert dict(frozen) == {'a': 1}
    assert len(frozen) == 1

def test_freeze_empty_containers():
    assert isinstance(freeze({}), FrozenDict)
    assert len(freeze({})) == 0

    assert freeze([]) == ()
    assert isinstance(freeze([]), tuple)

    assert freeze(set()) == frozenset()
    assert isinstance(freeze(set()), frozenset)

def test_freeze_string_is_not_treated_as_a_list():
    result = freeze('abc')

    assert isinstance(result, str)
    assert result == 'abc'

def test_freeze_is_idempotent():
    once = freeze({'a': [1, 2], 'b': {3, 4}})
    twice = freeze(once)

    assert once == twice
    assert isinstance(twice, FrozenDict)
    assert isinstance(twice['a'], tuple)
    assert hash(once) == hash(twice)

def test_freeze_set_elements_are_returned_unchanged():
    element = (1, 2)
    result = freeze({element})

    assert isinstance(result, frozenset)
    assert element in result

def test_freeze_list_of_tuples_keeps_inner_tuples():
    inner_list = [2]
    result = freeze([(1, inner_list)])

    assert result == ((1, [2]),)
    assert result[0][1] is inner_list

def test_freeze_subclasses_of_dict_and_list_are_converted_to_base_types():
    ordered = OrderedDict([('b', 1), ('a', 2)])
    result = freeze(ordered)

    assert isinstance(result, FrozenDict)
    assert list(result.keys()) == ['b', 'a']

    class MyList(list):
        pass

    assert freeze(MyList([1, 2])) == (1, 2)
    assert isinstance(freeze(MyList([1, 2])), tuple)

def test_freeze_output_can_be_used_as_a_dictionary_key():
    cache = {freeze({'b': [1, 2]}): 'value'}

    assert cache[freeze({'b': [1, 2]})] == 'value'
    assert cache[freeze({'b': [1, 2]})] == 'value'
    assert len(cache) == 1

class Unhashable:
    __hash__ = None


def test_freeze_raises_typeerror_for_unhashable_value_inside_frozen_dict():
    frozen = freeze({'key': Unhashable()})

    assert isinstance(frozen, FrozenDict)
    with pytest.raises(TypeError):
        hash(frozen)

def test_freeze_raises_typeerror_when_setting_attribute_on_frozen_dict_item_value():
    frozen = freeze({'outer': {'inner': 1}})

    with pytest.raises(TypeError):
        frozen['outer']['inner'] = 2

def test_freeze_del_item_on_frozen_dict_raises_typeerror():
    frozen = freeze({'a': 1, 'b': 2})

    with pytest.raises(TypeError):
        del frozen['a']

    assert dict(frozen) == {'a': 1, 'b': 2}

def test_freeze_supports_the_mapping_read_only_interface():
    frozen = freeze({'a': 1, 'b': 2})

    assert len(frozen) == 2
    assert 'a' in frozen
    assert 'missing' not in frozen
    assert sorted(frozen.keys()) == ['a', 'b']
    assert sorted(frozen.values()) == [1, 2]
    assert sorted(frozen.items()) == [('a', 1), ('b', 2)]
    assert frozen.get('missing') is None
    assert frozen.get('a') == 1
