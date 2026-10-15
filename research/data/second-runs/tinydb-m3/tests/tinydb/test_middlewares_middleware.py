import pytest
from tinydb.middlewares import Middleware

@pytest.fixture
def fake_storage_cls():
    """Provides a minimal Storage-like class used to exercise the Middleware base class.

    The class accepts an optional positional ``path`` and arbitrary keyword
    arguments so we can verify how the middleware forwards ``*args``/``**kwargs``.
    It also exposes a plain attribute and a pair of methods (``read``/``write``)
    to verify ``__getattr__`` transparency.
    """
    class FakeStorage:
        def __init__(self, path=None, **kwargs):
            self.path = path
            self.received_kwargs = kwargs
            self.custom_attr = "fake_value"
            self._data = {}
            self._closed = False

        def read(self):
            return self._data

        def write(self, data):
            self._data = data

        def close(self):
            self._closed = True

    return FakeStorage

def test_init_stores_storage_cls(fake_storage_cls):
    """``Middleware(storage_cls)`` keeps ``storage_cls`` on ``self._storage_cls``."""
    middleware = Middleware(fake_storage_cls)
    assert middleware._storage_cls is fake_storage_cls

def test_init_storage_is_none_before_call(fake_storage_cls):
    """After construction but before ``__call__``, ``self.storage`` is None."""
    middleware = Middleware(fake_storage_cls)
    assert middleware.storage is None

def test_call_creates_storage_instance(fake_storage_cls):
    """Calling the middleware constructs an instance of ``storage_cls``."""
    middleware = Middleware(fake_storage_cls)
    middleware()
    assert isinstance(middleware.storage, fake_storage_cls)

def test_call_returns_middleware_instance(fake_storage_cls):
    """``__call__`` returns the middleware itself, not the freshly-built storage."""
    middleware = Middleware(fake_storage_cls)
    result = middleware()
    assert result is middleware
    assert result is not middleware.storage

def test_call_forwards_positional_args_to_storage(fake_storage_cls):
    """Positional arguments given to ``__call__`` are forwarded to ``storage_cls``."""
    middleware = Middleware(fake_storage_cls)
    middleware("some/path")
    assert middleware.storage.path == "some/path"

def test_call_forwards_keyword_args_to_storage(fake_storage_cls):
    """Keyword arguments given to ``__call__`` are forwarded to ``storage_cls``."""
    middleware = Middleware(fake_storage_cls)
    middleware(path="some/path", extra="info")
    assert middleware.storage.path == "some/path"
    assert middleware.storage.received_kwargs == {"extra": "info"}

def test_call_forwards_mixed_args_to_storage(fake_storage_cls):
    """A mix of positional and keyword args reach ``storage_cls`` correctly."""
    middleware = Middleware(fake_storage_cls)
    middleware("positional/path", extra="info")
    assert middleware.storage.path == "positional/path"
    assert middleware.storage.received_kwargs == {"extra": "info"}

def test_chained_construction_pattern(fake_storage_cls):
    """The typical ``Middleware(cls)(args)`` pattern yields a usable middleware."""
    instance = Middleware(fake_storage_cls)("path")
    assert isinstance(instance, Middleware)
    assert isinstance(instance.storage, fake_storage_cls)
    assert instance.storage.path == "path"

def test_getattr_forwards_attribute_access_to_storage(fake_storage_cls):
    """An attribute defined on storage is reachable through the middleware."""
    middleware = Middleware(fake_storage_cls)
    middleware()
    # ``custom_attr`` exists on FakeStorage only, not on Middleware.
    assert middleware.custom_attr == "fake_value"

def test_getattr_forwards_method_calls_to_storage(fake_storage_cls):
    """Calling a method through the middleware invokes it on storage."""
    middleware = Middleware(fake_storage_cls)
    middleware()
    middleware.write({"foo": "bar"})
    assert middleware.read() == {"foo": "bar"}

def test_getattr_raises_for_unknown_attribute_after_call(fake_storage_cls):
    """Forwarding raises ``AttributeError`` when the storage has no such attribute."""
    middleware = Middleware(fake_storage_cls)
    middleware()
    with pytest.raises(AttributeError):
        _ = middleware.does_not_exist_anywhere

def test_getattr_before_call_raises_attribute_error(fake_storage_cls):
    """Before ``__call__``, ``self.storage`` is None so forwarded lookup fails.

    The middleware's ``__getattr__`` forwards to ``self.__dict__['storage']``
    which is ``None`` at this point, so any forwarded attribute raises
    ``AttributeError``.
    """
    middleware = Middleware(fake_storage_cls)
    with pytest.raises(AttributeError):
        _ = middleware.anything

def test_call_propagates_storage_construction_errors():
    """Errors raised by ``storage_cls.__init__`` propagate out of ``__call__``."""
    class ExplodingStorage:
        def __init__(self):
            raise ValueError("boom")

    middleware = Middleware(ExplodingStorage)
    with pytest.raises(ValueError, match="boom"):
        middleware()

def test_call_with_non_callable_storage_cls_raises_type_error():
    """Calling with a non-callable ``storage_cls`` raises ``TypeError``.

    ``__init__`` does not validate the argument, so the failure surfaces only
    when ``__call__`` actually tries to instantiate it.
    """
    middleware = Middleware(42)
    with pytest.raises(TypeError):
        middleware()

def test_nested_middleware_with_callable_instance(fake_storage_cls):
    """An inner middleware instance can be passed as ``storage_cls`` of an outer one.

    This is the documented mechanism for nested middlewares: calling the outer
    middleware invokes ``__call__`` on the inner one, which then builds the real
    storage.
    """
    inner = Middleware(fake_storage_cls)
    outer = Middleware(inner)
    outer("nested/path")
    # After the call, outer.storage is the inner middleware,
    # and inner.storage is the FakeStorage instance.
    assert outer.storage is inner
    assert isinstance(outer.storage.storage, fake_storage_cls)
    assert outer.storage.storage.path == "nested/path"
