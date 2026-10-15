import pytest
from abc import ABC
from tinydb.storages import Storage

@pytest.fixture
def concrete_storage_class():
    """
    Provide a fully-implemented concrete Storage subclass that overrides
    both abstract methods. This fixture lets other tests exercise the
    happy path (instantiation, default close(), etc.) without having to
    redefine the subclass in every test.
    """

    class ConcreteStorage(Storage):
        def read(self):
            return None

        def write(self, data):
            return None

    return ConcreteStorage

import pytest
from tinydb.storages import Storage


def test_storage_cannot_be_instantiated_directly():
    """
    The abstract Storage class itself cannot be instantiated.
    Because it declares abstract methods (read/write) and uses ABCMeta,
    Python refuses instantiation by raising TypeError.
    """
    with pytest.raises(TypeError):
        Storage()


import pytest
from abc import ABC
from tinydb.storages import Storage


def test_storage_inherits_from_abc():
    """
    Storage is declared as a subclass of ABC in the source. Confirming
    this subclass relationship verifies that it uses ABCMeta and the
    standard abstract-method enforcement.
    """
    assert issubclass(Storage, ABC)


import pytest
from tinydb.storages import Storage


def test_storage_declares_read_and_write_as_abstract_methods():
    """
    The __abstractmethods__ frozenset exposes the names of methods
    that subclasses must override. Per the source code, read() and
    write() are decorated with @abstractmethod and therefore MUST be
    present in this frozenset.
    """
    abstract_methods = Storage.__abstractmethods__
    assert 'read' in abstract_methods
    assert 'write' in abstract_methods


import pytest
from tinydb.storages import Storage


def test_storage_close_is_not_abstract():
    """
    Although close() exists on Storage, it is intentionally a regular
    concrete method (no @abstractmethod decorator in the source). It
    must therefore NOT appear in __abstractmethods__, meaning subclasses
    are allowed to inherit the default no-op implementation.
    """
    assert 'close' not in Storage.__abstractmethods__


import pytest
from tinydb.storages import Storage


def test_subclass_missing_read_method_cannot_be_instantiated():
    """
    A subclass that overrides write() but not read() still has an
    unimplemented abstract method. Python must refuse instantiation
    with TypeError, exactly as if no methods were overridden at all.
    """
    class IncompleteStorage(Storage):
        def write(self, data):
            return None

    with pytest.raises(TypeError):
        IncompleteStorage()


import pytest
from tinydb.storages import Storage


def test_subclass_missing_write_method_cannot_be_instantiated():
    """
    A subclass that overrides read() but not write() still has an
    unimplemented abstract method. Python must refuse instantiation
    with TypeError.
    """
    class IncompleteStorage(Storage):
        def read(self):
            return None

    with pytest.raises(TypeError):
        IncompleteStorage()


import pytest
from tinydb.storages import Storage


def test_subclass_implementing_both_abstract_methods_can_be_instantiated(concrete_storage_class):
    """
    The primary happy path: a subclass that implements both abstract
    methods (read and write) satisfies the abstract contract and can be
    instantiated without error. The resulting instance is-a Storage.
    """
    instance = concrete_storage_class()
    assert isinstance(instance, Storage)


import pytest
from tinydb.storages import Storage


def test_multilevel_subclass_chain_eventually_implements_methods():
    """
    Edge case for inheritance: an intermediate class that inherits from
    Storage but adds nothing concrete remains abstract and cannot be
    instantiated. Only the subclass at the bottom of the chain, which
    actually provides the read() and write() implementations, becomes
    instantiable.
    """
    class IntermediateStorage(Storage):
        pass

    class FinalStorage(IntermediateStorage):
        def read(self):
            return None

        def write(self, data):
            return None

    # Intermediate layer is still abstract.
    with pytest.raises(TypeError):
        IntermediateStorage()

    # The leaf class implementing both abstract methods IS instantiable.
    instance = FinalStorage()
    assert isinstance(instance, Storage)


import pytest
from tinydb.storages import Storage


def test_default_close_method_returns_none(concrete_storage_class):
    """
    Per the source, the default close() body is just ``pass``, which
    implicitly returns None. Verify that calling the inherited close()
    on a concrete subclass returns None.
    """
    instance = concrete_storage_class()
    assert instance.close() is None


import pytest
from tinydb.storages import Storage


def test_default_close_method_does_not_raise(concrete_storage_class):
    """
    Per the source, close() is a simple ``pass`` and must not raise.
    This guards against accidental changes (e.g. someone inserting
    cleanup code that raises when resources are already closed).
    """
    instance = concrete_storage_class()
    # No assertion needed; if close() raised, the test would fail.
    instance.close()
    instance.close()  # must also be safe to call repeatedly


import pytest
from tinydb.storages import Storage


def test_storage_read_method_body_raises_not_implemented_error():
    """
    The source defines read() with a body that raises NotImplementedError
    with the message 'To be overridden!'. This guarantees that calling
    the unimplemented parent method surfaces a clear, expected error.

    We reach the parent body by overriding read() in a concrete subclass
    and explicitly delegating to ``Storage.read(self)`` (Python allows
    calling abstract methods directly on the class; ABC only enforces
    the contract at instantiation time).
    """
    class ConcreteStorage(Storage):
        def read(self):
            return Storage.read(self)

        def write(self, data):
            return None

    instance = ConcreteStorage()
    with pytest.raises(NotImplementedError):
        instance.read()


import pytest
from tinydb.storages import Storage


def test_storage_write_method_body_raises_not_implemented_error():
    """
    Mirror of the read() check for write(): the source defines write()
    with a body that raises NotImplementedError('To be overridden!').
    Overriding write() in a concrete subclass and delegating to the
    parent body surfaces that error, confirming the sentinel behavior.
    """
    class ConcreteStorage(Storage):
        def read(self):
            return None

        def write(self, data):
            return Storage.write(self, data)

    instance = ConcreteStorage()
    with pytest.raises(NotImplementedError):
        instance.write({})

