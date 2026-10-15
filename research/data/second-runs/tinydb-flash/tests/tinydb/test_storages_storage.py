import pytest
from abc import ABC
from tinydb.storages import Storage, JSONStorage, MemoryStorage

def test_storage_cannot_be_instantiated_directly():
    """The abstract base class itself must not be instantiable."""
    with pytest.raises(TypeError):
        Storage()

def test_storage_read_and_write_are_abstract():
    """Both read() and write() are abstract methods of the base class."""
    assert 'read' in Storage.__abstractmethods__
    assert 'write' in Storage.__abstractmethods__

def test_storage_close_is_not_abstract():
    """close() is documented as optional, so it is a concrete method."""
    assert 'close' not in Storage.__abstractmethods__
    assert callable(Storage.close)

class MinimalStorage(Storage):
    """A minimal concrete Storage that implements only the required methods."""

    def __init__(self):
        self.data = None

    def read(self):
        return self.data

    def write(self, data):
        self.data = data


def test_storage_default_close_is_a_noop_returning_none():
    """The base close() implementation is an optional no-op returning None."""
    storage = MinimalStorage()
    assert storage.close() is None

class MinimalStorage(Storage):
    """A minimal concrete Storage that implements only the required methods."""

    def __init__(self):
        self.data = None

    def read(self):
        return self.data

    def write(self, data):
        self.data = data


def test_concrete_subclass_can_be_instantiated():
    """Implementing read() and write() makes a subclass concrete and instantiable."""
    storage = MinimalStorage()
    assert isinstance(storage, Storage)

class ReadOnlyStorage(Storage):
    """A subclass that forgets to implement write()."""

    def read(self):
        return None


def test_subclass_missing_write_is_not_instantiable():
    """read() alone does not satisfy the interface; write() is also required."""
    assert issubclass(ReadOnlyStorage, Storage)
    with pytest.raises(TypeError):
        ReadOnlyStorage()

class WriteOnlyStorage(Storage):
    """A subclass that forgets to implement read()."""

    def write(self, data):
        self.data = data


def test_subclass_missing_read_is_not_instantiable():
    """write() alone does not satisfy the interface; read() is also required."""
    assert issubclass(WriteOnlyStorage, Storage)
    with pytest.raises(TypeError):
        WriteOnlyStorage()

class EmptyStorage(Storage):
    """A subclass that implements neither read() nor write()."""

    pass


def test_subclass_missing_both_methods_is_not_instantiable():
    """A completely empty subclass cannot be instantiated."""
    with pytest.raises(TypeError):
        EmptyStorage()

def test_storage_is_an_abc():
    """Storage inherits from ABC, so instantiation rules are enforced by ABCMeta."""
    assert issubclass(Storage, ABC)

def test_read_can_return_none_for_empty_storage():
    """The abstract Storage.read must be overridden; the base implementation raises."""
    with pytest.raises(NotImplementedError):
        Storage.read(None)

class NoCloseStorage(Storage):
    """A concrete subclass relying on the inherited no-op close()."""

    def read(self):
        return None

    def write(self, data):
        self.data = data


def test_subclass_can_inherit_default_close_and_still_be_instantiable():
    """Because close() is not abstract, subclasses may simply inherit it."""
    storage = NoCloseStorage()
    assert storage.close() is None
    assert NoCloseStorage.close is Storage.close

def test_read_and_write_round_trip_via_custom_storage():
    """A concrete storage round-trips whatever write() stored back through read()."""
    class InMemoryStorage(Storage):
        def __init__(self):
            self._data = None

        def read(self):
            return self._data

        def write(self, data):
            self._data = data

    storage = InMemoryStorage()
    assert storage.read() is None  # empty storage -> None

    payload = {'_default': {'name': 'value'}}
    storage.write(payload)
    assert storage.read() == payload

def test_memory_storage_implements_storage_interface():
    """The bundled MemoryStorage honours the abstract base class contract."""
    storage = MemoryStorage()
    assert isinstance(storage, Storage)
    assert storage.read() is None

    data = {'_default': {'int': 1}}
    storage.write(data)
    assert storage.read() == data

    assert storage.close() is None

def test_json_storage_implements_storage_interface(tmp_path):
    """The bundled JSONStorage honours the abstract base class contract."""
    path = str(tmp_path / 'db.json')

    storage = JSONStorage(path)
    assert isinstance(storage, Storage)
    assert storage.read() is None  # missing file -> None (empty storage)

    data = {'_default': {'int': 1}}
    storage.write(data)
    assert storage.read() == data

    # close() from the base class contract returns None and releases handles
    assert storage.close() is None

def test_storage_subclass_can_opt_in_to_notimplemented_error_from_base():
    """Subclasses can delegate to super() and get a clear NotImplementedError."""

    class LazyStorage(Storage):
        def read(self):
            return super().read()

        def write(self, data):
            return super().write(data)

    storage = LazyStorage()
    with pytest.raises(NotImplementedError):
        storage.read()
    with pytest.raises(NotImplementedError):
        storage.write({})
