import pytest
from tinydb.utils import FrozenDict

def test_frozen_dict_is_dict_subclass():
    """Verify FrozenDict is a subclass of dict, confirming it behaves as a dictionary."""
    fd = FrozenDict({'a': 1})
    assert isinstance(fd, dict)


def test_frozen_dict_construction_from_mapping():
    """Test that FrozenDict can be constructed from a regular dict mapping."""
    fd = FrozenDict({'a': 1, 'b': 2, 'c': 3})
    assert fd['a'] == 1
    assert fd['b'] == 2
    assert fd['c'] == 3
    assert len(fd) == 3


def test_frozen_dict_construction_from_kwargs():
    """Test that FrozenDict can be constructed from keyword arguments."""
    fd = FrozenDict(a=1, b=2)
    assert fd['a'] == 1
    assert fd['b'] == 2
    assert len(fd) == 2


def test_frozen_dict_construction_from_iterable_of_pairs():
    """Test that FrozenDict can be constructed from an iterable of key-value pairs."""
    fd = FrozenDict([('a', 1), ('b', 2)])
    assert fd['a'] == 1
    assert fd['b'] == 2
    assert len(fd) == 2


def test_frozen_dict_empty_construction():
    """Test that an empty FrozenDict can be created with no arguments."""
    fd = FrozenDict()
    assert len(fd) == 0
    assert list(fd.keys()) == []
    assert list(fd.values()) == []
    assert list(fd.items()) == []


def test_frozen_dict_read_operations_work():
    """Test that all standard read operations on a FrozenDict work like a regular dict."""
    fd = FrozenDict({'a': 1, 'b': 2, 'c': 3})
    # __getitem__
    assert fd['a'] == 1
    # get with default
    assert fd.get('a') == 1
    assert fd.get('z') is None
    assert fd.get('z', 'default') == 'default'
    # __contains__
    assert 'a' in fd
    assert 'z' not in fd
    # keys, values, items
    assert list(fd.keys()) == ['a', 'b', 'c']
    assert list(fd.values()) == [1, 2, 3]
    assert list(fd.items()) == [('a', 1), ('b', 2), ('c', 3)]
    # __len__
    assert len(fd) == 3


def test_frozen_dict_iteration():
    """Test that FrozenDict supports iteration over its keys like a regular dict."""
    fd = FrozenDict({'a': 1, 'b': 2})
    keys = list(fd)
    assert 'a' in keys
    assert 'b' in keys
    assert len(keys) == 2


def test_frozen_dict_is_hashable():
    """Test that FrozenDict is hashable (the primary purpose: stable hashes for queries)."""
    fd = FrozenDict({'a': 1, 'b': 2})
    # Should not raise TypeError; a regular dict is unhashable in Python 3
    h = hash(fd)
    assert isinstance(h, int)


def test_frozen_dict_empty_is_hashable():
    """Test that an empty FrozenDict is hashable (edge case)."""
    fd = FrozenDict()
    # Should not raise TypeError
    h = hash(fd)
    assert isinstance(h, int)


def test_frozen_dict_hash_is_consistent_across_calls():
    """Test that hash() returns the same value on repeated calls for the same FrozenDict."""
    fd = FrozenDict({'a': 1, 'b': 2, 'c': 3})
    assert hash(fd) == hash(fd)
    # Multiple calls to ensure stability
    first = hash(fd)
    for _ in range(5):
        assert hash(fd) == first


def test_frozen_dict_equal_instances_have_equal_hashes():
    """Test that two FrozenDicts with equal content have equal hashes (hash contract)."""
    fd1 = FrozenDict({'a': 1, 'b': 2})
    fd2 = FrozenDict({'a': 1, 'b': 2})
    assert fd1 == fd2
    assert hash(fd1) == hash(fd2)


def test_frozen_dict_hash_is_independent_of_insertion_order():
    """Test that hash() is the same regardless of the order keys were inserted (because items are sorted)."""
    fd1 = FrozenDict({'a': 1, 'b': 2, 'c': 3})
    fd2 = FrozenDict({'c': 3, 'a': 1, 'b': 2})
    fd3 = FrozenDict({'b': 2, 'c': 3, 'a': 1})
    assert fd1 == fd2 == fd3
    assert hash(fd1) == hash(fd2)
    assert hash(fd2) == hash(fd3)


def test_frozen_dict_hash_matches_expected_calculation():
    """Test that hash() matches the documented algorithm: hash(tuple(sorted(items)))."""
    data = {'b': 1, 'a': 2, 'c': 3}
    fd = FrozenDict(data)
    # The algorithm: hash(tuple(sorted(self.items())))
    expected = hash(tuple(sorted(data.items())))
    assert hash(fd) == expected


def test_frozen_dict_empty_hash_is_consistent():
    """Test that two empty FrozenDicts have the same hash."""
    fd1 = FrozenDict()
    fd2 = FrozenDict()
    assert hash(fd1) == hash(fd2)
    # Both should equal hash(()) since sorted([]) == [] and tuple([]) == ()
    assert hash(fd1) == hash(())


def test_frozen_dict_can_be_used_as_dict_key():
    """Test that a FrozenDict can be used as a key in another dict (use case: query caching)."""
    fd1 = FrozenDict({'a': 1})
    fd2 = FrozenDict({'a': 1})
    cache = {fd1: 'result_for_a'}
    # Lookup with an equal but distinct FrozenDict
    assert cache[fd2] == 'result_for_a'


def test_frozen_dict_can_be_added_to_set():
    """Test that a FrozenDict can be added to a set (use case: query deduplication)."""
    fd1 = FrozenDict({'a': 1, 'b': 2})
    fd2 = FrozenDict({'a': 1, 'b': 2})
    s = {fd1}
    # Equal FrozenDict should be found in the set
    assert fd2 in s
    # Set should have only one element since they are equal
    assert len(s) == 1


def test_frozen_dict_setitem_raises_typeerror():
    """Test that __setitem__ raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1})
    with pytest.raises(TypeError, match='object is immutable'):
        fd['b'] = 2
    # Original dict unchanged
    assert fd['a'] == 1
    assert 'b' not in fd


def test_frozen_dict_delitem_raises_typeerror():
    """Test that __delitem__ raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1, 'b': 2})
    with pytest.raises(TypeError, match='object is immutable'):
        del fd['a']
    # Original dict unchanged
    assert fd['a'] == 1
    assert fd['b'] == 2
    assert len(fd) == 2


def test_frozen_dict_clear_raises_typeerror():
    """Test that clear() raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1, 'b': 2})
    with pytest.raises(TypeError, match='object is immutable'):
        fd.clear()
    # Original dict unchanged
    assert len(fd) == 2
    assert fd['a'] == 1


def test_frozen_dict_setdefault_raises_typeerror():
    """Test that setdefault() raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1})
    with pytest.raises(TypeError, match='object is immutable'):
        fd.setdefault('b', 2)
    # Original dict unchanged
    assert 'b' not in fd
    assert len(fd) == 1


def test_frozen_dict_popitem_raises_typeerror():
    """Test that popitem() raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1})
    with pytest.raises(TypeError, match='object is immutable'):
        fd.popitem()
    # Original dict unchanged
    assert len(fd) == 1
    assert fd['a'] == 1


def test_frozen_dict_update_with_mapping_raises_typeerror():
    """Test that update() with a mapping argument raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1})
    with pytest.raises(TypeError, match='object is immutable'):
        fd.update({'b': 2, 'c': 3})
    # Original dict unchanged
    assert 'b' not in fd
    assert 'c' not in fd
    assert len(fd) == 1


def test_frozen_dict_update_with_kwargs_raises_typeerror():
    """Test that update() with keyword arguments raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1})
    with pytest.raises(TypeError, match='object is immutable'):
        fd.update(b=2, c=3)
    # Original dict unchanged
    assert 'b' not in fd
    assert 'c' not in fd
    assert len(fd) == 1


def test_frozen_dict_pop_raises_typeerror():
    """Test that pop() raises TypeError (immutability)."""
    fd = FrozenDict({'a': 1, 'b': 2})
    with pytest.raises(TypeError, match='object is immutable'):
        fd.pop('a')
    # Even with a default value, pop should raise
    with pytest.raises(TypeError, match='object is immutable'):
        fd.pop('z', 'default')
    # Original dict unchanged
    assert fd['a'] == 1
    assert fd['b'] == 2
    assert len(fd) == 2


def test_frozen_dict_compares_equal_to_regular_dict():
    """Test that a FrozenDict compares equal to a regular dict with the same content."""
    fd = FrozenDict({'a': 1, 'b': 2})
    d = {'a': 1, 'b': 2}
    assert fd == d
    assert d == fd


def test_frozen_dict_with_unhashable_values_fails_on_hash():
    """Test that hashing a FrozenDict containing unhashable values raises TypeError (documents a limitation)."""
    fd = FrozenDict({'a': [1, 2, 3]})
    # The hash algorithm will attempt to hash the list value, which is unhashable
    with pytest.raises(TypeError):
        hash(fd)
    # The FrozenDict itself can still be constructed and read
    assert fd['a'] == [1, 2, 3]

