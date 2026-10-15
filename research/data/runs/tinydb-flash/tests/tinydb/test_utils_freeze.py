from collections import OrderedDict
import pytest
from tinydb.utils import freeze, FrozenDict

@pytest.fixture
def nested_mutable_structure():
    """A nested, fully mutable document used across several freeze tests.

    Contains all container types freeze() is expected to handle: a dict,
    a list of strings, a nested dict containing a list, and a set of ints.
    """
    return {
        'name': 'tinydb',
        'version': 4,
        'tags': ['database', 'nosql'],
        'options': {'cache': True, 'indexes': [1, 2]},
        'levels': {1, 2, 3},
    }


def test_freeze_returns_frozendict_for_dict_input():
    frozen = freeze({'a': 1, 'b': 2})

    assert isinstance(frozen, FrozenDict)
    assert frozen == {'a': 1, 'b': 2}
    assert len(frozen) == 2


def test_freeze_keeps_dict_key_lookup_working():
    frozen = freeze({'a': 1, 'b': 2})

    assert 'a' in frozen
    assert 'missing' not in frozen
    assert frozen['b'] == 2
    assert list(frozen.keys()) == ['a', 'b']
    assert list(frozen.values()) == [1, 2]

def test_freeze_dict_is_immutable_and_rejects_writes():
    frozen = freeze({'a': 1})

    with pytest.raises(TypeError):
        frozen['b'] = 2

    with pytest.raises(TypeError):
        frozen.update({'b': 2})

    with pytest.raises(TypeError):
        frozen.pop('a')

    # The original contents are untouched after the failed mutations
    assert frozen == {'a': 1}

def test_freeze_makes_unhashable_dict_hashable():
    original = {'a': 1}

    with pytest.raises(TypeError):
        hash(original)

    frozen = freeze(original)

    # Must not raise and must be usable as a dict key / in a set
    assert isinstance(hash(frozen), int)
    assert {frozen: 'value'}[freeze({'a': 1})] == 'value'

def test_freeze_transforms_list_into_tuple():
    frozen = freeze([1, 2, 3])

    assert isinstance(frozen, tuple)
    assert frozen == (1, 2, 3)
    assert isinstance(hash(frozen), int)

def test_freeze_transforms_set_into_frozenset():
    frozen = freeze({1, 2, 3})

    assert isinstance(frozen, frozenset)
    assert frozen == frozenset({1, 2, 3})
    assert isinstance(hash(frozen), int)

def test_freeze_recurses_into_nested_containers():
    frozen = freeze({'key': [{'inner': [1, {'deep': {2, 3}}]}]})

    assert isinstance(frozen, FrozenDict)
    outer_value = frozen['key']
    assert isinstance(outer_value, tuple)

    inner_dict = outer_value[0]
    assert isinstance(inner_dict, FrozenDict)

    inner_list = inner_dict['inner']
    assert isinstance(inner_list, tuple)
    assert inner_list[0] == 1

    innermost = inner_list[1]['deep']
    assert isinstance(innermost, frozenset)
    assert innermost == frozenset({2, 3})

    # The deeply frozen structure as a whole is hashable
    assert isinstance(hash(frozen), int)


def test_freeze_nested_structure_fixture_is_fully_immutable(nested_mutable_structure):
    frozen = freeze(nested_mutable_structure)

    assert isinstance(frozen, FrozenDict)
    assert frozen['name'] == 'tinydb'
    assert frozen['version'] == 4
    assert frozen['tags'] == ('database', 'nosql')
    assert isinstance(frozen['options'], FrozenDict)
    assert frozen['options']['indexes'] == (1, 2)
    assert frozen['levels'] == frozenset({1, 2, 3})
    assert isinstance(hash(frozen), int)

    with pytest.raises(TypeError):
        frozen['name'] = 'other'


def test_freeze_returns_plain_objects_unchanged():
    value = 42
    text = 'tinydb'

    assert freeze(value) is value
    assert freeze(text) is text
    assert freeze(None) is None
    assert freeze(True) is True
    assert freeze(3.5) == 3.5

class Document:
    def __init__(self, name):
        self.name = name


def test_freeze_passes_custom_objects_through_unchanged():
    document = Document('test')

    assert freeze(document) is document


def test_freeze_passes_tuples_through_unchanged():
    value = (1, 2, 3)

    assert freeze(value) is value

def test_freeze_does_not_freeze_containers_inside_tuples():
    frozen = freeze(([1, 2], {'a': 1}))

    assert isinstance(frozen, tuple)
    # The inner list is still a mutable list, it was not frozen
    assert isinstance(frozen[0], list)
    assert isinstance(frozen[1], dict)

    with pytest.raises(TypeError):
        hash(frozen)

def test_freeze_handles_empty_containers():
    frozen_dict = freeze({})
    frozen_list = freeze([])
    frozen_set = freeze(set())

    assert isinstance(frozen_dict, FrozenDict)
    assert len(frozen_dict) == 0
    assert isinstance(hash(frozen_dict), int)

    assert frozen_list == ()
    assert isinstance(frozen_list, tuple)

    assert frozen_set == frozenset()
    assert isinstance(frozen_set, frozenset)


def test_freeze_handles_dict_subclasses():
    ordered = OrderedDict([('b', 1), ('a', 2)])

    frozen = freeze(ordered)

    assert isinstance(frozen, FrozenDict)
    assert frozen == {'b': 1, 'a': 2}
    assert list(frozen.keys()) == ['b', 'a']


def test_freeze_does_not_mutate_the_original_object():
    original_dict = {'tags': ['a', 'b'], 'levels': {1, 2}}

    freeze(original_dict)

    assert isinstance(original_dict['tags'], list)
    assert original_dict['tags'] == ['a', 'b']
    assert isinstance(original_dict['levels'], set)
    assert original_dict == {'tags': ['a', 'b'], 'levels': {1, 2}}

def test_freeze_is_idempotent():
    original = {'tags': ['a', 'b'], 'levels': {1, 2}, 'meta': {'x': [1]}}

    once = freeze(original)
    twice = freeze(once)

    assert twice == once
    assert isinstance(twice, FrozenDict)
    assert twice['tags'] == ('a', 'b')
    assert twice['levels'] == frozenset({1, 2})
    assert isinstance(hash(twice), int)


def test_freeze_hash_is_stable_for_equal_structures():
    first = freeze({'tags': ['a', 'b'], 'levels': {1, 2}})
    second = freeze({'tags': ['a', 'b'], 'levels': {1, 2}})

    assert first == second
    assert hash(first) == hash(second)
    assert len({first, second}) == 1

class Unhashable:
    __hash__ = None

    def __init__(self, value):
        self.value = value


def test_freeze_raises_type_error_for_unhashable_custom_values():
    frozen = freeze({'payload': Unhashable('x')})

    # The dict itself was frozen into a FrozenDict, but the value is untouched
    assert isinstance(frozen, FrozenDict)
    assert isinstance(frozen['payload'], Unhashable)

    with pytest.raises(TypeError):
        hash(frozen)

