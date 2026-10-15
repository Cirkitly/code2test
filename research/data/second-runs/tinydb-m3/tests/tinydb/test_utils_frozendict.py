import pytest
from tinydb.utils import FrozenDict

@pytest.fixture
def sample_frozendict():
    """Provide a reusable FrozenDict with deterministic contents."""
    return FrozenDict({'a': 1, 'b': 2, 'c': 3})

def test_create_frozendict_from_dict():
    """FrozenDict can be created from a regular dict and preserves its items."""
    fd = FrozenDict({'a': 1, 'b': 2})
    assert fd['a'] == 1
    assert fd['b'] == 2
    assert len(fd) == 2

def test_create_empty_frozendict():
    """An empty FrozenDict can be created with no arguments."""
    fd = FrozenDict()
    assert len(fd) == 0
    assert dict(fd) == {}

def test_frozendict_inherits_from_dict():
    """FrozenDict is a subclass of dict (is-a dict)."""
    fd = FrozenDict({'a': 1})
    assert isinstance(fd, dict)

def test_frozendict_get_existing_key(sample_frozendict):
    """dict.get returns the stored value for an existing key."""
    assert sample_frozendict.get('a') == 1
    assert sample_frozendict.get('b') == 2

def test_frozendict_get_missing_returns_default(sample_frozendict):
    """dict.get returns the provided default when the key is absent."""
    assert sample_frozendict.get('missing') is None
    assert sample_frozendict.get('missing', 'fallback') == 'fallback'

def test_frozendict_keys_values_items(sample_frozendict):
    """keys(), values(), and items() work correctly on a FrozenDict."""
    assert sorted(sample_frozendict.keys()) == ['a', 'b', 'c']
    assert sorted(sample_frozendict.values()) == [1, 2, 3]
    assert sorted(sample_frozendict.items()) == [('a', 1), ('b', 2), ('c', 3)]

def test_frozendict_membership_test(sample_frozendict):
    """The 'in' operator works on a FrozenDict."""
    assert 'a' in sample_frozendict
    assert 'missing' not in sample_frozendict

def test_frozendict_iteration_yields_keys(sample_frozendict):
    """Iterating over a FrozenDict yields its keys."""
    assert sorted(sample_frozendict) == ['a', 'b', 'c']

def test_frozendict_is_hashable(sample_frozendict):
    """FrozenDict implements __hash__ and returns an int (which regular dicts cannot)."""
    assert isinstance(hash(sample_frozendict), int)

def test_empty_frozendict_is_hashable():
    """An empty FrozenDict is still hashable (edge case)."""
    fd = FrozenDict()
    assert isinstance(hash(fd), int)

def test_frozendict_hash_is_stable(sample_frozendict):
    """The hash of a FrozenDict is stable across multiple calls."""
    assert hash(sample_frozendict) == hash(sample_frozendict)
    assert hash(sample_frozendict) == hash(sample_frozendict)

def test_frozendict_equal_content_has_equal_hash():
    """Two FrozenDicts with the same content are equal and have equal hashes."""
    fd1 = FrozenDict({'a': 1, 'b': 2})
    fd2 = FrozenDict({'b': 2, 'a': 1})
    assert fd1 == fd2
    assert hash(fd1) == hash(fd2)

def test_frozendict_usable_in_set():
    """FrozenDicts can be added to a set and equal ones deduplicate."""
    fd1 = FrozenDict({'a': 1, 'b': 2})
    fd2 = FrozenDict({'b': 2, 'a': 1})
    s = {fd1, fd2}
    assert len(s) == 1

def test_frozendict_usable_as_dict_key():
    """A FrozenDict can be used as a dict key."""
    d = {FrozenDict({'a': 1}): 'value'}
    assert d[FrozenDict({'a': 1})] == 'value'

def test_setitem_raises_typeerror(sample_frozendict):
    """Assigning to a key raises TypeError due to immutability."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict['new'] = 99

def test_delitem_raises_typeerror(sample_frozendict):
    """Deleting a key raises TypeError due to immutability."""
    with pytest.raises(TypeError, match='object is immutable'):
        del sample_frozendict['a']

def test_clear_raises_typeerror(sample_frozendict):
    """FrozenDict.clear raises TypeError due to immutability."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict.clear()

def test_setdefault_raises_typeerror(sample_frozendict):
    """FrozenDict.setdefault raises TypeError due to immutability."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict.setdefault('a', 99)

def test_popitem_raises_typeerror(sample_frozendict):
    """FrozenDict.popitem raises TypeError due to immutability."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict.popitem()

def test_update_with_mapping_raises_typeerror(sample_frozendict):
    """FrozenDict.update with a mapping raises TypeError due to immutability."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict.update({'b': 99})

def test_update_with_kwargs_raises_typeerror(sample_frozendict):
    """FrozenDict.update with keyword arguments raises TypeError due to immutability."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict.update(b=99)

def test_pop_existing_key_raises_typeerror(sample_frozendict):
    """FrozenDict.pop raises TypeError even when the key exists."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict.pop('a')

def test_pop_missing_key_raises_typeerror(sample_frozendict):
    """FrozenDict.pop raises TypeError (not KeyError) for a missing key."""
    with pytest.raises(TypeError, match='object is immutable'):
        sample_frozendict.pop('missing', 'default')
