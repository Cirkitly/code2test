import json
import os
import pytest
from tinydb.database import TinyDB
from tinydb import JSONStorage
from tinydb.storages import Storage, MemoryStorage
from tinydb.table import Table, Document
from tinydb.utils import with_typehint

@pytest.fixture
def json_db(tmp_path):
    """A TinyDB instance backed by a JSON file inside a temporary directory."""
    path = str(tmp_path / 'db.json')
    db = TinyDB(path)
    yield db
    db.close()


@pytest.fixture
def memory_db():
    """A TinyDB instance backed by an in-memory storage."""
    db = TinyDB(storage=MemoryStorage)
    yield db
    db.close()


@pytest.fixture
def close_tracking_storage():
    """A Storage class that counts how often ``close()`` was called."""

    class CloseTrackingStorage(Storage):
        def __init__(self):
            self.close_count = 0
            self._data = {}

        def read(self):
            return self._data

        def write(self, data):
            self._data = data

        def close(self):
            self.close_count += 1

    return CloseTrackingStorage

def test_insert_and_read_document_via_default_table(memory_db):
    """The primary happy path: insert a document and read it back."""
    doc_id = memory_db.insert({'name': 'John', 'age': 42})

    assert memory_db.all() == [{'name': 'John', 'age': 42}]
    assert memory_db.get(doc_id=doc_id) == {'name': 'John', 'age': 42}
    assert len(memory_db) == 1

def test_storage_defaults_to_jsonstorage(tmp_path):
    """Without an explicit storage, ``default_storage_class`` (JSONStorage) is used."""
    assert TinyDB.default_storage_class is JSONStorage

    db = TinyDB(str(tmp_path / 'db.json'))
    try:
        assert isinstance(db.storage, JSONStorage)
    finally:
        db.close()

def test_default_storage_class_is_overridable():
    """``default_storage_class`` may be overridden to change the default storage."""

    class MyDB(TinyDB):
        default_storage_class = MemoryStorage

    db = MyDB()
    try:
        assert isinstance(db.storage, MemoryStorage)
    finally:
        db.close()

def test_storage_receives_args_and_kwargs(tmp_path):
    """All arguments except ``storage`` are handed to the storage class."""
    path = str(tmp_path / 'nested' / 'dir' / 'db.json')

    db = TinyDB(path, create_dirs=True)
    db.insert({'x': 1})
    db.close()

    assert os.path.isfile(path)
    with open(path) as f:
        assert json.load(f) == {'_default': {'1': {'x': 1}}}

def test_explicit_storage_is_instantiated_without_extra_args():
    """An explicit ``storage`` class is instantiated without extra arguments."""
    db = TinyDB(storage=MemoryStorage)

    try:
        assert isinstance(db.storage, MemoryStorage)
        assert db.tables() == set()
    finally:
        db.close()

def test_len_counts_default_table_documents(memory_db):
    """``len(db)`` reports the number of documents in the default table."""
    assert len(memory_db) == 0

    memory_db.insert({'a': 1})
    memory_db.insert_multiple([{'b': 2}, {'c': 3}])

    assert len(memory_db) == 3

def test_iteration_yields_default_table_documents(memory_db):
    """``__iter__`` returns an iterator over the default table's documents."""
    memory_db.insert({'i': 0})
    memory_db.insert({'i': 1})

    iterator = iter(memory_db)

    assert next(iterator) == {'i': 0}
    assert list(memory_db) == [{'i': 0}, {'i': 1}]

def test_repr_contains_table_information(memory_db):
    """``__repr__`` exposes the table names and document counts."""
    memory_db.insert({'a': 1})
    memory_db.table('other')

    result = repr(memory_db)

    assert result.startswith('<TinyDB ')
    assert 'tables=' in result
    assert 'tables_count=' in result
    assert 'default_table_documents_count=1' in result
    assert 'all_tables_documents_count=' in result

def test_table_returns_table_instance(memory_db):
    """``table()`` creates a :class:`Table` bound to the database's storage."""
    table = memory_db.table('users')

    assert isinstance(table, Table)
    assert table.name == 'users'
    assert table.storage is memory_db.storage

def test_table_is_cached_per_name(memory_db):
    """Accessing the same table name twice returns the very same object."""
    first = memory_db.table('users')
    second = memory_db.table('users')

    assert first is second

def test_different_table_names_are_separate_instances(memory_db):
    """Different table names produce different table objects."""
    a = memory_db.table('a')
    b = memory_db.table('b')

    assert a is not b
    assert a.name == 'a'
    assert b.name == 'b'

def test_tables_lists_all_table_names(memory_db):
    """``tables()`` returns the set of table names stored in the database.

    Note that ``tables()`` derives the table names from the data held by the
    storage, so only tables that actually contain data are listed: merely
    accessing a table without inserting anything does not persist it.
    """
    assert memory_db.tables() == set()

    memory_db.table('one').insert({'x': 1})
    memory_db.table('two').insert({'y': 2})

    assert memory_db.tables() == {'one', 'two'}

def test_tables_is_empty_for_uninitialised_database(tmp_path):
    """``Storage.read()`` may return ``None``; ``tables()`` must return an empty set."""
    path = tmp_path / 'empty.json'
    path.write_text('')

    db = TinyDB(str(path))
    try:
        assert db.storage.read() is None
        assert db.tables() == set()
    finally:
        db.close()

def test_tables_include_default_table_after_use(memory_db):
    """Writing to the default table makes it show up in ``tables()``."""
    memory_db.insert({'a': 1})

    assert memory_db.tables() == {TinyDB.default_table_name}

def test_table_kwargs_are_forwarded_to_table_class():
    """Extra keyword arguments are forwarded to the table class constructor."""

    class RecordingTable(Table):
        def __init__(self, storage, name, marker=None, **kwargs):
            super().__init__(storage, name, **kwargs)
            self.marker = marker

    class MyDB(TinyDB):
        table_class = RecordingTable

    db = MyDB(storage=MemoryStorage)
    try:
        table = db.table('t', marker='hello')

        assert isinstance(table, RecordingTable)
        assert table.marker == 'hello'
    finally:
        db.close()

def test_table_class_is_overridable():
    """``table_class`` defines the class used to instantiate tables."""

    class DummyTable(Table):
        pass

    class MyDB(TinyDB):
        table_class = DummyTable

    db = MyDB(storage=MemoryStorage)
    try:
        assert isinstance(db.table('t'), DummyTable)
    finally:
        db.close()

def test_drop_table_removes_only_named_table(memory_db):
    """``drop_table`` deletes only the named table from the storage."""
    memory_db.table('keep').insert({'a': 1})
    memory_db.table('drop').insert({'b': 2})

    memory_db.drop_table('drop')

    assert memory_db.tables() == {'keep'}
    assert memory_db.storage.read()['keep']
    assert 'drop' not in memory_db.storage.read()

def test_drop_table_forgets_cached_instance(memory_db):
    """A dropped table is no longer served from the internal table cache."""
    memory_db.table('gone').insert({'a': 1})
    memory_db.table('gone').insert({'a': 2})

    memory_db.drop_table('gone')

    # The table instance is recreated from storage, which no longer has the data
    assert memory_db.table('gone').all() == []

def test_drop_table_on_unknown_table_is_a_noop(memory_db):
    """Dropping a table that does not exist is silently ignored."""
    memory_db.table('existing').insert({'a': 1})
    before = memory_db.storage.read()

    memory_db.drop_table('does_not_exist')

    assert memory_db.storage.read() == before
    assert memory_db.tables() == {'existing'}

def test_drop_table_on_uninitialised_database_is_a_noop(tmp_path):
    """Dropping a table from a database without data is a no-op."""
    path = tmp_path / 'empty.json'
    path.write_text('')

    db = TinyDB(str(path))
    try:
        db.drop_table('anything')  # must not raise

        assert db.tables() == set()
    finally:
        db.close()

def test_drop_tables_removes_everything(memory_db):
    """``drop_tables`` wipes the whole database and clears the table cache."""
    memory_db.insert({'a': 1})
    memory_db.table('other').insert({'b': 2})

    memory_db.drop_tables()

    assert memory_db.storage.read() == {}
    assert memory_db.tables() == set()
    assert memory_db.table('other').all() == []

def test_drop_tables_allows_recreating_tables(memory_db):
    """After dropping all tables the same name can be used for a new table."""
    memory_db.table('a').insert({'v': 1})
    memory_db.drop_tables()

    memory_db.table('a').insert({'v': 2})

    assert memory_db.table('a').all() == [{'v': 2}]
    assert memory_db.tables() == {'a'}

def test_default_table_name_default_value():
    """The default table is named ``_default``."""
    assert TinyDB.default_table_name == '_default'
    assert TinyDB.table_class is Table

def test_getattr_forwards_to_default_table(memory_db):
    """Unknown attribute calls are forwarded to the default table."""
    memory_db.insert({'val': 1})

    assert memory_db.all() == [{'val': 1}]
    assert memory_db.contains(lambda doc: doc['val'] == 1) is True
    assert memory_db.count(lambda doc: doc['val'] == 1) == 1

def test_search_call_is_forwarded_to_default_table(memory_db):
    """``db.search(cond)`` is executed against the default table."""
    memory_db.insert({'val': 1})
    memory_db.insert({'val': 2})
    memory_db.table('other').insert({'val': 2})

    result = memory_db.search(lambda doc: doc['val'] == 2)

    assert result == [{'val': 2}]

def test_update_call_is_forwarded_to_default_table(memory_db):
    """``db.update(...)`` modifies documents of the default table."""
    memory_db.insert({'val': 1})

    memory_db.update({'val': 99})

    assert memory_db.all() == [{'val': 99}]

def test_custom_default_table_name_is_used():
    """Subclasses may change ``default_table_name``."""

    class MyDB(TinyDB):
        default_table_name = 'my_table'

    db = MyDB(storage=MemoryStorage)
    try:
        db.insert({'a': 1})

        assert db.tables() == {'my_table'}
        assert db.table('my_table').all() == [{'a': 1}]
    finally:
        db.close()

def test_storage_property_returns_storage_instance(memory_db):
    """The ``storage`` property always returns this instance's storage."""
    assert isinstance(memory_db.storage, Storage)
    assert memory_db.storage is memory_db.storage

def test_close_closes_the_storage(close_tracking_storage):
    """``close()`` forwards to the storage's ``close()`` method."""
    db = TinyDB(storage=close_tracking_storage)

    assert db.storage.close_count == 0

    db.close()

    assert db.storage.close_count == 1

def test_context_manager_closes_database(tmp_path):
    """Leaving the context manager calls ``close()`` and releases the file."""
    path = str(tmp_path / 'ctx.json')

    with TinyDB(path) as db:
        db.insert({'a': 1})

    with open(path) as f:
        data = json.load(f)

    assert data == {'_default': {'1': {'a': 1}}}

def test_context_manager_returns_same_instance(close_tracking_storage):
    """``__enter__`` returns the current instance so ``with`` rebinds it."""
    db = TinyDB(storage=close_tracking_storage)

    with db as entered:
        assert entered is db
        assert db.storage.close_count == 0

    assert db.storage.close_count == 1

def test_exit_after_manual_close_does_not_close_storage_twice(close_tracking_storage):
    """An explicit ``close()`` inside the context prevents a second close."""
    db = TinyDB(storage=close_tracking_storage)

    with db:
        db.close()

    assert db.storage.close_count == 1

def test_reopening_database_reads_persisted_data(tmp_path):
    """Data written by one instance is visible to a newly opened instance."""
    path = str(tmp_path / 'persist.json')

    db = TinyDB(path)
    db.insert({'a': 1})
    db.table('second').insert({'b': 2})
    db.close()

    db2 = TinyDB(path)
    try:
        assert db2.all() == [{'a': 1}]
        assert db2.table('second').all() == [{'b': 2}]
        assert db2.tables() == {'_default', 'second'}
    finally:
        db2.close()

def test_empty_default_table_has_no_documents(memory_db):
    """A freshly created default table contains no documents."""
    assert memory_db.all() == []
    assert len(memory_db) == 0
    assert list(memory_db) == []

def test_search_on_empty_table_returns_empty_list(memory_db):
    """Searching an empty default table returns an empty list."""
    result = memory_db.search(lambda doc: doc.get('anything') == 1)

    assert result == []

def test_all_returns_document_instances(memory_db):
    """Documents returned by the default table are ``Document`` objects."""
    memory_db.insert({'a': 1})

    docs = memory_db.all()

    assert len(docs) == 1
    assert isinstance(docs[0], Document)
    assert docs[0] == {'a': 1}

def test_insert_multiple_returns_ids_matching_storage(memory_db):
    """``insert_multiple`` returns one ID per inserted document."""
    ids = memory_db.insert_multiple([{'a': 1}, {'a': 2}])

    assert len(ids) == 2
    # JSON based storages turn the integer document IDs into string keys,
    # so the keys have to be converted back before comparing them.
    stored_ids = {int(doc_id) for doc_id in memory_db.storage.read()['_default']}
    assert stored_ids == set(ids)
    assert len(memory_db) == 2

def test_inserted_document_is_stored_in_documented_format(memory_db):
    """The storage layout is ``{table_name: {doc_id: document}}``."""
    doc_id = memory_db.insert({'name': 'John'})
    memory_db.table('extra').insert({'name': 'Jane'})

    data = memory_db.storage.read()

    assert set(data.keys()) == {'_default', 'extra'}
    # The JSON round trip performed by the storage turns document IDs into
    # string keys, hence ``str(doc_id)`` is used to look a document up.
    assert data['_default'][str(doc_id)] == {'name': 'John'}
    assert list(data['extra'].values()) == [{'name': 'Jane'}]

def test_remove_all_documents_from_default_table(memory_db):
    """``db.remove(...)`` removes documents from the default table."""
    memory_db.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    removed = memory_db.remove(lambda doc: True)

    assert len(removed) == 3
    assert memory_db.all() == []
    assert len(memory_db) == 0

def test_tables_returns_a_set(memory_db):
    """``tables()`` returns a ``set`` of table names."""
    memory_db.table('x').insert({'a': 1})
    memory_db.table('y').insert({'b': 2})

    result = memory_db.tables()

    assert isinstance(result, set)
    assert result == {'x', 'y'}

def test_with_typehint_is_available_for_table_type_hints():
    """The ``with_typehint`` helper is usable on the Table class."""
    hinted_base = with_typehint(Table)

    # ``with_typehint`` is designed to be used as a base class expression,
    # the same way ``TinyDB`` inherits from ``TableBase`` (which is built
    # from ``with_typehint(Table)``).
    class MyTable(hinted_base):
        pass

    assert isinstance(hinted_base, type)
    assert issubclass(MyTable, hinted_base)
    assert hasattr(MyTable, '__annotations__')
