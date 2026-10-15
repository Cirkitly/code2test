import pytest
from tinydb.middlewares import CachingMiddleware

class _FakeStorage:
    """Minimal in-memory Storage implementation used to exercise CachingMiddleware.

    Records call counts and the most recently written payload so tests can
    assert exact interactions with the underlying storage.
    """

    def __init__(self, *args, **kwargs):
        self._store = {"initial": "value"}
        self.read_calls = 0
        self.write_calls = 0
        self.close_calls = 0
        self.last_written = None
        self.init_args = args
        self.init_kwargs = kwargs

    def read(self):
        self.read_calls += 1
        return self._store

    def write(self, data):
        self.write_calls += 1
        self.last_written = data
        self._store = data

    def close(self):
        self.close_calls += 1


@pytest.fixture
def cache_middleware():
    """Return a (middleware, backing_storage) pair ready to use.

    The middleware is constructed and its __call__ is invoked so the wrapped
    storage instance is attached and accessible via ``mw.storage``.
    """
    mw = CachingMiddleware(_FakeStorage)
    mw("path_arg", kw_arg="value")
    return mw, mw.storage

def test_init_starts_with_empty_cache():
    """A fresh CachingMiddleware should have an empty cache and zero counter."""
    mw = CachingMiddleware(_FakeStorage)
    assert mw.cache is None
    assert mw._cache_modified_count == 0

def test_default_write_cache_size_is_one_thousand():
    """WRITE_CACHE_SIZE should be the documented default of 1000."""
    assert CachingMiddleware.WRITE_CACHE_SIZE == 1000

def test_call_forwards_arguments_to_storage_class(cache_middleware):
    """Calling the middleware should instantiate the storage class with provided args."""
    mw, storage = cache_middleware
    assert storage.init_args == ("path_arg",)
    assert storage.init_kwargs == {"kw_arg": "value"}

def test_first_read_populates_cache_from_underlying_storage(cache_middleware):
    """First read with empty cache should load from storage and cache the result."""
    mw, storage = cache_middleware
    result = mw.read()
    assert result == {"initial": "value"}
    assert mw.cache == {"initial": "value"}
    assert storage.read_calls == 1

def test_subsequent_reads_serve_from_cache_without_hitting_storage(cache_middleware):
    """Multiple reads after the first one should be served from cache only."""
    mw, storage = cache_middleware
    mw.read()
    mw.read()
    mw.read()
    assert storage.read_calls == 1

def test_write_caches_data_and_increments_counter_without_flushing(cache_middleware):
    """A single write should cache data and increment the counter, not flush yet."""
    mw, storage = cache_middleware
    mw.write({"k": "v"})
    assert mw.cache == {"k": "v"}
    assert mw._cache_modified_count == 1
    assert storage.write_calls == 0

def test_read_after_write_returns_cached_data_without_reading_storage(cache_middleware):
    """A read following a write should return the cached value without I/O."""
    mw, storage = cache_middleware
    mw.write({"updated": True})
    assert mw.read() == {"updated": True}
    assert storage.read_calls == 0

def test_write_below_threshold_does_not_auto_flush(cache_middleware, monkeypatch):
    """Writes below WRITE_CACHE_SIZE should be buffered and not flushed automatically."""
    monkeypatch.setattr(CachingMiddleware, "WRITE_CACHE_SIZE", 5)
    mw, storage = cache_middleware
    for i in range(4):
        mw.write({"i": i})
    assert storage.write_calls == 0
    assert mw._cache_modified_count == 4

def test_write_at_threshold_triggers_auto_flush(cache_middleware, monkeypatch):
    """Reaching WRITE_CACHE_SIZE writes should trigger an automatic flush."""
    monkeypatch.setattr(CachingMiddleware, "WRITE_CACHE_SIZE", 3)
    mw, storage = cache_middleware
    mw.write({"i": 0})  # count -> 1
    mw.write({"i": 1})  # count -> 2
    mw.write({"i": 2})  # count -> 3, triggers flush
    assert storage.write_calls == 1
    assert storage.last_written == {"i": 2}
    assert mw._cache_modified_count == 0

def test_counter_resets_after_auto_flush(cache_middleware, monkeypatch):
    """The pending-write counter should reset to zero after an auto-flush."""
    monkeypatch.setattr(CachingMiddleware, "WRITE_CACHE_SIZE", 2)
    mw, storage = cache_middleware
    mw.write({"a": 1})  # count -> 1
    mw.write({"a": 2})  # count -> 2, triggers flush
    assert storage.write_calls == 1
    assert mw._cache_modified_count == 0
    # A new write after the flush should start counting again
    mw.write({"a": 3})
    assert mw._cache_modified_count == 1
    assert storage.write_calls == 1  # not yet flushed again

def test_explicit_flush_writes_pending_data_to_storage(cache_middleware):
    """flush() should write pending data to storage and reset the counter."""
    mw, storage = cache_middleware
    mw.write({"new": "data"})
    mw.flush()
    assert storage.write_calls == 1
    assert storage.last_written == {"new": "data"}
    assert mw._cache_modified_count == 0

def test_flush_is_noop_when_no_pending_writes(cache_middleware):
    """flush() should not touch storage when the counter is zero."""
    mw, storage = cache_middleware
    mw.flush()
    assert storage.write_calls == 0

def test_second_flush_without_new_writes_does_not_write_again(cache_middleware):
    """A second flush with no new writes should not produce extra storage writes."""
    mw, storage = cache_middleware
    mw.write({"k": "v"})
    mw.flush()
    mw.flush()
    assert storage.write_calls == 1

def test_close_flushes_pending_data_then_closes_underlying_storage(cache_middleware):
    """close() should flush pending writes before closing the storage."""
    mw, storage = cache_middleware
    mw.write({"pending": True})
    mw.close()
    assert storage.write_calls == 1
    assert storage.last_written == {"pending": True}
    assert storage.close_calls == 1

def test_close_without_pending_data_only_closes_storage(cache_middleware):
    """close() should not write to storage if there is nothing pending."""
    mw, storage = cache_middleware
    mw.close()
    assert storage.write_calls == 0
    assert storage.close_calls == 1
