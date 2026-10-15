import pytest
from tinydb import Storage
from tinydb.middlewares import Middleware

@pytest.fixture
def dummy_storage_cls():
    """A minimal concrete Storage implementation used as the wrapped 'real' storage."""

    class DummyStorage(Storage):
        """Records the arguments it was constructed with for later assertions."""

        def __init__(self, *args, **kwargs):
            super().__init__()
            self.init_args = args
            self.init_kwargs = kwargs
            self.read_data = None
            self.write_calls = []
            self.closed = False

        def read(self):
            return self.read_data

        def write(self, data):
            self.write_calls.append(data)

        def close(self):
            self.closed = True

    return DummyStorage


@pytest.fixture
def dummy_storage_instance(dummy_storage_cls):
    """An already-created DummyStorage instance (not the class)."""
    return dummy_storage_cls()

def test_constructor_stores_storage_class_and_initializes_storage_to_none(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)

    assert middleware._storage_cls is dummy_storage_cls
    assert middleware.storage is None

def test_call_creates_storage_instance_from_wrapped_storage_class(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)

    middleware()

    assert isinstance(middleware.storage, dummy_storage_cls)

def test_call_returns_self_so_it_can_replace_the_storage_class(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)

    result = middleware()

    assert result is middleware

def test_call_forwards_positional_and_keyword_arguments_to_storage(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)

    middleware('some-positional', 42, mode='r+', encoding='utf-8')

    assert middleware.storage.init_args == ('some-positional', 42)
    assert middleware.storage.init_kwargs == {'mode': 'r+', 'encoding': 'utf-8'}

def test_call_without_arguments_creates_storage_with_no_arguments(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)

    middleware()

    assert middleware.storage.init_args == ()
    assert middleware.storage.init_kwargs == {}

def test_unknown_attributes_are_forwarded_to_underlying_storage(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)
    middleware()

    middleware.custom_attribute = 'hello'
    middleware.read_data = {'items': []}

    assert middleware.custom_attribute == 'hello'
    assert middleware.read_data == {'items': []}

def test_read_method_is_forwarded_to_underlying_storage(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)
    middleware()
    middleware.storage.read_data = {'value': 1}

    assert middleware.read() == {'value': 1}

def test_write_method_is_forwarded_to_underlying_storage(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)
    middleware()

    middleware.write({'a': 1})

    assert middleware.storage.write_calls == [{'a': 1}]

def test_explicitly_set_attributes_shadow_underlying_storage_attributes(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)
    middleware()

    assert middleware.storage is middleware.storage

    middleware._local_marker = 'own-attribute'
    assert middleware._local_marker == 'own-attribute'

def test_calling_twice_reinitializes_the_underlying_storage(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)

    middleware('first')
    first_storage = middleware.storage

    middleware('second')

    assert middleware.storage is not first_storage
    assert middleware.storage.init_args == ('second',)

def test_nested_middlewares_chain_to_the_real_storage_class(dummy_storage_cls):
    inner = Middleware(dummy_storage_cls)
    outer = Middleware(inner)

    result = outer('chained-arg')

    assert result is outer
    assert outer.storage is inner
    assert isinstance(outer.storage.storage, dummy_storage_cls)
    assert outer.storage.storage.init_args == ('chained-arg',)

def test_middleware_is_usable_as_a_storage_class_argument(dummy_storage_cls):
    # Simulates TinyDB(storage=Middleware(StorageClass)) followed by storage(...)
    storage_like = Middleware(dummy_storage_cls)
    instance = storage_like('db-path', flag=True)

    instance.write({'k': 'v'})

    assert instance is storage_like
    assert instance.storage.init_kwargs == {'flag': True}
    assert instance.read is not None
    assert instance.storage.write_calls == [{'k': 'v'}]

def test_attribute_access_before_call_raises_attribute_error_on_none_storage(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)

    with pytest.raises(AttributeError):
        middleware.some_unknown_attribute

def test_unknown_attribute_not_on_storage_raises_attribute_error(dummy_storage_cls):
    middleware = Middleware(dummy_storage_cls)
    middleware()

    with pytest.raises(AttributeError):
        middleware.definitely_not_defined_anywhere

def test_call_propagates_storage_constructor_errors(dummy_storage_cls):
    class ExplodingStorage(dummy_storage_cls):
        def __init__(self, *args, **kwargs):
            raise RuntimeError('storage init failed')

    middleware = Middleware(ExplodingStorage)

    with pytest.raises(RuntimeError, match='storage init failed'):
        middleware()

def test_call_with_wrong_arguments_raises_type_error():
    class NoArgsStorage(Storage):
        def __init__(self):
            super().__init__()

        def read(self):
            return None

        def write(self, data):
            pass

    middleware = Middleware(NoArgsStorage)

    with pytest.raises(TypeError):
        middleware('unexpected-positional-argument')

def test_constructor_requires_a_storage_class_argument():
    with pytest.raises(TypeError):
        Middleware()

def test_storage_class_is_stored_as_given_so_subclasses_can_reuse_it(dummy_storage_cls):
    class MyMiddleware(Middleware):
        pass

    middleware = MyMiddleware(dummy_storage_cls)

    assert isinstance(middleware, Middleware)
    assert middleware._storage_cls is dummy_storage_cls
