import pytest
from tinydb.storages import Storage
from tinydb.storages import MemoryStorage
from tinydb.storages import JSONStorage
from tinydb.storages import touch

import pytest
from tinydb.storages import Storage


def test_storage_abstract_class_cannot_be_instantiated():
    """
    The abstract Storage class itself cannot be instantiated directly
    because read() and write() are marked abstract.
    """
    with pytest.raises(TypeError):
        Storage()

import pytest
from tinydb.storages import Storage


def test_subclass_missing_read_cannot_be_instantiated():
    """
    A subclass that does not implement read() cannot be instantiated
    because read() remains abstract.
    """
    class IncompleteStorage(Storage):
        def write(self, data):
            pass

    with pytest.raises(TypeError):
        IncompleteStorage()

import pytest
from tinydb.storages import Storage


def test_subclass_missing_write_cannot_be_instantiated():
    """
    A subclass that does not implement write() cannot be instantiated
    because write() remains abstract.
    """
    class IncompleteStorage(Storage):
        def read(self):
            return None

    with pytest.raises(TypeError):
        IncompleteStorage()

from tinydb.storages import Storage


def test_subclass_implementing_both_methods_can_be_instantiated():
    """
    A subclass implementing both abstract methods (read and write)
    can be instantiated successfully.
    """
    class ConcreteStorage(Storage):
        def __init__(self):
            self._data = None

        def read(self):
            return self._data

        def write(self, data):
            self._data = data

    storage = ConcreteStorage()
    assert isinstance(storage, Storage)

from tinydb.storages import Storage


def test_base_close_is_noop():
    """
    The default Storage.close() implementation does nothing and
    returns None (per the source: body is just `pass`).
    """
    class ConcreteStorage(Storage):
        def __init__(self):
            self._data = None

        def read(self):
            return self._data

        def write(self, data):
            self._data = data

    storage = ConcreteStorage()
    assert storage.close() is None

from tinydb.storages import Storage


def test_subclass_can_override_close():
    """
    Subclasses may override the optional close() method to run
    custom cleanup logic.
    """
    calls = []

    class CustomCloseStorage(Storage):
        def __init__(self):
            self._data = None

        def read(self):
            return self._data

        def write(self, data):
            self._data = data

        def close(self):
            calls.append("closed")

    storage = CustomCloseStorage()
    storage.close()
    assert calls == ["closed"]

from tinydb.storages import MemoryStorage


def test_memory_storage_initial_read_returns_none():
    """
    A freshly created MemoryStorage has no stored data, and read()
    returns None to indicate the empty state, per the intent.
    """
    storage = MemoryStorage()
    assert storage.read() is None

from tinydb.storages import MemoryStorage


def test_memory_storage_write_then_read_roundtrip():
    """
    Data written to MemoryStorage via write() is returned unchanged
    by a subsequent read() call.
    """
    storage = MemoryStorage()
    data = {"users": {"1": {"name": "Alice", "age": 30}}}
    storage.write(data)
    assert storage.read() == data

from tinydb.storages import MemoryStorage


def test_memory_storage_write_replaces_previous_data():
    """
    A subsequent write() call replaces the previously stored data
    rather than merging.
    """
    storage = MemoryStorage()
    storage.write({"old": {"key": "old_value"}})
    new_data = {"new": {"key": "new_value"}}
    storage.write(new_data)
    assert storage.read() == new_data

from tinydb.storages import MemoryStorage


def test_memory_storage_close_does_not_raise():
    """
    Calling close() on MemoryStorage (which inherits the default
    no-op close() from Storage) executes without error.
    """
    storage = MemoryStorage()
    storage.write({"key": "value"})
    storage.close()

from tinydb.storages import JSONStorage, touch


def test_json_storage_empty_file_read_returns_none(tmp_path):
    """
    When the backing JSON file exists but is empty, JSONStorage.read()
    returns None to indicate the storage is empty.
    """
    path = str(tmp_path / "db.json")
    touch(path, create_dirs=False)

    storage = JSONStorage(path)
    try:
        assert storage.read() is None
    finally:
        storage.close()

from tinydb.storages import JSONStorage, touch


def test_json_storage_write_then_read_roundtrip(tmp_path):
    """
    Data written to JSONStorage via write() is returned by a subsequent
    read() within the same instance.
    """
    path = str(tmp_path / "db.json")
    touch(path, create_dirs=False)

    storage = JSONStorage(path)
    try:
        data = {"tables": {"items": {"1": {"name": "widget"}}}}
        storage.write(data)
        assert storage.read() == data
    finally:
        storage.close()

from tinydb.storages import JSONStorage, touch


def test_json_storage_persists_across_instances(tmp_path):
    """
    Data persisted to disk by one JSONStorage instance is readable
    by a freshly opened JSONStorage instance, proving that
    write() actually serializes to durable storage and close()
    flushes state.
    """
    path = str(tmp_path / "db.json")
    touch(path, create_dirs=False)

    data = {"persistent": {"key": "value"}}

    storage1 = JSONStorage(path)
    storage1.write(data)
    storage1.close()

    storage2 = JSONStorage(path)
    try:
        assert storage2.read() == data
    finally:
        storage2.close()
