import inspect
import typing
from abc import ABCMeta
from typing import Any, Dict, Optional
import pytest
from tinydb.storages import Storage, MemoryStorage, JSONStorage

@pytest.fixture
def concrete_storage_class():
    """A minimal concrete Storage subclass implementing only the required methods."""
    class ConcreteStorage(Storage):
        def __init__(self):
            self.data = None

        def read(self):
            return self.data

        def write(self, data):
            self.data = data

    return ConcreteStorage

@pytest.fixture
def concrete_storage(concrete_storage_class):
    """An instance of a minimal concrete Storage subclass."""
    return concrete_storage_class()

@pytest.fixture
def delegating_storage_class():
    """A concrete Storage whose read/write delegate to the abstract base implementations."""
    class DelegatingStorage(Storage):
        def read(self):
            return super().read()

        def write(self, data):
            return super().write(data)

    return DelegatingStorage

def test_storage_cannot_be_instantiated_directly():
    # Storage is declared as `class Storage(ABC)`, so the abstract base class
    # itself must not be instantiable.
    with pytest.raises(TypeError):
        Storage()

def test_storage_is_an_abstract_base_class():
    assert inspect.isabstract(Storage)
    assert isinstance(Storage, ABCMeta)

def test_read_and_write_are_the_only_abstract_methods():
    # Only `read` and `write` are decorated with @abstractmethod; `close` is a
    # plain, optional method.
    assert set(Storage.__abstractmethods__) == {'read', 'write'}

def test_concrete_subclass_implementing_read_and_write_can_be_instantiated(
    concrete_storage_class,
):
    storage = concrete_storage_class()
    assert isinstance(storage, Storage)

def test_subclass_missing_read_cannot_be_instantiated():
    class NoReadStorage(Storage):
        def write(self, data):
            pass

    with pytest.raises(TypeError, match='read'):
        NoReadStorage()

def test_subclass_missing_write_cannot_be_instantiated():
    class NoWriteStorage(Storage):
        def read(self):
            return None

    with pytest.raises(TypeError, match='write'):
        NoWriteStorage()

def test_subclass_missing_both_read_and_write_cannot_be_instantiated():
    class EmptyStorage(Storage):
        pass

    with pytest.raises(TypeError):
        EmptyStorage()

def test_extra_methods_do_not_make_an_incomplete_subclass_concrete():
    class PartialStorage(Storage):
        def __init__(self):
            self.value = 42

        def close(self):
            pass

    with pytest.raises(TypeError):
        PartialStorage()

def test_abstract_read_raises_not_implemented_error_when_delegated_to_super(
    delegating_storage_class,
):
    storage = delegating_storage_class()
    with pytest.raises(NotImplementedError, match='To be overridden!'):
        storage.read()

def test_abstract_write_raises_not_implemented_error_when_delegated_to_super(
    delegating_storage_class,
):
    storage = delegating_storage_class()
    data = {'_default': {'name': 'John'}}
    with pytest.raises(NotImplementedError, match='To be overridden!'):
        storage.write(data)

def test_base_class_read_and_write_bodies_raise_not_implemented_error():
    # The base class bodies exist purely as documentation/safety nets and must
    # raise when invoked directly with any `self` object.
    with pytest.raises(NotImplementedError):
        Storage.read(object())

    with pytest.raises(NotImplementedError):
        Storage.write(object(), {'_default': {}})

def test_close_is_optional_and_returns_none_by_default(concrete_storage):
    assert concrete_storage.close() is None

def test_base_close_implementation_is_a_noop_for_any_instance():
    assert Storage.close(object()) is None

def test_subclass_may_override_close_to_release_resources():
    class ClosableStorage(Storage):
        def __init__(self):
            self.handle = 'open'

        def read(self):
            return None

        def write(self, data):
            pass

        def close(self):
            self.handle = 'closed'

    storage = ClosableStorage()
    assert storage.handle == 'open'
    storage.close()
    assert storage.handle == 'closed'

def test_read_may_return_none_to_indicat_an_empty_storage(concrete_storage_class):
    storage = concrete_storage_class()
    # Per the contract of the base class, `None` is the documented way of
    # signalling an empty storage.
    assert storage.read() is None

def test_written_state_can_be_read_back_through_the_storage_contract(
    concrete_storage,
):
    data = {
        '_default': {'name': 'John', 'age': 42},
        'users': {'1': {'name': 'Jane'}},
    }
    concrete_storage.write(data)
    assert concrete_storage.read() == data

def test_incomplete_intermediate_class_forces_subclasses_to_implement_write():
    class HalfStorage(Storage):
        def read(self):
            return None

    class FullStorage(HalfStorage):
        def write(self, data):
            pass

    # The intermediate class is still abstract because `write` is unimplemented
    with pytest.raises(TypeError):
        HalfStorage()

    assert FullStorage().read() is None

def test_read_return_annotation_declares_an_optional_mapping_of_tables():
    hints = typing.get_type_hints(Storage.read)
    assert hints['return'] == Optional[Dict[str, Dict[str, Any]]]

def test_write_signature_declares_a_nested_mapping_parameter_returning_none():
    hints = typing.get_type_hints(Storage.write)
    assert hints['data'] == Dict[str, Dict[str, Any]]
    assert hints['return'] is type(None)

def test_memory_storage_implements_the_storage_contract():
    storage = MemoryStorage()
    assert isinstance(storage, Storage)

    # An untouched storage reports an empty state (None or an empty mapping)
    assert not storage.read()

    data = {'_default': {'name': 'John'}}
    storage.write(data)
    assert storage.read() == data

def test_json_storage_implements_the_storage_contract_across_instances(tmp_path):
    path = str(tmp_path / 'db.json')
    storage = JSONStorage(path)
    assert isinstance(storage, Storage)

    # The freshly created file holds no data yet
    assert not storage.read()

    data = {'_default': {'name': 'John'}, 'users': {'1': {'name': 'Jane'}}}
    storage.write(data)
    # `close` is part of the contract and must not raise
    assert storage.close() is None

    # The state survives across storage instances (i.e. it is persisted)
    assert JSONStorage(path).read() == data
