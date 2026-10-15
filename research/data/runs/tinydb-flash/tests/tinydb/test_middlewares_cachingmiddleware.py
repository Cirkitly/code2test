import pytest
from tinydb import Storage
from tinydb.middlewares import CachingMiddleware

class RecordingStorage(Storage):
    """In-memory storage that records every interaction for assertions."""

    def __init__(self, initial=None, *args, **kwargs):
        super().__init__()
        self.data = initial if initial is not None else {}
        self.init_args = (initial, args, kwargs)
        self.events = []
        self.read_calls = 0
        self.write_calls = 0
        self.written_data = []
        self.closed = False

    def read(self):
        self.events.append('read')
        self.read_calls += 1
        return self.data

    def write(self, data):
        self.events.append('write')
        self.write_calls += 1
        self.written_data.append(data)
        self.data = data

    def close(self):
        self.events.append('close')
        self.closed = True


class FailingReadStorage(RecordingStorage):
    """Storage whose read() always fails."""

    def read(self):
        super().read()
        raise RuntimeError('storage read failed')


class FailingWriteStorage(RecordingStorage):
    """Storage whose write() always fails."""

    def write(self, data):
        super().write(data)
        raise RuntimeError('storage write failed')

@pytest.fixture
def middleware():
    """A CachingMiddleware with an already instantiated recording storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw({'existing': {'row': 1}})
    return mw

def test_call_instantiates_storage_and_returns_the_middleware():
    """Happy path: calling the middleware builds the storage and returns itself."""
    mw = CachingMiddleware(RecordingStorage)

    assert mw.storage is None  # nothing built yet

    returned = mw()

    assert returned is mw
    assert isinstance(mw.storage, RecordingStorage)


def test_call_forwards_all_arguments_to_the_storage_class():
    """The middleware is only a wrapper: it must forward its call args to storage_cls."""
    mw = CachingMiddleware(RecordingStorage)

    mw({'a': 1}, 'extra-positional', keyword=42)

    initial, args, kwargs = mw.storage.init_args
    assert initial == {'a': 1}
    assert args == ('extra-positional',)
    assert kwargs == {'keyword': 42}


def test_read_returns_the_data_stored_in_the_storage():
    """Happy path: the very first read is delegated to the underlying storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw({'table': {'row': 1}})

    data = mw.read()

    assert data == {'table': {'row': 1}}
    assert mw.storage.read_calls == 1


def test_repeated_reads_are_served_from_the_cache():
    """Only the first read hits the storage; later reads return the very same object."""
    mw = CachingMiddleware(RecordingStorage)
    mw({'table': {'row': 1}})

    first = mw.read()
    second = mw.read()
    third = mw.read()

    assert first is second is third
    assert mw.storage.read_calls == 1
    assert mw.storage.events == ['read']


def test_write_only_updates_the_cache_until_the_cache_size_is_reached():
    """Edge case: a single write is not persisted because it is below the cache size."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    data = {'table': {'row': 1}}
    mw.write(data)

    assert mw.cache == data
    assert mw.storage.write_calls == 0


def test_default_write_cache_size_is_1000():
    """The documented default cache size is 1000 write operations."""
    assert CachingMiddleware.WRITE_CACHE_SIZE == 1000


def test_write_does_not_touch_storage_before_the_1000th_write():
    """Edge case: 999 writes stay cached, the 1000th write is flushed to the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    for index in range(999):
        mw.write({'index': index})
        assert mw.storage.write_calls == 0

    mw.write({'index': 999})

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [{'index': 999}]


def test_write_flushes_to_storage_as_soon_as_the_cache_size_is_reached():
    """With a small cache size the middleware writes through to the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 2

    mw.write({'first': 1})
    assert mw.storage.write_calls == 0

    mw.write({'second': 2})

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [{'second': 2}]
    assert mw.cache == {'second': 2}  # flushing keeps the cache warm


def test_write_with_a_cache_size_of_one_is_flushed_immediately():
    """Edge case: with WRITE_CACHE_SIZE == 1 even the first write reaches the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 1

    mw.write({'only': 1})

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [{'only': 1}]


def test_only_the_last_written_state_is_persisted():
    """The flushed payload is the latest state, not an intermediate one."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 2

    mw.write({'version': 1})
    mw.write({'version': 2})

    assert mw.storage.written_data == [{'version': 2}]


def test_flush_writes_pending_changes_to_the_storage():
    """An explicit flush persists all cached modifications."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    data = {'table': {'row': 1}}
    mw.write(data)

    mw.flush()

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [data]
    assert mw.storage.data == data


def test_flush_without_pending_changes_does_not_write():
    """Edge case: flushing a freshly created middleware is a no-op."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    mw.flush()
    mw.flush()

    assert mw.storage.write_calls == 0
    assert mw.storage.events == []


def test_repeated_flush_does_not_write_the_same_data_twice():
    """After a flush the pending-change counter is reset, so a second flush is a no-op."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.write({'table': {'row': 1}})

    mw.flush()
    mw.flush()

    assert mw.storage.write_calls == 1
    assert mw.storage.events == ['write']


def test_flush_resets_the_counter_so_a_full_cache_size_of_writes_is_needed_again():
    """After a flush, modifications are cached again until the cache size is reached."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 2

    mw.write({'round': 1})
    mw.write({'round': 2})   # triggers the first flush
    assert mw.storage.write_calls == 1

    mw.write({'round': 3})
    assert mw.storage.write_calls == 1  # still cached

    mw.write({'round': 4})   # triggers the second flush
    assert mw.storage.write_calls == 2
    assert mw.storage.written_data == [{'round': 2}, {'round': 4}]


def test_close_flushes_pending_data_and_then_closes_the_storage():
    """Closing must not lose unwritten data: flush happens before the storage is closed."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    data = {'table': {'row': 1}}
    mw.write(data)

    mw.close()

    assert mw.storage.written_data == [data]
    assert mw.storage.closed is True
    assert mw.storage.events == ['write', 'close']


def test_close_without_pending_changes_only_closes_the_storage():
    """Edge case: closing without writes must not write anything to the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    mw.close()

    assert mw.storage.write_calls == 0
    assert mw.storage.closed is True
    assert mw.storage.events == ['close']


def test_read_after_write_returns_the_written_data_without_reading_the_storage():
    """Once something is cached, reads never touch the storage again."""
    mw = CachingMiddleware(RecordingStorage)
    mw({'initial': {}})

    data = {'table': {'row': 1}}
    mw.write(data)

    assert mw.read() == data
    assert mw.storage.read_calls == 0


def test_read_after_flush_still_returns_the_current_state_from_the_cache():
    """Flushing must not invalidate the cache, so subsequent reads stay cheap."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    data = {'table': {'row': 1}}

    mw.read()          # populates the cache from the storage
    mw.write(data)
    mw.flush()

    assert mw.read() == data
    assert mw.read() is data
    assert mw.storage.read_calls == 1


def test_read_propagates_storage_errors_and_leaves_the_cache_empty():
    """Error handling: a failing storage read surfaces and nothing is cached."""
    mw = CachingMiddleware(FailingReadStorage)
    mw()

    with pytest.raises(RuntimeError):
        mw.read()

    assert mw.cache is None


def test_flush_propagates_storage_write_errors_and_keeps_the_data_pending():
    """Error handling: a failing storage write surfaces and the change stays cached."""
    mw = CachingMiddleware(FailingWriteStorage)
    mw()
    mw.write({'table': {'row': 1}})

    with pytest.raises(RuntimeError):
        mw.flush()

    assert mw.cache == {'table': {'row': 1}}

    # the failed flush did not consume the pending change
    with pytest.raises(RuntimeError):
        mw.flush()


def test_using_the_middleware_before_calling_it_raises_an_error():
    """Error handling: the storage only exists once the middleware has been called."""
    mw = CachingMiddleware(RecordingStorage)

    with pytest.raises(AttributeError):
        mw.read()

def test_read_returns_the_data_stored_in_the_storage():
    """Happy path: the very first read is delegated to the underlying storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw({'table': {'row': 1}})

    data = mw.read()

    assert data == {'table': {'row': 1}}
    assert mw.storage.read_calls == 1


def test_repeated_reads_are_served_from_the_cache():
    """Only the first read hits the storage; later reads return the very same object."""
    mw = CachingMiddleware(RecordingStorage)
    mw({'table': {'row': 1}})

    first = mw.read()
    second = mw.read()
    third = mw.read()

    assert first is second is third
    assert mw.storage.read_calls == 1
    assert mw.storage.events == ['read']

def test_write_only_updates_the_cache_until_the_cache_size_is_reached():
    """Edge case: a single write is not persisted because it is below the cache size."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    data = {'table': {'row': 1}}
    mw.write(data)

    assert mw.cache == data
    assert mw.storage.write_calls == 0


def test_default_write_cache_size_is_1000():
    """The documented default cache size is 1000 write operations."""
    assert CachingMiddleware.WRITE_CACHE_SIZE == 1000


def test_write_does_not_touch_storage_before_the_1000th_write():
    """Edge case: 999 writes stay cached, the 1000th write is flushed to the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    for index in range(999):
        mw.write({'index': index})
        assert mw.storage.write_calls == 0

    mw.write({'index': 999})

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [{'index': 999}]

def test_flush_writes_pending_changes_to_the_storage():
    """An explicit flush persists all cached modifications."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    data = {'table': {'row': 1}}
    mw.write(data)

    mw.flush()

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [data]
    assert mw.storage.data == data


def test_flush_without_pending_changes_does_not_write():
    """Edge case: flushing a freshly created middleware is a no-op."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    mw.flush()
    mw.flush()

    assert mw.storage.write_calls == 0
    assert mw.storage.events == []


def test_repeated_flush_does_not_write_the_same_data_twice():
    """After a flush the pending-change counter is reset, so a second flush is a no-op."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.write({'table': {'row': 1}})

    mw.flush()
    mw.flush()

    assert mw.storage.write_calls == 1
    assert mw.storage.events == ['write']


def test_close_flushes_pending_data_and_then_closes_the_storage():
    """Closing must not lose unwritten data: flush happens before the storage is closed."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    data = {'table': {'row': 1}}
    mw.write(data)

    mw.close()

    assert mw.storage.written_data == [data]
    assert mw.storage.closed is True
    assert mw.storage.events == ['write', 'close']


def test_close_without_pending_changes_only_closes_the_storage():
    """Edge case: closing without writes must not write anything to the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()

    mw.close()

    assert mw.storage.write_calls == 0
    assert mw.storage.closed is True
    assert mw.storage.events == ['close']

def test_write_flushes_to_storage_as_soon_as_the_cache_size_is_reached():
    """With a small cache size the middleware writes through to the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 2

    mw.write({'first': 1})
    assert mw.storage.write_calls == 0

    mw.write({'second': 2})

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [{'second': 2}]
    assert mw.cache == {'second': 2}  # flushing keeps the cache warm


def test_write_with_a_cache_size_of_one_is_flushed_immediately():
    """Edge case: with WRITE_CACHE_SIZE == 1 even the first write reaches the storage."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 1

    mw.write({'only': 1})

    assert mw.storage.write_calls == 1
    assert mw.storage.written_data == [{'only': 1}]


def test_only_the_last_written_state_is_persisted():
    """The flushed payload is the latest state, not an intermediate one."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 2

    mw.write({'version': 1})
    mw.write({'version': 2})

    assert mw.storage.written_data == [{'version': 2}]


def test_flush_resets_the_counter_so_a_full_cache_size_of_writes_is_needed_again():
    """After a flush, modifications are cached again until the cache size is reached."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    mw.WRITE_CACHE_SIZE = 2

    mw.write({'round': 1})
    mw.write({'round': 2})   # triggers the first flush
    assert mw.storage.write_calls == 1

    mw.write({'round': 3})
    assert mw.storage.write_calls == 1  # still cached

    mw.write({'round': 4})   # triggers the second flush
    assert mw.storage.write_calls == 2
    assert mw.storage.written_data == [{'round': 2}, {'round': 4}]

def test_read_after_write_returns_the_written_data_without_reading_the_storage():
    """Once something is cached, reads never touch the storage again."""
    mw = CachingMiddleware(RecordingStorage)
    mw({'initial': {}})

    data = {'table': {'row': 1}}
    mw.write(data)

    assert mw.read() == data
    assert mw.storage.read_calls == 0


def test_read_after_flush_still_returns_the_current_state_from_the_cache():
    """Flushing must not invalidate the cache, so subsequent reads stay cheap."""
    mw = CachingMiddleware(RecordingStorage)
    mw()
    data = {'table': {'row': 1}}

    mw.read()          # populates the cache from the storage
    mw.write(data)
    mw.flush()

    assert mw.read() == data
    assert mw.read() is data
    assert mw.storage.read_calls == 1

def test_read_propagates_storage_errors_and_leaves_the_cache_empty():
    """Error handling: a failing storage read surfaces and nothing is cached."""
    mw = CachingMiddleware(FailingReadStorage)
    mw()

    with pytest.raises(RuntimeError):
        mw.read()

    assert mw.cache is None


def test_flush_propagates_storage_write_errors_and_keeps_the_data_pending():
    """Error handling: a failing storage write surfaces and the change stays cached."""
    mw = CachingMiddleware(FailingWriteStorage)
    mw()
    mw.write({'table': {'row': 1}})

    with pytest.raises(RuntimeError):
        mw.flush()

    assert mw.cache == {'table': {'row': 1}}

    # the failed flush did not consume the pending change
    with pytest.raises(RuntimeError):
        mw.flush()

def test_using_the_middleware_before_calling_it_raises_an_error():
    """Error handling: the storage only exists once the middleware has been called."""
    mw = CachingMiddleware(RecordingStorage)

    with pytest.raises(AttributeError):
        mw.read()
