import pytest
from tinydb.middlewares import Middleware

@pytest.fixture
def DummyStorage():
    '''A minimal stand-in for a real TinyDB storage class.'''
    class DummyStorage:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.value = 42
            self.__custom__ = 'custom'

        def describe(self):
            return 'DummyStorage'

        def __len__(self):
            return 3

    return DummyStorage

@pytest.fixture
def NoArgStorage():
    '''A storage class that accepts no constructor arguments.'''
    class NoArgStorage:
        def __init__(self):
            self.ready = True

    return NoArgStorage

@pytest.fixture
def BadStorage():
    '''A storage class whose constructor always fails.'''
    class BadStorage:
        def __init__(self, *args, **kwargs):
            raise ValueError('storage constructor failed')

    return BadStorage

def test_init_stores_storage_class_and_initializes_storage_to_none():
    """A fresh Middleware keeps the class (not an instance) and has storage=None."""
    middleware = Middleware(DummyStorage)

    assert middleware._storage_cls is DummyStorage
    assert middleware.storage is None
    assert isinstance(middleware, Middleware)

def test_call_creates_storage_instance_and_returns_itself(DummyStorage):
    """Calling the middleware builds the real storage and returns the middleware."""
    middleware = Middleware(DummyStorage)

    result = middleware()

    assert result is middleware
    assert isinstance(middleware.storage, DummyStorage)
    assert middleware.storage.args == ()
    assert middleware.storage.kwargs == {}

def test_call_forwards_positional_arguments_to_storage_class(DummyStorage):
    """Positional arguments given to the middleware reach the wrapped storage class."""
    middleware = Middleware(DummyStorage)

    middleware('first', 'second')

    assert middleware.storage.args == ('first', 'second')
    assert middleware.storage.kwargs == {}

def test_call_forwards_keyword_arguments_to_storage_class(DummyStorage):
    """Keyword arguments given to the middleware reach the wrapped storage class."""
    middleware = Middleware(DummyStorage)

    middleware(path='/tmp/db.json', mode='r+')

    assert middleware.storage.args == ()
    assert middleware.storage.kwargs == {'path': '/tmp/db.json', 'mode': 'r+'}

def test_call_forwards_mixed_positional_and_keyword_arguments(DummyStorage):
    """Both args and kwargs are forwarded together, mimicking TinyDB(storage=...) usage."""
    middleware = Middleware(DummyStorage)

    middleware('pos1', 'pos2', path='/tmp/db.json')

    assert middleware.storage.args == ('pos1', 'pos2')
    assert middleware.storage.kwargs == {'path': '/tmp/db.json'}

def test_getattr_forwards_unknown_attributes_to_underlying_storage(DummyStorage):
    """Unknown attributes resolve against the wrapped storage instance."""
    middleware = Middleware(DummyStorage)
    middleware()

    assert middleware.value == 42
    assert middleware.describe() == 'DummyStorage'

def test_getattr_forwards_dunder_attributes_excluding_call(DummyStorage):
    """Dunder attributes (except those handled by Python itself) are forwarded to storage."""
    middleware = Middleware(DummyStorage)
    middleware()

    assert middleware.__custom__ == 'custom'
    assert middleware.__len__() == 3

def test_own_attributes_are_not_forwarded_to_storage(DummyStorage):
    """Defined attributes shadow storage attributes of the same name."""
    middleware = Middleware(DummyStorage)
    middleware()

    # The middleware's own attributes win over the storage's attributes
    assert middleware._storage_cls is DummyStorage
    assert isinstance(middleware.storage, DummyStorage)
    assert middleware.storage is not middleware

def test_accessing_unknown_attribute_before_call_raises_attribute_error():
    """Using the middleware as storage before it was called fails loudly."""
    middleware = Middleware(DummyStorage)

    with pytest.raises(AttributeError):
        middleware.value

def test_accessing_missing_attribute_on_storage_raises_attribute_error(DummyStorage):
    """Unknown-on-middleware and unknown-on-storage both raise AttributeError."""
    middleware = Middleware(DummyStorage)
    middleware()

    with pytest.raises(AttributeError):
        middleware.does_not_exist_anywhere

def test_getattr_raises_key_error_when_storage_instance_attribute_is_deleted(DummyStorage):
    """Removing the 'storage' entry from __dict__ makes __getattr__ raise KeyError."""
    middleware = Middleware(DummyStorage)
    middleware()
    del middleware.__dict__['storage']

    with pytest.raises(KeyError):
        middleware.value

def test_errors_from_storage_constructor_propagate_on_call(BadStorage):
    """Constructor errors of the wrapped storage bubble up through __call__."""
    middleware = Middleware(BadStorage)

    with pytest.raises(ValueError):
        middleware()

def test_nested_middlewares_are_initialized_in_order_and_innermost_storage_is_used(DummyStorage):
    """Nested Middlewares chain their __call__ methods down to the real storage."""
    inner = Middleware(DummyStorage)
    outer = Middleware(inner)

    result = outer('pos', flag=True)

    # The outermost middleware returns itself
    assert result is outer
    # The inner middleware was initialized by the outer one
    assert inner.storage is not None
    assert isinstance(inner.storage, DummyStorage)
    # Arguments were forwarded through the whole chain
    assert inner.storage.args == ('pos',)
    assert inner.storage.kwargs == {'flag': True}
    # Attribute forwarding now ends at the real storage
    assert outer.value == 42

def test_calling_middleware_twice_replaces_the_storage_instance(DummyStorage):
    """A second __call__ overwrites self.storage with a fresh storage instance."""
    middleware = Middleware(DummyStorage)

    middleware('/first')
    first_storage = middleware.storage

    middleware('/second')
    second_storage = middleware.storage

    assert first_storage is not second_storage
    assert second_storage.args == ('/second',)
    assert middleware.value == 42

def test_middleware_can_be_passed_as_storage_class_without_passing_instance(DummyStorage):
    """Typical TinyDB(storage=Middleware(StorageClass)) usage works end to end."""
    middleware = Middleware(DummyStorage)

    class TinyDBLike:
        def __init__(self, *args, storage=None, **kwargs):
            self.storage = storage(*args, **kwargs)

    db = TinyDBLike('/tmp/db.json', storage=middleware)

    assert db.storage is middleware
    assert isinstance(middleware.storage, DummyStorage)
    assert middleware.storage.args == ('/tmp/db.json',)

def test_call_accepts_no_arguments_at_all(NoArgStorage):
    """Calling the middleware without arguments still yields a storage instance."""
    middleware = Middleware(NoArgStorage)

    result = middleware()

    assert result is middleware
    assert isinstance(middleware.storage, NoArgStorage)
