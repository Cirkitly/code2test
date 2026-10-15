import pytest
from tinydb.middlewares import Middleware
from tinydb import Storage

class FakeStorage:
    """A fake storage class used to verify Middleware forwarding behaviour."""

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs

    def custom_method(self):
        return "from-storage"

def test_init_stores_storage_class_for_later_use():
    """Middleware remembers the storage class passed to __init__."""
    m = Middleware(FakeStorage)
    assert m._storage_cls is FakeStorage

def test_init_storage_defaults_to_none():
    """Before __call__ runs, the storage attribute is None."""
    m = Middleware(FakeStorage)
    assert m.storage is None

def test_init_does_not_instantiate_storage():
    """The storage class constructor is not invoked by __init__ alone."""
    init_calls = []

    class CountingStorage:
        def __init__(self, *args, **kwargs):
            init_calls.append((args, kwargs))

    Middleware(CountingStorage)
    assert init_calls == []

def test_call_creates_storage_instance():
    """__call__ instantiates the underlying storage class and stores the result."""
    m = Middleware(FakeStorage)
    m()
    assert isinstance(m.storage, FakeStorage)

def test_call_returns_middleware_instance():
    """__call__ returns the middleware itself so it can stand in for a class."""
    m = Middleware(FakeStorage)
    assert m() is m

def test_call_forwards_positional_arguments():
    """Positional arguments passed to __call__ reach the storage constructor."""
    m = Middleware(FakeStorage)
    m(1, 2, 3)
    assert m.storage.init_args == (1, 2, 3)

def test_call_forwards_keyword_arguments():
    """Keyword arguments passed to __call__ reach the storage constructor."""
    m = Middleware(FakeStorage)
    m(foo="bar", baz=42)
    assert m.storage.init_kwargs == {"foo": "bar", "baz": 42}

def test_call_forwards_both_positional_and_keyword_arguments():
    """Both positional and keyword arguments are forwarded to the storage class."""
    m = Middleware(FakeStorage)
    m("a", "b", key="value")
    assert m.storage.init_args == ("a", "b")
    assert m.storage.init_kwargs == {"key": "value"}

def test_getattr_delegates_to_storage():
    """Unknown attributes are transparently forwarded to the wrapped storage."""
    m = Middleware(FakeStorage)
    m()
    assert m.custom_method() == "from-storage"

def test_getattr_raises_when_storage_is_none():
    """Forwarding an unknown attribute before __call__ raises AttributeError."""
    m = Middleware(FakeStorage)
    with pytest.raises(AttributeError):
        m.unknown_attribute

def test_getattr_raises_when_storage_lacks_attribute():
    """Forwarding to a storage that does not define the attribute raises AttributeError."""
    m = Middleware(FakeStorage)
    m()
    with pytest.raises(AttributeError):
        m.unknown_attribute

def test_nested_middlewares_form_chain():
    """Wrapping a Middleware in another Middleware produces a chained configuration."""
    inner = Middleware(FakeStorage)
    outer = Middleware(inner)
    outer()
    assert outer.storage is inner
    assert isinstance(inner.storage, FakeStorage)
