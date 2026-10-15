import pytest
import os
from tinydb import Query
from tinydb.database import TinyDB
from tinydb.storages import JSONStorage, MemoryStorage, Storage
from tinydb.table import Table, Document

class RecordingStorage(Storage):
    """An in-memory storage that records how it was created and closed."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.memory = None
        self.close_count = 0

    def read(self):
        return self.memory

    def write(self, data):
        self.memory = data

    def close(self):
        self.close_count += 1


class CustomTable(Table):
    """Marker table class used to verify the ``table_class`` customization."""


class CustomTinyDB(TinyDB):
    """TinyDB subclass that customizes the documented class variables."""

    table_class = CustomTable
    default_table_name = 'my_default'


@pytest.fixture
def db():
    """An empty, in-memory TinyDB instance."""
    db = TinyDB(storage=MemoryStorage)
    yield db
    db.close()

def test_default_storage_class_is_jsonstorage(tmp_path):
    """Without an explicit ``storage`` argument, JSONStorage is used."""

    with TinyDB(str(tmp_path / 'db.json')) as db:
        assert isinstance(db.storage, JSONStorage)


def test_documented_class_variables_have_the_expected_defaults():
    """The documented customization points have their documented defaults."""

    assert TinyDB.table_class is Table
    assert TinyDB.default_table_name == '_default'
    assert TinyDB.default_storage_class is JSONStorage


def test_missing_path_raises_type_error():
    """No args are given, so the default storage class complains about ``path``."""

    with pytest.raises(TypeError):
        TinyDB()


def test_positional_arguments_are_forwarded_to_the_storage_class():
    """Positional args are handed to the storage class (which rejects them)."""

    with pytest.raises(TypeError):
        TinyDB('some/path.json', 'unexpected', storage=MemoryStorage)


def test_storage_class_receives_args_and_kwargs():
    """Args and kwargs end up in the storage class constructor."""

    db = TinyDB('some/path.json', create_dirs=True, encoding='utf-8',
                storage=RecordingStorage)

    assert isinstance(db.storage, RecordingStorage)
    assert db.storage.args == ('some/path.json',)
    assert db.storage.kwargs == {'create_dirs': True, 'encoding': 'utf-8'}


def test_keyword_arguments_are_forwarded_to_the_storage_class(tmp_path):
    """``create_dirs=True`` is understood by JSONStorage and creates directories."""

    nested = tmp_path / 'some' / 'nested' / 'dir' / 'db.json'

    with TinyDB(str(nested), create_dirs=True) as db:
        db.insert({'foo': 'bar'})
        assert os.path.exists(str(nested))


def test_missing_directory_raises_file_not_found_error(tmp_path):
    """The storage raises an error if the containing directory is missing."""

    with pytest.raises(FileNotFoundError):
        TinyDB(str(tmp_path / 'missing' / 'db.json'))


def test_documents_persist_between_instances(tmp_path):
    """Data survives closing and re-opening the same database file."""

    path = str(tmp_path / 'db.json')

    with TinyDB(path) as db:
        db.insert({'foo': 'bar'})
        db.table('other').insert({'a': 1})

    with TinyDB(path) as reopened:
        assert reopened.tables() == {'_default', 'other'}
        assert reopened.all() == [{'foo': 'bar'}]
        assert reopened.table('other').all() == [{'a': 1}]


def test_table_returns_the_same_instance_for_the_same_name(db):
    """Accessing the same table name twice returns the very same object."""

    assert db.table('users') is db.table('users')


def test_different_names_create_different_tables(db):
    """Two different names create two independent table objects."""

    assert db.table('users') is not db.table('posts')


def test_tables_share_the_database_storage(db):
    """Tables are built with the storage instance of the database."""

    assert db.table('users').storage is db.storage
    assert db.table('posts').storage is db.storage
    assert db.storage is db.storage


def test_table_keyword_arguments_are_forwarded_to_the_table_class(db):
    """Options like ``persist_empty`` reach the Table constructor."""

    table = db.table('kept', persist_empty=True)
    doc_id = table.insert({'a': 1})
    table.remove(doc_ids=[doc_id])

    # The ``persist_empty=True`` option passed to ``TinyDB.table`` has been
    # forwarded to the table class, so the emptied table is still stored
    assert db.tables() == {'kept'}
    assert table.all() == []

def test_table_options_are_ignored_when_the_table_already_exists(db):
    """The table is only created on first access, so later kwargs are dropped."""

    first = db.table('t', persist_empty=True)
    second = db.table('t', persist_empty=False)

    assert first is second


def test_unknown_table_option_raises_type_error(db):
    """Unknown table options are an error."""

    with pytest.raises(TypeError):
        db.table('t', this_option_does_not_exist=True)


def test_tables_is_an_empty_set_for_a_new_database(db):
    """An uninitialized storage yields an empty set of table names."""

    assert db.storage.read() is None
    assert db.tables() == set()
    assert isinstance(db.tables(), set)


def test_creating_a_table_without_documents_does_not_persist_it(db):
    """Accessing a table does not create it in the database file."""

    db.table('empty')

    assert db.tables() == set()


def test_tables_lists_the_names_of_tables_holding_data(db):
    """Tables are listed by the names used to create them."""

    db.insert({'a': 1})
    db.table('posts').insert({'b': 2})

    assert db.tables() == {'_default', 'posts'}


def test_drop_table_removes_the_table_and_its_data(db):
    """A dropped table is gone from storage and recreated empty when accessed."""

    table = db.table('posts')
    table.insert({'b': 2})
    assert db.tables() == {'posts'}

    db.drop_table('posts')

    assert db.tables() == set()

    recreated = db.table('posts')
    assert recreated is not table
    assert recreated.all() == []


def test_drop_table_keeps_other_tables_intact(db):
    """Only the named table is removed."""

    db.table('keep').insert({'a': 1})
    db.table('drop').insert({'b': 2})

    db.drop_table('drop')

    assert db.tables() == {'keep'}
    assert db.table('keep').all() == [{'a': 1}]


def test_drop_table_with_an_unknown_name_keeps_the_data(db):
    """Dropping an unknown table name does nothing and does not raise."""

    db.insert({'a': 1})

    db.drop_table('does-not-exist')

    assert db.tables() == {'_default'}
    assert db.all() == [{'a': 1}]


def test_drop_table_on_an_uninitialized_database_is_a_noop():
    """Dropping a table from an uninitialized database is a no-op."""

    db = TinyDB(storage=MemoryStorage)
    assert db.storage.read() is None

    db.drop_table('anything')

    assert db.storage.read() is None
    assert db.tables() == set()


def test_drop_tables_removes_every_table(db):
    """``drop_tables()`` removes all data and forgets all table instances."""

    db.insert({'a': 1})
    table = db.table('posts')
    table.insert({'b': 2})
    assert db.tables() == {'_default', 'posts'}

    db.drop_tables()

    assert db.tables() == set()
    assert db.table('posts') is not table
    assert db.table('_default').all() == []
    assert len(db) == 0


def test_close_closes_the_storage():
    """Closing the database closes the storage."""

    db = TinyDB(storage=RecordingStorage)
    assert db.storage.close_count == 0

    assert db.close() is None

    assert db.storage.close_count == 1


def test_context_manager_returns_the_instance_and_closes_the_storage():
    """The context manager yields the database itself and closes on exit."""

    db = TinyDB(storage=RecordingStorage)

    with db as entered:
        assert entered is db
        assert db.storage.close_count == 0
        db.insert({'a': 1})

    assert db.storage.close_count == 1

    stored = db.storage.read()
    # Storages may represent document IDs as strings when persisting them,
    # so compare them numerically
    assert {
        int(stored_id): document
        for stored_id, document in stored['_default'].items()
    } == {1: {'a': 1}}

def test_context_manager_does_not_close_an_already_closed_database():
    """A database closed manually is not closed again when used as context."""

    db = TinyDB(storage=RecordingStorage)
    db.close()
    assert db.storage.close_count == 1

    with db:
        pass

    assert db.storage.close_count == 1


def test_exceptions_inside_the_context_are_not_swallowed():
    """Exceptions propagate while the storage is closed nevertheless."""

    db = TinyDB(storage=RecordingStorage)

    with pytest.raises(RuntimeError):
        with db:
            raise RuntimeError('boom')

    assert db.storage.close_count == 1


def test_unknown_attributes_are_forwarded_to_the_default_table(db):
    """Reading ``db.name`` returns the name of the default table."""

    assert db.name == TinyDB.default_table_name
    assert db.name == '_default'


def test_table_operations_are_forwarded_to_the_default_table(db):
    """Table methods called on the database operate on the default table."""

    doc_id = db.insert({'a': 1})

    assert db.contains(doc_id=doc_id)
    assert db.get(doc_id=doc_id) == {'a': 1}
    assert db.all() == [{'a': 1}]

    assert db.update({'a': 2}, doc_ids=[doc_id]) == [doc_id]
    assert db.get(doc_id=doc_id) == {'a': 2}

    assert db.remove(doc_ids=[doc_id]) == [doc_id]
    assert db.all() == []


def test_search_is_forwarded_to_the_default_table(db):
    """Queries passed to the database are evaluated against the default table."""

    db.insert({'value': 1})
    db.insert({'value': 2})
    db.table('other').insert({'value': 3})

    assert db.search(Query().value == 1) == [{'value': 1}]
    # Documents of other tables are not considered
    assert db.search(Query().value > 1) == [{'value': 2}]

def test_unknown_attribute_on_the_default_table_raises_attribute_error(db):
    """Attribute forwarding still raises AttributeError for unknown names."""

    with pytest.raises(AttributeError):
        db.this_attribute_does_not_exist


def test_len_counts_only_documents_of_the_default_table(db):
    """``len(db)`` counts the default table's documents."""

    assert len(db) == 0

    db.insert({'a': 1})
    db.table('other').insert({'b': 2})

    assert len(db) == 1
    assert len(db.table('other')) == 1


def test_iteration_yields_documents_of_the_default_table(db):
    """Iterating over the database iterates the default table."""

    db.insert_multiple([{'a': 1}, {'a': 2}])
    db.table('other').insert({'a': 3})

    documents = list(db)

    assert [doc['a'] for doc in documents] == [1, 2]
    assert all(isinstance(doc, Document) for doc in documents)


def test_repr_contains_table_and_document_information(db):
    """``repr(db)`` summarises tables and document counts."""

    db.insert({'foo': 'bar'})

    representation = repr(db)

    assert representation.startswith('<TinyDB ')
    assert "tables=['_default']" in representation
    assert 'tables_count=1' in representation
    assert 'default_table_documents_count=1' in representation
    assert "all_tables_documents_count=['_default=1']" in representation
    assert representation.endswith('>')


def test_custom_table_class_and_default_table_name_are_used():
    """Customization through the documented class variables."""

    db = CustomTinyDB(storage=MemoryStorage)

    assert type(db.table('custom')) is CustomTable

    doc_id = db.insert({'a': 1})

    assert db.tables() == {'my_default'}

    stored = db.storage.read()
    # Storages may represent document IDs as strings when persisting them,
    # so compare them numerically
    assert {
        int(stored_id): document
        for stored_id, document in stored['my_default'].items()
    } == {doc_id: {'a': 1}}

    assert len(db) == 1
    assert repr(db).startswith('<CustomTinyDB ')

def test_documents_are_stored_in_the_documented_data_model(db):
    """The storage mirrors the documented {table: {id: document}} structure."""

    default_id = db.insert({'foo': 'bar'})
    other_id = db.table('posts').insert({'b': 2})

    stored = db.storage.read()

    # Storages may represent document IDs as strings when persisting them,
    # so compare them numerically
    assert {
        table: {int(stored_id): document for stored_id, document in docs.items()}
        for table, docs in stored.items()
    } == {
        '_default': {default_id: {'foo': 'bar'}},
        'posts': {other_id: {'b': 2}},
    }
