import json
import pytest
from typing import Any, Dict, Optional
from tinydb.storages import MemoryStorage, Storage

@pytest.fixture
def storage():
    """Provide a fresh, empty MemoryStorage instance for each test."""
    return MemoryStorage()

def test_read_returns_none_before_any_write(storage):
    """A freshly constructed MemoryStorage holds no data yet."""
    assert storage.read() is None

def test_memory_storage_implements_the_storage_interface():
    """MemoryStorage is a usable, concrete implementation of the Storage ABC."""
    assert issubclass(MemoryStorage, Storage)
    assert isinstance(MemoryStorage(), Storage)

def test_write_then_read_returns_written_data(storage):
    """The primary happy path: written data is available through read()."""
    data = {'1': {'name': 'Alice', 'age': 30}}

    storage.write(data)

    assert storage.read() == {'1': {'name': 'Alice', 'age': 30}}

def test_read_returns_the_exact_object_that_was_written(storage):
    """The data is kept in memory as-is: read() hands back the very same object."""
    data = {'1': {'value': 1}}

    storage.write(data)

    assert storage.read() is data

def test_write_stores_a_reference_and_not_a_snapshot(storage):
    """No copy is made, so in-place mutations of the written dict are visible."""
    data = {'1': {'value': 1}}
    storage.write(data)

    data['1']['value'] = 2
    data['2'] = {'value': 3}

    assert storage.read() == {'1': {'value': 2}, '2': {'value': 3}}

def test_later_write_replaces_the_previously_stored_data(storage):
    """Each write overwrites the whole in-memory content instead of merging."""
    storage.write({'1': {'value': 'first'}})
    storage.write({'2': {'value': 'second'}})

    result = storage.read()

    assert result == {'2': {'value': 'second'}}
    assert '1' not in result
    assert len(result) == 1

def test_write_empty_dict_then_read_returns_empty_dict_not_none(storage):
    """Empty content is a valid state and is distinguishable from 'never written'."""
    storage.write({})

    result = storage.read()

    assert result == {}
    assert result is not None

def test_write_returns_none(storage):
    """write() is a pure side effect and returns None."""
    assert storage.write({'1': {'value': 1}}) is None

def test_read_returns_a_plain_dict_instance(storage):
    """The data is kept as a plain Python dict, which is the in-memory JSON form."""
    storage.write({'1': {'value': 1}})

    assert isinstance(storage.read(), dict)

def test_instances_do_not_share_their_memory():
    """Two storages are fully independent; writing to one does not affect the other."""
    first = MemoryStorage()
    second = MemoryStorage()

    first.write({'1': {'value': 1}})

    assert first.read() == {'1': {'value': 1}}
    assert second.read() is None

def test_separate_instances_can_hold_different_data():
    """Independent storages can hold different payloads at the same time."""
    first = MemoryStorage()
    second = MemoryStorage()

    first.write({'a': {'v': 1}})
    second.write({'b': {'v': 2}})

    assert first.read() == {'a': {'v': 1}}
    assert second.read() == {'b': {'v': 2}}

@pytest.mark.parametrize('payload', [
    {},
    {'1': {}},
    {'0': {'flag': False, 'value': 0, 'text': ''}},
    {'1': {'nested': {'list': [1, 2, 3], 'none': None, 'flag': True}}},
    {'1': {'unicode': 'ünïcödé ☃'}, '2': {'pi': 3.14}},
    {'t1': {'items': []}, 't2': {'items': [{}]}},
])
def test_write_read_roundtrip_for_json_like_payloads(storage, payload):
    """Any JSON-compatible mapping survives the write/read round trip unchanged."""
    storage.write(payload)

    result = storage.read()

    assert result == payload
    assert result is payload

def test_falsy_table_keys_are_stored_normally(storage):
    """Falsy-but-valid table names are stored and read back without special casing."""
    payload = {'0': {'v': 1}, '': {'v': 2}}

    storage.write(payload)

    result = storage.read()

    assert result == payload
    assert '0' in result
    assert '' in result

def test_close_returns_none_for_memory_storage(storage):
    """Closing an in-memory storage is allowed and returns None."""
    assert storage.close() is None

def test_close_does_not_clear_the_stored_data(storage):
    """Because the data lives in the object, close() must not wipe it."""
    storage.write({'1': {'value': 1}})

    storage.close()

    assert storage.read() == {'1': {'value': 1}}

def test_read_can_be_called_repeatedly_without_changing_state(storage):
    """read() only returns the stored data; calling it repeatedly is side-effect free."""
    storage.write({'1': {'value': 1}})

    first = storage.read()
    second = storage.read()

    assert first == second
    assert storage.read() == {'1': {'value': 1}}
