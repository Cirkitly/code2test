import itertools
import pytest
from tinydb.utils import LRUCache

def test_capacity_is_stored():
    """The constructor stores the given cache size."""
    cache = LRUCache(capacity=5)
    assert cache.capacity == 5

def test_capacity_defaults_to_none():
    """Without an argument the cache size is unlimited (None)."""
    cache = LRUCache()
    assert cache.capacity is None

def test_setitem_and_getitem_roundtrip():
    """Items can be stored with [] and read back with []."""
    cache = LRUCache(capacity=3)
    cache['a'] = 1

    assert cache['a'] == 1
    assert 'a' in cache
    assert len(cache) == 1

def test_set_and_get_roundtrip():
    """Items can also be stored/read through the set()/get() methods."""
    cache = LRUCache(capacity=3)
    cache.set('a', 1)

    assert cache.get('a') == 1
    assert len(cache) == 1
    assert cache.lru == ['a']

def test_length_matches_number_of_entries():
    """len(cache) and the length property report the entry count."""
    cache = LRUCache(capacity=3)
    assert cache.length == 0
    assert len(cache) == 0

    cache['a'] = 1
    cache['b'] = 2

    assert cache.length == 2
    assert len(cache) == 2

def test_lru_lists_keys_from_least_to_most_recently_used():
    """lru lists keys from least- to most-recently used and follows accesses."""
    cache = LRUCache(capacity=3)
    cache['a'] = 1
    cache['b'] = 2
    cache['c'] = 3
    assert cache.lru == ['a', 'b', 'c']

    assert cache.get('a') == 1
    assert cache.lru == ['b', 'c', 'a']

def test_iteration_yields_keys_in_lru_order():
    """Iterating the cache yields keys ordered from LRU to MRU."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1
    cache['b'] = 2
    cache['c'] = 3

    assert list(cache) == ['b', 'c']
    assert list(cache.keys()) == ['b', 'c']

def test_iterating_does_not_change_the_lru_order():
    """Walking the cache is not an access and must not reorder anything."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1
    cache['b'] = 2

    list(cache)
    cache.lru
    len(cache)

    assert cache.lru == ['a', 'b']

def test_exceeding_capacity_discards_least_recently_used_entry():
    """Adding an entry beyond the cache size drops the least recently used one."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1
    cache['b'] = 2
    cache['c'] = 3

    assert 'a' not in cache
    assert cache.lru == ['b', 'c']
    assert len(cache) == 2
    assert cache['b'] == 2
    assert cache['c'] == 3

def test_getting_entry_prevents_it_from_being_evicted():
    """A read access refreshes an entry, so it survives the next insertion."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1
    cache['b'] = 2

    assert cache['a'] == 1  # 'a' becomes the most recently used entry
    cache['c'] = 3

    assert 'b' not in cache
    assert cache.lru == ['a', 'c']

def test_get_with_default_also_marks_entry_as_recently_used():
    """get() refreshes recency even when an explicit default is supplied."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1
    cache['b'] = 2

    assert cache.get('a', 'fallback') == 1
    cache['c'] = 3

    assert 'b' not in cache
    assert cache.lru == ['a', 'c']

def test_membership_check_does_not_mark_entry_as_recently_used():
    """Testing for a key with `in` is not an access and must not reorder."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1
    cache['b'] = 2

    assert 'a' in cache
    assert cache.lru == ['a', 'b']

    cache['c'] = 3

    assert 'a' not in cache
    assert cache.lru == ['b', 'c']

def test_updating_existing_key_refreshes_its_recency():
    """Overwriting an existing entry marks it as most recently used."""
    cache = LRUCache(capacity=3)
    cache['a'] = 1
    cache['b'] = 2

    cache['a'] = 10

    assert cache.lru == ['b', 'a']
    assert len(cache) == 2
    assert cache['a'] == 10

def test_cache_with_capacity_one_keeps_only_the_latest_entry():
    """A cache of size one keeps only the newest entry."""
    cache = LRUCache(capacity=1)
    cache['a'] = 1
    cache['b'] = 2

    assert cache.lru == ['b']
    assert len(cache) == 1
    assert cache['b'] == 2

    with pytest.raises(KeyError):
        cache['a']

def test_cache_with_capacity_zero_never_stores_entries():
    """A cache of size zero discards every entry immediately."""
    cache = LRUCache(capacity=0)
    cache['a'] = 1

    assert len(cache) == 0
    assert cache.lru == []
    assert 'a' not in cache

    with pytest.raises(KeyError):
        cache['a']

def test_cache_with_none_capacity_never_evicts_entries():
    """capacity=None disables eviction completely."""
    cache = LRUCache(capacity=None)
    for i in range(10):
        cache[i] = i

    assert len(cache) == 10
    assert cache.lru == list(range(10))

def test_cache_never_exceeds_capacity_while_being_filled():
    """Filling a bounded cache never makes it grow beyond its capacity."""
    capacity = 3
    cache = LRUCache(capacity=capacity)

    for i in range(10):
        cache[i] = i
        assert len(cache) <= capacity

    assert cache.lru == [7, 8, 9]
    assert set(cache.lru) == {7, 8, 9}

def test_delete_removes_entry():
    """del cache[key] removes the entry from the cache."""
    cache = LRUCache(capacity=3)
    cache['a'] = 1
    cache['b'] = 2

    del cache['a']

    assert 'a' not in cache
    assert cache.lru == ['b']
    assert len(cache) == 1

def test_deleting_missing_key_raises_keyerror():
    """Deleting a key that is not cached raises a KeyError."""
    cache = LRUCache(capacity=2)

    with pytest.raises(KeyError):
        del cache['missing']

def test_getitem_for_missing_key_raises_keyerror():
    """Reading a key that is not cached raises a KeyError."""
    cache = LRUCache(capacity=2)

    with pytest.raises(KeyError):
        cache['missing']

def test_get_returns_default_without_storing_the_key():
    """get() on a missing key returns the default and leaves the cache untouched."""
    cache = LRUCache(capacity=2)

    assert cache.get('missing') is None
    assert cache.get('missing', 'default') == 'default'
    assert len(cache) == 0
    assert cache.lru == []

def test_clear_empties_cache_but_keeps_it_usable():
    """clear() removes all entries, the cache stays usable afterwards."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1
    cache['b'] = 2

    cache.clear()

    assert len(cache) == 0
    assert cache.lru == []
    assert 'a' not in cache

    cache['c'] = 3
    assert cache['c'] == 3
    assert cache.lru == ['c']

def test_values_and_items_expose_single_entry():
    """The values() and items() mapping views report the cached entry."""
    cache = LRUCache(capacity=2)
    cache['a'] = 1

    assert list(cache.values()) == [1]
    assert list(cache.items()) == [('a', 1)]

def test_pop_removes_and_returns_entry():
    """pop() returns the value of an entry and removes it from the cache."""
    cache = LRUCache(capacity=3)
    cache['a'] = 1
    cache['b'] = 2

    assert cache.pop('a') == 1
    assert 'a' not in cache
    assert cache.lru == ['b']

def test_pop_with_default_and_pop_of_missing_key():
    """pop() returns the given default for unknown keys and raises otherwise."""
    cache = LRUCache(capacity=2)

    assert cache.pop('missing', 'default') == 'default'
    assert len(cache) == 0

    with pytest.raises(KeyError):
        cache.pop('missing')

def test_update_adds_multiple_entries():
    """update() adds all given entries in iteration order."""
    cache = LRUCache(capacity=3)
    cache.update({'a': 1, 'b': 2})

    assert cache.lru == ['a', 'b']
    assert dict(cache) == {'a': 1, 'b': 2}
    assert len(cache) == 2

def test_getitem_raises_keyerror_for_stored_none_value():
    """A stored None value is indistinguishable from a missing key for []."""
    cache = LRUCache(capacity=2)
    cache['a'] = None

    assert 'a' in cache
    assert cache.length == 1

    with pytest.raises(KeyError):
        cache['a']

def test_get_returns_default_for_stored_none_value():
    """get() falls back to the default when the cached value is None."""
    cache = LRUCache(capacity=2)
    cache['a'] = None

    assert cache.get('a') is None
    assert cache.get('a', 'default') == 'default'

def test_setting_existing_key_with_falsy_old_value_keeps_position():
    """Re-setting a key whose old value is falsy keeps its LRU position."""
    cache = LRUCache(capacity=3)
    cache['a'] = 0
    cache['b'] = 1

    cache['a'] = 5

    assert cache.lru == ['a', 'b']
    assert cache.length == 2
    assert cache['a'] == 5

def test_unhashable_keys_raise_typeerror():
    """Unhashable keys are rejected because the cache is backed by a dict."""
    cache = LRUCache(capacity=2)

    with pytest.raises(TypeError):
        cache[[1, 2]] = 'value'
