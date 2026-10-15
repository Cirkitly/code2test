import pytest
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage, Storage

class MemoryStorage(Storage):
    """An in-memory storage that records how often it was accessed."""

    def __init__(self):
        super().__init__()
        self.memory = None
        self.read_count = 0
        self.write_count = 0
        self.written = []
        self.close_count = 0

    def read(self):
        self.read_count += 1
        return self.memory

    def write(self, data):
        self.write_count += 1
        self.written.append(data)
        self.memory = data

    def close(self):
        self.close_count += 1


class FlakyReadStorage(MemoryStorage):
    """A storage whose read() fails a given number of times."""

    def __init__(self, failures=1):
        super().__init__()
        self.failures = failures

    def read(self):
        self.read_count += 1
        if self.failures > 0:
            self.failures -= 1
            raise OSError('reading from the storage failed')
        return self.memory


class BrokenWriteStorage(MemoryStorage):
    """A storage whose write() always fails."""

    def write(self, data):
        self.write_count += 1
        raise OSError('writing to the storage failed')


def make_middleware(storage_cls):
    """Build a CachingMiddleware together with the storage it delegates to.

    CachingMiddleware is constructed from the storage *class* only, so the
    storage instance the middleware reads from / writes to has to be created
    separately.
    """
    middleware = CachingMiddleware(storage_cls)
    middleware.storage = storage_cls()
    return middleware


@pytest.fixture
def middleware():
    """A CachingMiddleware wrapping a fresh MemoryStorage instance."""
    return make_middleware(MemoryStorage)


@pytest.fixture
def storage(middleware):
    """The storage instance the middleware under test reads from and writes to."""
    return middleware.storage

def test_write_cache_size_default_is_1000():
    """The documented default number of cached writes is 1000."""
    assert CachingMiddleware.WRITE_CACHE_SIZE == 1000


def test_first_read_delegates_to_the_storage(middleware, storage):
    storage.memory = {'_default': {'1': {'int': 1}}}

    result = middleware.read()

    assert result == {'_default': {'1': {'int': 1}}}
    assert storage.read_count == 1


def test_second_read_is_served_from_the_cache(middleware, storage):
    storage.memory = {'_default': {'1': {'int': 1}}}

    first = middleware.read()
    second = middleware.read()

    assert first == second
    assert storage.read_count == 1


def test_cached_read_ignores_later_storage_changes(middleware, storage):
    storage.memory = {'_default': {'1': {'int': 1}}}
    assert middleware.read() == {'_default': {'1': {'int': 1}}}

    storage.memory = {'_default': {'1': {'int': 999}}}

    assert middleware.read() == {'_default': {'1': {'int': 1}}}


def test_read_on_empty_storage_returns_none(middleware, storage):
    assert storage.memory is None

    assert middleware.read() is None
    assert storage.read_count == 1


def test_none_is_not_retained_as_a_cache_entry(middleware, storage):
    assert middleware.read() is None
    assert storage.read_count == 1

    assert middleware.read() is None
    assert storage.read_count == 2

    assert middleware.read() is None
    assert storage.read_count == 3


def test_write_only_updates_the_cache(middleware, storage):
    data = {'_default': {'1': {'int': 1}}}

    middleware.write(data)

    assert storage.write_count == 0
    assert storage.written == []
    assert middleware.cache is data


def test_written_data_is_read_from_the_cache_without_reading_storage(middleware, storage):
    data = {'_default': {'1': {'int': 1}}}

    middleware.write(data)
    result = middleware.read()

    assert result == data
    assert storage.read_count == 0
    assert storage.write_count == 0


def test_writes_below_the_default_cache_size_are_not_persisted(middleware, storage):
    for index in range(CachingMiddleware.WRITE_CACHE_SIZE - 1):
        middleware.write({'i': index})

    assert storage.write_count == 0
    assert storage.written == []
    assert storage.read_count == 0


def test_reaching_the_default_cache_size_flushes_once(middleware, storage):
    for index in range(CachingMiddleware.WRITE_CACHE_SIZE):
        middleware.write({'i': index})

    assert storage.write_count == 1
    assert storage.written == [{'i': CachingMiddleware.WRITE_CACHE_SIZE - 1}]


def test_cache_is_flushed_only_when_the_cache_size_is_reached(middleware, monkeypatch, storage):
    monkeypatch.setattr(middleware, 'WRITE_CACHE_SIZE', 3)

    first = {'i': 1}
    second = {'i': 2}
    third = {'i': 3}

    middleware.write(first)
    assert storage.write_count == 0

    middleware.write(second)
    assert storage.write_count == 0

    middleware.write(third)
    assert storage.write_count == 1
    assert storage.written == [third]


def test_write_counting_restarts_after_an_automatic_flush(middleware, monkeypatch, storage):
    monkeypatch.setattr(middleware, 'WRITE_CACHE_SIZE', 2)

    middleware.write({'i': 1})
    middleware.write({'i': 2})
    assert storage.write_count == 1

    middleware.write({'i': 3})
    assert storage.write_count == 1

    middleware.write({'i': 4})
    assert storage.write_count == 2
    assert storage.written == [{'i': 2}, {'i': 4}]


def test_flush_writes_pending_data_to_the_storage(middleware, storage):
    data = {'_default': {'1': {'int': 1}}}

    middleware.write(data)
    middleware.flush()

    assert storage.write_count == 1
    assert storage.written == [data]
    assert storage.memory == data


def test_flush_without_pending_changes_does_not_write(middleware, storage):
    middleware.flush()

    assert storage.write_count == 0
    assert storage.written == []


def test_repeated_flush_writes_only_once(middleware, storage):
    data = {'i': 1}
    middleware.write(data)

    middleware.flush()
    middleware.flush()
    middleware.flush()

    assert storage.write_count == 1
    assert storage.written == [data]


def test_flush_persists_only_the_latest_state(middleware, storage):
    first = {'i': 1}
    second = {'i': 2}
    third = {'i': 3}

    middleware.write(first)
    middleware.write(second)
    middleware.write(third)
    middleware.flush()

    assert storage.write_count == 1
    assert storage.written[0] is third
    assert storage.memory is third


def test_close_flushes_pending_changes_and_closes_the_storage(middleware, storage):
    data = {'_default': {'1': {'int': 1}}}

    middleware.write(data)
    middleware.close()

    assert storage.write_count == 1
    assert storage.written == [data]
    assert storage.close_count == 1


def test_close_without_pending_changes_only_closes_the_storage(middleware, storage):
    middleware.close()

    assert storage.write_count == 0
    assert storage.close_count == 1


def test_close_persists_only_the_latest_pending_state(middleware, storage):
    middleware.write({'i': 1})
    middleware.write({'i': 2})
    latest = {'i': 3}
    middleware.write(latest)

    middleware.close()

    assert storage.write_count == 1
    assert storage.written == [latest]
    assert storage.close_count == 1


def test_data_is_readable_after_close(middleware, storage):
    data = {'_default': {'1': {'int': 1}}}
    middleware.write(data)

    middleware.close()

    assert middleware.read() == data
    assert storage.read_count == 0


def test_read_error_from_the_storage_is_propagated():
    middleware = make_middleware(FlakyReadStorage)

    with pytest.raises(OSError):
        middleware.read()

    assert middleware.storage.read_count == 1


def test_read_can_be_retried_after_a_storage_read_error():
    middleware = make_middleware(FlakyReadStorage)
    middleware.storage.memory = {'i': 1}

    with pytest.raises(OSError):
        middleware.read()

    assert middleware.read() == {'i': 1}
    assert middleware.storage.read_count == 2

    assert middleware.read() == {'i': 1}
    assert middleware.storage.read_count == 2


def test_flush_propagates_storage_write_errors():
    middleware = make_middleware(BrokenWriteStorage)

    middleware.write({'i': 1})

    with pytest.raises(OSError):
        middleware.flush()

    assert middleware.storage.write_count == 1

    with pytest.raises(OSError):
        middleware.flush()

    assert middleware.storage.write_count == 2


def test_write_propagates_storage_errors_when_the_cache_is_full(monkeypatch):
    middleware = make_middleware(BrokenWriteStorage)
    monkeypatch.setattr(middleware, 'WRITE_CACHE_SIZE', 1)

    with pytest.raises(OSError):
        middleware.write({'i': 1})

    assert middleware.storage.write_count == 1


def test_close_propagates_storage_write_errors():
    middleware = make_middleware(BrokenWriteStorage)

    middleware.write({'i': 1})

    with pytest.raises(OSError):
        middleware.close()

    assert middleware.storage.close_count == 0


def test_middleware_wraps_a_new_storage_instance_per_instance():
    first = make_middleware(MemoryStorage)
    second = make_middleware(MemoryStorage)

    assert isinstance(first.storage, MemoryStorage)
    assert isinstance(second.storage, MemoryStorage)
    assert first.storage is not second.storage


def test_tinydb_only_persists_data_when_the_middleware_is_closed(tmp_path):
    db_file = tmp_path / 'db.json'

    middleware = CachingMiddleware(JSONStorage)
    middleware.storage = JSONStorage(str(db_file))

    data = {'_default': {'1': {'int': 1}}}
    middleware.write(data)

    assert middleware.read() == data
    assert not middleware.storage.read()

    middleware.close()

    assert JSONStorage(str(db_file)).read() == data

