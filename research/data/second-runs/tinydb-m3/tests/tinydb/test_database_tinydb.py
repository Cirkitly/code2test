import pytest
from tinydb.database import TinyDB
from tinydb import JSONStorage
from tinydb.storages import MemoryStorage
from tinydb.table import Table

@pytest.fixture
def db():
    """Create an in-memory TinyDB instance for testing."""
    return TinyDB(storage=MemoryStorage)

def test_default_class_attributes():
    """Verify the class-level default attributes are correct."""
    assert TinyDB.table_class is Table
    assert TinyDB.default_table_name == '_default'
    assert TinyDB.default_storage_class is JSONStorage


def test_init_creates_storage_instance(db):
    """Verify __init__ creates a storage instance accessible via storage property."""
    assert db.storage is not None


def test_init_sets_opened_true(db):
    """Verify __init__ sets the internal _opened flag to True."""
    assert db._opened is True


def test_init_initializes_empty_tables_cache(db):
    """Verify __init__ initializes the internal _tables dict as empty."""
    assert db._tables == {}


def test_init_uses_default_jsonstorage(tmp_path):
    """Verify the default storage class is JSONStorage when no storage is provided."""
    path = str(tmp_path / "db.json")
    db = TinyDB(path)
    try:
        assert isinstance(db.storage, JSONStorage)
    finally:
        db.close()


def test_table_returns_table_instance(db):
    """Verify table(name) returns a Table instance."""
    table = db.table('mytable')
    assert isinstance(table, Table)


def test_table_returns_same_instance_on_repeated_calls(db):
    """Verify table() caches and returns the same Table instance on repeated calls."""
    table1 = db.table('mytable')
    table2 = db.table('mytable')
    assert table1 is table2


def test_table_returns_different_instances_for_different_names(db):
    """Verify table() returns different Table instances for different table names."""
    table1 = db.table('a')
    table2 = db.table('b')
    assert table1 is not table2


def test_table_forwards_kwargs_to_table_class(db):
    """Verify that additional kwargs passed to table() are forwarded to the Table constructor."""
    # Table accepts cache_size and persist_empty kwargs. If not forwarded, this would error.
    table = db.table('mytable', cache_size=5, persist_empty=True)
    assert isinstance(table, Table)


def test_tables_returns_empty_set_when_no_data(db):
    """Verify tables() returns an empty set when storage has no data (None)."""
    assert db.tables() == set()


def test_tables_returns_table_names_after_inserts(db):
    """Verify tables() returns the names of tables after inserting data into them."""
    db.table('users').insert({'name': 'alice'})
    db.table('products').insert({'name': 'widget'})
    names = db.tables()
    assert 'users' in names
    assert 'products' in names


def test_tables_includes_default_table_after_insert(db):
    """Verify the default table name appears in tables() after using db.insert."""
    db.insert({'name': 'alice'})
    assert TinyDB.default_table_name in db.tables()


def test_storage_property_returns_storage(db):
    """Verify the storage property returns the underlying storage instance."""
    assert db.storage is not None


def test_storage_property_returns_same_instance(db):
    """Verify the storage property consistently returns the same instance."""
    assert db.storage is db.storage


def test_drop_tables_removes_all_tables(db):
    """Verify drop_tables() removes all tables from storage."""
    db.table('users').insert({'name': 'alice'})
    db.table('products').insert({'name': 'widget'})
    db.drop_tables()
    assert db.tables() == set()


def test_drop_tables_clears_cache(db):
    """Verify drop_tables() clears the internal _tables cache dict."""
    db.table('users')
    assert 'users' in db._tables
    db.drop_tables()
    assert db._tables == {}


def test_drop_tables_on_empty_db_is_noop(db):
    """Verify drop_tables() works without error on an empty database."""
    db.drop_tables()  # Should not raise
    assert db.tables() == set()


def test_drop_table_existing_removes_from_storage(db):
    """Verify drop_table() removes the named table from storage while preserving others."""
    db.table('users').insert({'name': 'alice'})
    db.table('products').insert({'name': 'widget'})
    db.drop_table('users')
    names = db.tables()
    assert 'users' not in names
    assert 'products' in names


def test_drop_table_removes_from_cache(db):
    """Verify drop_table() also removes the table instance from the _tables cache."""
    db.table('users').insert({'name': 'alice'})
    assert 'users' in db._tables
    db.drop_table('users')
    assert 'users' not in db._tables


def test_drop_table_nonexistent_is_noop(db):
    """Verify drop_table() on a non-existent table name does not raise an error."""
    db.table('users').insert({'name': 'alice'})
    db.drop_table('nonexistent')  # Should not raise
    assert 'users' in db.tables()


def test_drop_table_empty_storage_is_noop(db):
    """Verify drop_table() on empty storage returns early without raising."""
    db.drop_table('anything')  # Should not raise
    assert db.tables() == set()


def test_drop_table_after_drop_tables(db):
    """Verify drop_table() works correctly after drop_tables() has been called."""
    db.table('users').insert({'name': 'alice'})
    db.drop_tables()
    db.drop_table('users')  # Should not raise
    assert db.tables() == set()


def test_close_sets_opened_false(db):
    """Verify close() sets the internal _opened flag to False."""
    db.close()
    assert db._opened is False


def test_enter_returns_self():
    """Verify __enter__ returns the database instance itself for use with 'with ... as' syntax."""
    db = TinyDB(storage=MemoryStorage)
    with db as ctx:
        assert ctx is db


def test_exit_calls_close_on_exit():
    """Verify __exit__ closes the database when leaving the context block."""
    db = TinyDB(storage=MemoryStorage)
    with db:
        pass
    assert db._opened is False


def test_exit_does_not_close_if_already_closed():
    """Verify __exit__ does not call close() again if already closed (idempotent)."""
    db = TinyDB(storage=MemoryStorage)
    db.close()
    with db:
        pass
    assert db._opened is False


def test_len_returns_zero_for_empty_default_table(db):
    """Verify len(db) returns 0 when the default table has no documents."""
    assert len(db) == 0


def test_len_returns_default_table_count(db):
    """Verify len(db) returns the count of documents in the default table."""
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})
    assert len(db) == 2


def test_len_only_counts_default_table(db):
    """Verify len(db) only counts the default table, not documents in other tables."""
    db.insert({'name': 'alice'})  # Goes into default table
    db.table('other').insert({'name': 'bob'})
    assert len(db) == 1


def test_iter_returns_default_table_documents(db):
    """Verify iter(db) returns an iterable over the default table's documents."""
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})
    docs = list(db)
    assert len(docs) == 2


def test_iter_yields_document_data(db):
    """Verify iterating the database yields documents with their inserted data."""
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})
    names = sorted(doc['name'] for doc in db)
    assert names == ['alice', 'bob']


def test_getattr_forwards_insert_to_default_table(db):
    """Verify db.insert() forwards to the default table via __getattr__."""
    db.insert({'name': 'alice'})
    # all() also forwards via __getattr__
    docs = db.all()
    assert len(docs) == 1
    assert docs[0]['name'] == 'alice'


def test_getattr_forwards_all_to_default_table(db):
    """Verify db.all() forwards to the default table via __getattr__."""
    db.insert({'name': 'alice'})
    assert len(db.all()) == 1


def test_getattr_raises_attributeerror_for_unknown():
    """Verify accessing an unknown attribute raises AttributeError (not silently forwarded)."""
    db = TinyDB(storage=MemoryStorage)
    with pytest.raises(AttributeError):
        db.this_attribute_definitely_does_not_exist


def test_repr_returns_string_containing_class_name(db):
    """Verify __repr__ returns a string representation containing the class name."""
    result = repr(db)
    assert isinstance(result, str)
    assert 'TinyDB' in result


def test_repr_contains_default_table_count(db):
    """Verify __repr__ output includes the default table document count info."""
    db.insert({'name': 'alice'})
    result = repr(db)
    # The repr includes default_table_documents_count info
    assert '0' in result or '1' in result  # some count info present
    assert isinstance(result, str)

def test_tables_returns_set_type(db):
    """Verify tables() returns a set, not a list or dict."""
    db.table('users').insert({'name': 'alice'})
    result = db.tables()
    assert isinstance(result, set)
