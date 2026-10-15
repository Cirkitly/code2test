import pytest
from tinydb.utils import FrozenDict, freeze

@pytest.fixture
def frozen_dict():
    """A FrozenDict holding two entries, used by the read-only tests."""
    return FrozenDict({'a': 1, 'b': 2})

def test_frozendict_is_a_dict_subclass():
    assert issubclass(FrozenDict, dict)
    assert isinstance(FrozenDict(), dict)
    # Not empty -> truthy; empty -> falsy, just like a plain dict
    assert FrozenDict({'a': 1}) == {'a': 1}
    assert FrozenDict({'a': 1})
    assert not FrozenDict()


def test_frozendict_can_be_built_from_dict_kwargs_and_pairs():
    from_mapping = FrozenDict({'a': 1, 'b': 2})
    from_kwargs = FrozenDict(a=1, b=2)
    from_pairs = FrozenDict([('a', 1), ('b', 2)])

    for candidate in (from_mapping, from_kwargs, from_pairs):
        assert candidate == {'a': 1, 'b': 2}
        assert len(candidate) == 2

def test_frozendict_supports_read_only_mapping_access(frozen_dict):
    assert len(frozen_dict) == 2
    assert 'a' in frozen_dict
    assert 'missing' not in frozen_dict
    assert frozen_dict['a'] == 1
    assert frozen_dict.get('a') == 1
    assert frozen_dict.get('missing') is None
    assert list(frozen_dict.keys()) == ['a', 'b']
    assert list(frozen_dict.values()) == [1, 2]
    assert list(frozen_dict.items()) == [('a', 1), ('b', 2)]
    assert sorted(frozen_dict) == ['a', 'b']


def test_frozendict_missing_key_raises_key_error(frozen_dict):
    with pytest.raises(KeyError):
        frozen_dict['missing']

def test_frozendict_hash_matches_sorted_items_tuple():
    # Source: hash(tuple(sorted(self.items())))
    assert hash(FrozenDict()) == hash(())
    assert hash(FrozenDict({'a': 1})) == hash((('a', 1),))
    assert hash(FrozenDict({'b': 2, 'a': 1})) == hash((('a', 1), ('b', 2)))


def test_frozendict_is_hashable_and_hash_is_stable():
    frozen = FrozenDict({'a': 1, 'b': 2})
    assert isinstance(hash(frozen), int)
    assert hash(frozen) == hash(frozen)


def test_frozendict_hash_is_independent_of_insertion_order():
    assert FrozenDict([('b', 2), ('a', 1)]) == FrozenDict([('a', 1), ('b', 2)])
    assert hash(FrozenDict([('b', 2), ('a', 1)])) == hash(FrozenDict([('a', 1), ('b', 2)]))
    assert hash(FrozenDict({2: 'b', 1: 'a'})) == hash(FrozenDict({1: 'a', 2: 'b'}))

def test_frozendict_can_be_used_as_dict_key():
    mapping = {FrozenDict({'a': 1}): 'value'}
    assert mapping[FrozenDict({'a': 1})] == 'value'
    with pytest.raises(KeyError):
        mapping[FrozenDict({'a': 2})]


def test_frozendict_can_be_added_to_a_set():
    members = {FrozenDict({'a': 1}), FrozenDict({'a': 1})}
    assert len(members) == 1
    assert FrozenDict({'a': 1}) in members


def test_frozendict_equals_plain_dict_with_same_items(frozen_dict):
    assert frozen_dict == {'a': 1, 'b': 2}
    assert {'a': 1, 'b': 2} == frozen_dict
    assert frozen_dict != {'a': 1}
    assert frozen_dict != FrozenDict({'a': 1, 'b': 3})

def _set_item(fd):
    fd['a'] = 99


def _del_item(fd):
    del fd['a']


def _update_with_mapping(fd):
    fd.update({'a': 99})


def _update_with_kwargs(fd):
    fd.update(a=99)


def _update_without_args(fd):
    fd.update()


def _pop_existing_key(fd):
    fd.pop('a')


def _pop_with_default_for_missing_key(fd):
    fd.pop('missing', None)


def _popitem(fd):
    fd.popitem()


def _clear(fd):
    fd.clear()


def _setdefault_missing_key(fd):
    fd.setdefault('missing', 99)


def _setdefault_existing_key(fd):
    fd.setdefault('a', 99)


MUTATING_OPERATIONS = [
    pytest.param(_set_item, id='setitem'),
    pytest.param(_del_item, id='delitem'),
    pytest.param(_update_with_mapping, id='update_with_mapping'),
    pytest.param(_update_with_kwargs, id='update_with_kwargs'),
    pytest.param(_update_without_args, id='update_without_args'),
    pytest.param(_pop_existing_key, id='pop_existing_key'),
    pytest.param(_pop_with_default_for_missing_key, id='pop_missing_key_with_default'),
    pytest.param(_popitem, id='popitem'),
    pytest.param(_clear, id='clear'),
    pytest.param(_setdefault_missing_key, id='setdefault_missing_key'),
    pytest.param(_setdefault_existing_key, id='setdefault_existing_key'),
]


@pytest.mark.parametrize('operation', MUTATING_OPERATIONS)
def test_frozendict_mutating_operations_raise_type_error(operation):
    frozen = FrozenDict({'a': 1, 'b': 2})

    with pytest.raises(TypeError) as exc_info:
        operation(frozen)

    assert 'object is immutable' in str(exc_info.value)


@pytest.mark.parametrize('operation', MUTATING_OPERATIONS)
def test_frozendict_content_is_unchanged_after_failed_mutation(operation):
    frozen = FrozenDict({'a': 1, 'b': 2})

    with pytest.raises(TypeError):
        operation(frozen)

    assert frozen == {'a': 1, 'b': 2}
    assert len(frozen) == 2
    assert hash(frozen) == hash((('a', 1), ('b', 2)))

def test_frozendict_hash_raises_for_keys_that_cannot_be_ordered():
    # sorted(self.items()) compares the mixed-type keys and fails
    with pytest.raises(TypeError):
        hash(FrozenDict({'a': 1, 1: 2}))


def test_frozendict_with_unhashable_values_can_be_created_but_not_hashed():
    frozen = FrozenDict({'a': [1, 2]})
    assert frozen == {'a': [1, 2]}

    with pytest.raises(TypeError):
        hash(frozen)


def test_nested_plain_dict_value_prevents_hashing():
    # A nested plain dict is not hashable, so hashing the FrozenDict fails
    with pytest.raises(TypeError):
        hash(FrozenDict({'a': {'b': 1}}))

def test_frozendict_can_be_copied_into_a_mutable_plain_dict(frozen_dict):
    plain = dict(frozen_dict)

    assert isinstance(plain, dict)
    assert plain == {'a': 1, 'b': 2}
    assert plain is not frozen_dict

    # The copy is a regular, mutable dict
    plain['c'] = 3
    assert plain == {'a': 1, 'b': 2, 'c': 3}
    assert frozen_dict == {'a': 1, 'b': 2}

def test_freeze_turns_dicts_into_frozendicts():
    frozen = freeze({'a': 1, 'b': 2})

    assert isinstance(frozen, FrozenDict)
    assert frozen == {'a': 1, 'b': 2}
    assert hash(frozen) == hash((('a', 1), ('b', 2)))


def test_freeze_result_is_immutable_and_supports_nested_dicts():
    frozen = freeze({'a': 1, 'nested': {'b': 2}})

    assert frozen == {'a': 1, 'nested': {'b': 2}}
    # Nested dicts are frozen too, which is what makes the whole thing hashable
    assert isinstance(hash(frozen), int)

    with pytest.raises(TypeError):
        frozen['a'] = 99
