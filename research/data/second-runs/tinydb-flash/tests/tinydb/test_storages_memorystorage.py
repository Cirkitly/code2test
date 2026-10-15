import pytest
import json
from tinydb.storages import MemoryStorage, Storage

def test_memory_storage_is_storage_instance():
    """A MemoryStorage instance must be usable as a Storage."""
    storage = MemoryStorage()

    assert isinstance(storage, Storage)

def test_read_returns_none_before_any_write():
    """Before any write, reading from memory returns None."""
    storage = MemoryStorage()

    assert storage.read() is None

def test_write_then_read_returns_written_data():
    """Data passed to write() is returned unchanged by the following read()."""
    storage = MemoryStorage()
    data = {'table1': {'key1': 'value1', 'key2': 42}}

    storage.write(data)

    assert storage.read() == data

def test_written_data_is_json_serializable():
    """Data held in memory is JSON-serializable, matching the 'as JSON in memory' intent."""
    import json

    storage = MemoryStorage()
    data = {'table': {'a': 1, 'b': [1, 2, 3], 'c': {'d': None}, 'e': True}}

    storage.write(data)

    assert json.loads(json.dumps(storage.read())) == data

def test_writing_empty_dict_reads_back_empty_dict():
    """Writing an empty mapping stores it as-is instead of being treated as 'no data'."""
    storage = MemoryStorage()

    storage.write({})

    assert storage.read() == {}

def test_write_overwrites_previously_stored_data():
    """A later write replaces the earlier content instead of merging it."""
    storage = MemoryStorage()

    storage.write({'first': {'a': 1}})
    storage.write({'second': {'b': 2}})

    assert storage.read() == {'second': {'b': 2}}

def test_read_does_not_mutate_stored_data():
    """Repeated reads return the same data; read() has no side effects."""
    storage = MemoryStorage()
    data = {'table': {'key': 'value'}}
    storage.write(data)

    first = storage.read()
    second = storage.read()

    assert first == second == data

def test_instances_do_not_share_state():
    """Each MemoryStorage instance owns its own data."""
    storage_a = MemoryStorage()
    storage_b = MemoryStorage()

    storage_a.write({'a': {'x': 1}})
    storage_b.write({'b': {'y': 2}})

    assert storage_a.read() == {'a': {'x': 1}}
    assert storage_b.read() == {'b': {'y': 2}}

def test_fresh_instance_reads_none_even_after_another_instance_writes():
    """A newly created MemoryStorage starts empty regardless of other instances."""
    used = MemoryStorage()
    used.write({'table': {'key': 'value'}})

    fresh = MemoryStorage()

    assert fresh.read() is None

def test_read_result_is_a_dict():
    """After a write, read() returns a dict as declared by the return type."""
    storage = MemoryStorage()

    storage.write({'table': {'key': 'value'}})

    result = storage.read()
    assert isinstance(result, dict)

def test_nested_data_with_mixed_value_types_is_stored_intact():
    """Arbitrary JSON-compatible value types survive the write/read round trip."""
    storage = MemoryStorage()
    data = {
        'users': {
            '1': {'name': 'John', 'age': 30, 'active': True, 'score': 4.5,
                  'tags': ['a', 'b'], 'meta': {'nested': {'deep': None}}},
        }
    }

    storage.write(data)

    assert storage.read() == data

def test_close_is_a_noop_and_data_survives():
    """close() is a harmless no-op for an in-memory storage."""
    storage = MemoryStorage()
    data = {'table': {'key': 'value'}}
    storage.write(data)

    storage.close()

    assert storage.read() == data

def test_write_returns_none():
    """write() returns None as declared by its signature."""
    storage = MemoryStorage()

    assert storage.write({'table': {'key': 'value'}}) is None

def test_read_returns_none_again_after_close_on_unwritten_storage():
    """Closing a storage that was never written to still reads None."""
    storage = MemoryStorage()

    storage.close()

    assert storage.read() is None
