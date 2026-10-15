import pytest
from tinydb.storages import MemoryStorage
from tinydb.storages import Storage

def test_memory_storage_inherits_from_storage():
    """MemoryStorage must be a subclass of the abstract Storage class."""
    from tinydb.storages import Storage

    assert issubclass(MemoryStorage, Storage)


def test_memory_storage_can_be_instantiated():
    """MemoryStorage should be instantiable with no arguments (matching its __init__ signature)."""
    storage = MemoryStorage()
    assert storage is not None


def test_initial_memory_is_none():
    """A freshly constructed MemoryStorage should have its memory set to None."""
    storage = MemoryStorage()
    assert storage.memory is None


def test_read_before_write_returns_none():
    """read() on a brand new instance must return None, matching the Optional return type."""
    storage = MemoryStorage()
    result = storage.read()
    assert result is None


def test_write_then_read_returns_same_data():
    """The primary happy path: data written via write() must be retrievable through read()."""
    storage = MemoryStorage()
    data = {"table1": {"row1": {"name": "Alice", "age": 30}}}
    storage.write(data)
    result = storage.read()
    assert result == data


def test_write_overwrites_previous_data():
    """A second write() must replace, not merge with, previously stored data."""
    storage = MemoryStorage()
    storage.write({"old": {"id": 1}})
    storage.write({"new": {"id": 2}})
    result = storage.read()
    assert result == {"new": {"id": 2}}
    assert "old" not in result


def test_write_with_empty_dict():
    """Edge case: writing an empty dict should be allowed and stored."""
    storage = MemoryStorage()
    storage.write({})
    result = storage.read()
    assert result == {}
    assert isinstance(result, dict)


def test_write_with_nested_dict_structure():
    """Edge case: writing a deeply nested dict (as JSON would deserialize to) should round-trip."""
    storage = MemoryStorage()
    data = {
        "users": {
            "u1": {"name": "Bob", "meta": {"tags": ["a", "b"], "active": True, "score": 0.5}},
            "u2": {"name": "Carol", "meta": {"tags": [], "active": False, "score": None}},
        }
    }
    storage.write(data)
    result = storage.read()
    assert result == data
    assert result["users"]["u1"]["meta"]["tags"] == ["a", "b"]
    assert result["users"]["u2"]["meta"]["score"] is None


def test_close_method_is_callable():
    """MemoryStorage inherits close() from Storage; it must be callable without error."""
    storage = MemoryStorage()
    storage.write({"some": {"data": 1}})
    # Should not raise
    storage.close()


def test_close_is_callable_on_empty_storage():
    """close() should also be safe to call on a fresh, never-written instance."""
    storage = MemoryStorage()
    storage.close()


def test_read_returns_same_object_reference():
    """Per the source, read() returns self.memory directly (reference, not copy).

    Verifying this contract so future refactors don't silently change semantics.
    """
    storage = MemoryStorage()
    data = {"k": {"v": 1}}
    storage.write(data)
    result = storage.read()
    assert result is data


def test_multiple_sequential_writes_keep_only_latest():
    """The memory buffer holds only the most recently written data."""
    storage = MemoryStorage()
    payloads = [
        {"a": {"x": 1}},
        {"b": {"y": 2}},
        {"c": {"z": 3}},
    ]
    for payload in payloads:
        storage.write(payload)
    assert storage.read() == payloads[-1]


def test_write_with_dict_containing_special_values():
    """Edge case: dict containing common JSON-friendly values (bool, None, int, float, str, list)."""
    storage = MemoryStorage()
    data = {
        "mixed": {
            "row": {
                "flag": True,
                "nothing": None,
                "count": 42,
                "ratio": 3.14,
                "label": "hello",
                "items": [1, 2, 3],
            }
        }
    }
    storage.write(data)
    result = storage.read()
    assert result == data
    assert result["mixed"]["row"]["flag"] is True
    assert result["mixed"]["row"]["nothing"] is None
    assert result["mixed"]["row"]["items"] == [1, 2, 3]


def test_read_after_close_does_not_raise():
    """Reading after close() should still work since the data lives in process memory."""
    storage = MemoryStorage()
    storage.write({"after": {"close": True}})
    storage.close()
    # Data is still in memory; read() should still return it.
    assert storage.read() == {"after": {"close": True}}

