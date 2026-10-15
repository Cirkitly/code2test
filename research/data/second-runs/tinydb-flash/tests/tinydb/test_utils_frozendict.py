import pytest
from tinydb.utils import FrozenDict

@pytest.fixture
def frozen_dict():
    """A small FrozenDict shared by the immutability tests."""
    return FrozenDict({'a': 1, 'b': 2})

def test_frozendict_is_a_dict_subclass_and_equals_plain_dict():
    frozen = FrozenDict({'a': 1, 'b': 2})

    assert isinstance(frozen, dict)
    assert frozen == {'a': 1, 'b': 2}
    assert {'a': 1, 'b': 2} == frozen

def test_construct_from_keyword_arguments():
    assert FrozenDict(a=1, b=2) == {'a': 1, 'b': 2}

def test_construct_from_mapping_and_iterable_of_pairs():
    assert FrozenDict({'a': 1}) == {'a': 1}
    assert FrozenDict([('a', 1), ('b', 2)]) == {'a': 1, 'b': 2}

def test_construct_from_another_frozendict():
    original = FrozenDict({'a': 1, 'b': 2})
    copy = FrozenDict(original)

    assert isinstance(copy, FrozenDict)
    assert copy == {'a': 1, 'b': 2}

def test_empty_frozendict_is_empty_falsy_and_hashable():
    frozen = FrozenDict()

    assert len(frozen) == 0
    assert frozen == {}
    assert bool(frozen) is False
    assert hash(frozen) == hash(())

def test_non_empty_frozendict_is_truthy():
    assert bool(FrozenDict({'a': 1})) is True

def test_read_only_operations_work(frozen_dict):
    assert len(frozen_dict) == 2
    assert 'a' in frozen_dict
    assert 'missing' not in frozen_dict
    assert frozen_dict['a'] == 1
    assert frozen_dict['b'] == 2
    assert frozen_dict.get('a') == 1
    assert frozen_dict.get('missing') is None
    assert frozen_dict.get('missing', 'default') == 'default'
    assert sorted(frozen_dict.keys()) == ['a', 'b']
    assert sorted(frozen_dict.values()) == [1, 2]
    assert sorted(frozen_dict.items()) == [('a', 1), ('b', 2)]
    assert list(iter(frozen_dict)) == ['a', 'b']

def test_lookup_of_missing_key_raises_keyerror(frozen_dict):
    with pytest.raises(KeyError):
        frozen_dict['missing']

def test_hash_equals_hash_of_sorted_items_tuple():
    frozen = FrozenDict({'a': 1, 'b': 2})

    assert isinstance(hash(frozen), int)
    assert hash(frozen) == hash((('a', 1), ('b', 2)))

def test_hash_with_integer_keys():
    assert hash(FrozenDict({1: 'one'})) == hash(((1, 'one'),))

def test_hash_does_not_depend_on_insertion_order():
    first = FrozenDict({'a': 1, 'b': 2})
    second = FrozenDict({'b': 2, 'a': 1})

    assert hash(first) == hash(second)

def test_frozendict_can_be_used_as_a_dict_key_and_in_a_set():
    container = {FrozenDict({'a': 1}): 'value'}

    assert container[FrozenDict({'a': 1})] == 'value'
    assert FrozenDict({'a': 1}) in container
    assert FrozenDict({'a': 2}) not in container

def test_hash_with_nested_frozendict_value():
    frozen = FrozenDict({'a': FrozenDict({'b': 1})})

    assert hash(frozen) == hash((('a', FrozenDict({'b': 1})),))

def test_hash_fails_when_a_value_is_unhashable():
    with pytest.raises(TypeError, match='unhashable'):
        hash(FrozenDict({'a': [1, 2]}))

def test_hash_fails_for_keys_that_cannot_be_sorted():
    frozen = FrozenDict({1: 'one', 'one': 1})

    with pytest.raises(TypeError):
        hash(frozen)

def test_setitem_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict['c'] = 3

def test_delitem_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        del frozen_dict['a']

def test_clear_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.clear()

def test_setdefault_raises_typeerror_for_missing_key(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.setdefault('new', 1)

def test_setdefault_raises_typeerror_even_for_existing_key(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.setdefault('a', 99)

def test_popitem_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.popitem()

def test_popitem_raises_typeerror_on_empty_frozendict():
    with pytest.raises(TypeError, match='object is immutable'):
        FrozenDict().popitem()

def test_update_with_mapping_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.update({'c': 3})

def test_update_with_kwargs_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.update(c=3)

def test_pop_existing_key_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.pop('a')

def test_pop_missing_key_with_default_raises_typeerror(frozen_dict):
    with pytest.raises(TypeError, match='object is immutable'):
        frozen_dict.pop('missing', None)

def test_contents_survive_all_failed_mutations(frozen_dict):
    attempts = [
        lambda d: d.__setitem__('c', 3),
        lambda d: d.__delitem__('a'),
        lambda d: d.clear(),
        lambda d: d.setdefault('c', 3),
        lambda d: d.setdefault('a', 3),
        lambda d: d.popitem(),
        lambda d: d.update({'c': 3}),
        lambda d: d.update(c=3),
        lambda d: d.pop('a'),
        lambda d: d.pop('missing', 1),
    ]

    for attempt in attempts:
        with pytest.raises(TypeError):
            attempt(frozen_dict)
        assert frozen_dict == {'a': 1, 'b': 2}
        assert len(frozen_dict) == 2

def test_frozendict_can_be_unpacked_into_a_new_dict(frozen_dict):
    assert {**frozen_dict} == {'a': 1, 'b': 2}
    assert dict(**frozen_dict) == {'a': 1, 'b': 2}

def test_copy_returns_a_mutable_plain_dict(frozen_dict):
    copied = frozen_dict.copy()

    assert copied == {'a': 1, 'b': 2}
    assert not isinstance(copied, FrozenDict)

    copied['c'] = 3
    assert copied == {'a': 1, 'b': 2, 'c': 3}
    assert frozen_dict == {'a': 1, 'b': 2}

def test_iteration_preserves_insertion_order():
    frozen = FrozenDict([('b', 1), ('a', 2)])

    assert list(frozen) == ['b', 'a']
    assert list(frozen.keys()) == ['b', 'a']
    assert list(frozen.items()) == [('b', 1), ('a', 2)]

def test_repr_reflects_the_frozen_contents(frozen_dict):
    text = repr(frozen_dict)

    # FrozenDict is a plain dict subclass, so repr matches dict's repr
    assert text == repr({'a': 1, 'b': 2})
    assert 'a' in text and '1' in text
    assert 'b' in text and '2' in text
