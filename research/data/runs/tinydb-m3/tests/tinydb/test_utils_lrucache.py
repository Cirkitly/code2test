import pytest
from tinydb.utils import LRUCache

import pytest

from tinydb.utils import LRUCache


def test_set_and_get_stores_and_retrieves_values():
    """cache.set stores values that are retrievable via cache.get."""
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    assert cache.get("b") == 2


def test_exceeding_capacity_evicts_least_recently_used():
    """When capacity is exceeded, the LRU entry is evicted on the next insert."""
    cache = LRUCache(capacity=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache
    assert len(cache) == 2


def test_get_promotes_entry_to_most_recently_used():
    """cache.get marks the accessed entry as most recently used."""
    cache = LRUCache(capacity=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # promote 'a' to the end
    cache.set("c", 3)  # should evict 'b' instead of 'a'
    assert "a" in cache
    assert "b" not in cache
    assert "c" in cache


def test_set_existing_key_promotes_to_most_recently_used():
    """Updating an existing entry via set() promotes it to MRU."""
    cache = LRUCache(capacity=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)  # update 'a' and promote it
    cache.set("c", 3)  # should evict 'b' instead of 'a'
    assert "a" in cache
    assert cache.get("a") == 10
    assert "b" not in cache
    assert "c" in cache


def test_unlimited_capacity_when_capacity_is_none():
    """capacity=None means items are never evicted (unbounded growth)."""
    cache = LRUCache(capacity=None)
    for i in range(50):
        cache.set(i, i)
    assert len(cache) == 50


def test_zero_capacity_evicts_immediately():
    """A cache with capacity=0 holds no items after a set completes."""
    cache = LRUCache(capacity=0)
    cache.set("a", 1)
    assert "a" not in cache
    assert len(cache) == 0


def test_lru_property_lists_keys_oldest_first():
    """The ``lru`` property returns keys ordered from LRU (first) to MRU (last)."""
    cache = LRUCache(capacity=4)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.lru == ["a", "b", "c"]
    # Accessing 'a' promotes it to MRU, shifting it to the end of the list
    cache.get("a")
    assert cache.lru == ["b", "c", "a"]


def test_length_property_and_dunder_len():
    """The ``length`` property and ``__len__`` report the entry count."""
    cache = LRUCache(capacity=4)
    assert cache.length == 0
    assert len(cache) == 0
    cache.set("a", 1)
    assert cache.length == 1
    assert len(cache) == 1


def test_clear_empties_the_cache():
    """cache.clear removes every entry from the cache."""
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0
    assert "a" not in cache
    assert "b" not in cache


def test_dict_setitem_and_getitem():
    """Cache supports dict-style __setitem__ and __getitem__ access."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    cache["b"] = 2
    assert cache["a"] == 1
    assert cache["b"] == 2


def test_dict_contains():
    """Cache supports the ``in`` operator via __contains__."""
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    assert "a" in cache
    assert "missing" not in cache


def test_dict_delitem():
    """Cache supports the ``del`` operator via __delitem__."""
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    cache.set("b", 2)
    del cache["a"]
    assert "a" not in cache
    assert len(cache) == 1


def test_dict_delitem_missing_raises_keyerror():
    """Deleting a missing key raises KeyError."""
    cache = LRUCache(capacity=3)
    with pytest.raises(KeyError):
        del cache["missing"]


def test_getitem_missing_key_raises_keyerror():
    """dict-style access on a missing key raises KeyError."""
    cache = LRUCache(capacity=3)
    with pytest.raises(KeyError):
        _ = cache["missing"]


def test_get_returns_default_when_missing():
    """cache.get returns the supplied default (or None) for missing keys."""
    cache = LRUCache(capacity=3)
    assert cache.get("missing") is None
    assert cache.get("missing", "fallback") == "fallback"


def test_iter_preserves_lru_order():
    """Iteration yields keys from least- to most-recently used."""
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert list(cache) == ["a", "b", "c"]


def test_set_with_same_key_does_not_grow():
    """Re-setting the same key does not increase the cache size."""
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    cache.set("a", 2)
    cache.set("a", 3)
    assert len(cache) == 1
    assert cache.get("a") == 3

