import pytest
from tinydb.utils import LRUCache

def test_create_cache_with_capacity():
    """A cache created with a capacity starts empty and stores the capacity."""
    cache = LRUCache(capacity=3)
    assert cache.length == 0
    assert cache.capacity == 3

def test_create_cache_without_capacity():
    """A cache created without a capacity has capacity=None (unlimited)."""
    cache = LRUCache()
    assert cache.length == 0
    assert cache.capacity is None

def test_set_and_get_item_via_dict_syntax():
    """Items can be set and retrieved using dict-like syntax."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    assert cache["a"] == 1
    assert cache.length == 1

def test_set_via_explicit_set_method():
    """The set() method stores a key/value pair."""
    cache = LRUCache(capacity=3)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.length == 1

def test_get_returns_default_for_missing_key():
    """get() returns the default for a missing key (None and explicit defaults)."""
    cache = LRUCache(capacity=3)
    assert cache.get("missing") is None
    assert cache.get("missing", "fallback") == "fallback"

def test_getitem_raises_keyerror_for_missing_key():
    """__getitem__ raises KeyError for missing keys."""
    cache = LRUCache(capacity=3)
    with pytest.raises(KeyError):
        _ = cache["missing"]

def test_len_reports_current_size():
    """len() reflects the number of items in the cache."""
    cache = LRUCache(capacity=3)
    assert len(cache) == 0
    cache["a"] = 1
    assert len(cache) == 1
    cache["b"] = 2
    assert len(cache) == 2

def test_contains_operator():
    """The 'in' operator returns True for present keys and False otherwise."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    assert "a" in cache
    assert "missing" not in cache

def test_delete_existing_item():
    """Deleting an existing key removes it from the cache."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    del cache["a"]
    assert "a" not in cache
    assert cache.length == 0

def test_delete_missing_raises_keyerror():
    """Deleting a missing key raises KeyError."""
    cache = LRUCache(capacity=3)
    with pytest.raises(KeyError):
        del cache["missing"]

def test_iter_yields_keys():
    """The cache is iterable and yields its keys."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    cache["b"] = 2
    keys = list(cache)
    assert set(keys) == {"a", "b"}
    assert len(keys) == 2

def test_clear_empties_cache():
    """clear() removes all items from the cache."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    cache["b"] = 2
    cache.clear()
    assert cache.length == 0
    assert "a" not in cache
    assert "b" not in cache

def test_lru_property_orders_insertion_from_lru_to_mru():
    """lru lists keys in insertion order: LRU first, MRU last."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3
    assert cache.lru == ["a", "b", "c"]

def test_lru_property_reflects_eviction_order():
    """The head of lru is the next key to be evicted on overflow."""
    cache = LRUCache(capacity=2)
    cache["a"] = 1
    cache["b"] = 2
    assert cache.lru[0] == "a"
    cache["c"] = 3
    assert "a" not in cache
    assert cache.lru == ["b", "c"]

def test_evicts_lru_when_capacity_exceeded():
    """Exceeding capacity evicts the least-recently-used key."""
    cache = LRUCache(capacity=2)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3
    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache
    assert cache.length == 2

def test_access_promotes_item_to_mru():
    """Accessing an item moves it to the MRU end of the OrderedDict."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3
    _ = cache.get("a")
    assert cache.lru == ["b", "c", "a"]
    _ = cache["c"]
    assert cache.lru == ["b", "a", "c"]

def test_recently_accessed_item_survives_eviction():
    """A recently accessed item is not evicted on the next insertion."""
    cache = LRUCache(capacity=2)
    cache["a"] = 1
    cache["b"] = 2
    _ = cache.get("a")  # promote 'a' to MRU; 'b' is now the LRU
    cache["c"] = 3
    assert "a" in cache
    assert "b" not in cache
    assert "c" in cache

def test_set_existing_key_updates_value():
    """Re-setting an existing key updates the value and keeps the size constant."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    cache["a"] = 2
    assert cache["a"] == 2
    assert cache.length == 1

def test_set_existing_key_promotes_to_mru():
    """Updating an existing key promotes it to the MRU end."""
    cache = LRUCache(capacity=3)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3
    cache["a"] = 10
    assert cache.lru == ["b", "c", "a"]
    assert cache["a"] == 10

def test_unlimited_capacity_never_evicts():
    """capacity=None means the cache never evicts items."""
    cache = LRUCache()
    for i in range(100):
        cache[f"key{i}"] = i
    assert cache.length == 100
    assert cache.get("key0") == 0
    assert cache.get("key99") == 99

def test_capacity_one_keeps_only_most_recent():
    """capacity=1 keeps only the most recently inserted item."""
    cache = LRUCache(capacity=1)
    cache["a"] = 1
    cache["b"] = 2
    assert "a" not in cache
    assert "b" in cache
    assert cache.length == 1

def test_capacity_one_access_protects_current_item():
    """Accessing the sole item keeps it alive across the next insert."""
    cache = LRUCache(capacity=1)
    cache["a"] = 1
    _ = cache.get("a")
    cache["b"] = 2
    assert "a" not in cache
    assert "b" in cache

def test_capacity_zero_evicts_immediately():
    """capacity=0 means no item can survive its insertion."""
    cache = LRUCache(capacity=0)
    cache["a"] = 1
    assert "a" not in cache
    assert cache.length == 0

def test_repeated_inserts_evict_oldest_in_order():
    """Inserting many items keeps only the most recent `capacity` ones."""
    cache = LRUCache(capacity=2)
    for i in range(10):
        cache[f"key{i}"] = i
    assert cache.length == 2
    assert cache.lru == ["key8", "key9"]
    assert cache["key8"] == 8
    assert cache["key9"] == 9
    assert "key0" not in cache
    assert "key7" not in cache
