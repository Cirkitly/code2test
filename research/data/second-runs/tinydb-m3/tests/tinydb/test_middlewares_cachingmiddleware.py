import pytest
from tinydb.middlewares import CachingMiddleware

class FakeStorage:
    """A minimal in-memory storage stand-in that records its method calls."""
    def __init__(self, path=None, **kwargs):
        self.path = path
        self._data = None
        self.read_count = 0
        self.write_count = 0
        self.close_count = 0
        self.write_history = []
        self.read_history = []

    def read(self):
        self.read_count += 1
        if self._data is None:
            return {}
        return self._data

    def write(self, data):
        self.write_count += 1
        self.write_history.append(data)
        self._data = data

    def close(self):
        self.close_count += 1


class FastFlushMiddleware(CachingMiddleware):
    """CachingMiddleware subclass with a tiny WRITE_CACHE_SIZE for threshold tests."""
    WRITE_CACHE_SIZE = 3


@pytest.fixture
def storage_class():
    """Provide the FakeStorage class to tests that need to construct a middleware."""
    return FakeStorage


@pytest.fixture
def middleware(storage_class):
    """Provide a fully initialized CachingMiddleware wrapping a FakeStorage."""
    return CachingMiddleware(storage_class)()


@pytest.fixture
def fast_middleware(storage_class):
    """Provide a CachingMiddleware subclass with WRITE_CACHE_SIZE == 3 for threshold tests."""
    return FastFlushMiddleware(storage_class)()

def test_write_cache_size_constant_is_1000():
    """The WRITE_CACHE_SIZE class constant should default to 1000."""
    assert CachingMiddleware.WRITE_CACHE_SIZE == 1000

def test_cache_is_none_when_newly_constructed(middleware):
    """A freshly constructed CachingMiddleware must start with cache == None."""
    assert middleware.cache is None

def test_modified_count_is_zero_when_newly_constructed(middleware):
    """A freshly constructed CachingMiddleware must start with _cache_modified_count == 0."""
    assert middleware._cache_modified_count == 0

def test_first_read_populates_cache_and_returns_storage_data(middleware):
    """The first read() call fetches from storage and stores the result in the cache."""
    middleware.storage._data = {"k": "v"}

    result = middleware.read()

    assert result == {"k": "v"}
    assert middleware.cache == {"k": "v"}

def test_subsequent_reads_use_cache_without_calling_storage(middleware):
    """Reads after the first one should hit the cache, not the underlying storage."""
    middleware.storage._data = {"x": 1}
    middleware.read()
    middleware.read()
    middleware.read()

    assert middleware.storage.read_count == 1

def test_read_returns_latest_cached_data_after_write(middleware):
    """Writes should update the cache so subsequent reads reflect the latest value."""
    middleware.write({"n": 1})
    middleware.write({"n": 2})

    result = middleware.read()

    assert result == {"n": 2}
    assert middleware.storage.read_count == 0

def test_write_stores_data_in_cache(middleware):
    """write() should place the provided data into the cache."""
    data = {"hello": "world"}

    middleware.write(data)

    assert middleware.cache == data

def test_write_increments_modified_count_by_one(middleware):
    """Each write() should bump the pending-write counter by exactly one."""
    assert middleware._cache_modified_count == 0

    middleware.write({})
    assert middleware._cache_modified_count == 1

    middleware.write({})
    assert middleware._cache_modified_count == 2

def test_writes_below_threshold_do_not_flush_to_storage(middleware):
    """A small number of writes (well below WRITE_CACHE_SIZE) should not trigger storage writes."""
    for _ in range(5):
        middleware.write({})

    assert middleware.storage.write_count == 0
    assert middleware._cache_modified_count == 5

def test_writes_at_threshold_trigger_exactly_one_flush(fast_middleware):
    """Writing exactly WRITE_CACHE_SIZE times should trigger exactly one auto-flush."""
    for _ in range(fast_middleware.WRITE_CACHE_SIZE):
        fast_middleware.write({})

    assert fast_middleware.storage.write_count == 1

def test_writes_spanning_multiple_threshold_cycles_trigger_repeated_flushes(fast_middleware):
    """Multiple WRITE_CACHE_SIZE cycles should produce multiple auto-flushes and reset the counter."""
    for _ in range(2 * fast_middleware.WRITE_CACHE_SIZE):
        fast_middleware.write({})

    assert fast_middleware.storage.write_count == 2
    assert fast_middleware._cache_modified_count == 0

def test_flush_writes_pending_cache_through_to_storage(middleware):
    """flush() should write the cached data through to the underlying storage."""
    middleware.write({"a": 1, "b": 2})

    middleware.flush()

    assert middleware.storage.write_count == 1
    assert middleware.storage.write_history[-1] == {"a": 1, "b": 2}

def test_flush_with_no_pending_writes_is_a_noop(middleware):
    """flush() should not call storage.write() when the pending-write counter is zero."""
    middleware.flush()
    middleware.flush()

    assert middleware.storage.write_count == 0

def test_flush_resets_pending_write_counter(middleware):
    """flush() should reset _cache_modified_count to zero after a successful flush."""
    middleware.write({})
    middleware.write({})
    middleware.flush()

    assert middleware._cache_modified_count == 0

def test_close_flushes_pending_writes_before_closing(middleware):
    """close() should flush pending writes and persist the latest cached value to storage."""
    middleware.write({"pending": True})
    middleware.write({"more": "data"})

    middleware.close()

    assert middleware.storage.write_count == 1
    assert middleware.storage.write_history[-1] == {"more": "data"}

def test_close_propagates_to_underlying_storage(middleware):
    """close() should call storage.close() exactly once."""
    middleware.close()

    assert middleware.storage.close_count == 1
