import pytest
from tinydb.table import Table, Document
from tinydb.storages import MemoryStorage
from tinydb.queries import Query

@pytest.fixture
def storage():
    """Provide a fresh in-memory storage instance for each test."""
    return MemoryStorage()


@pytest.fixture
def table(storage):
    """Provide a Table instance backed by the in-memory storage."""
    return Table(storage, 'test')

def test_init_stores_name(table):
    """The table's name is accessible via the .name property."""
    assert table.name == 'test'


def test_init_stores_storage(table, storage):
    """The storage instance passed to the constructor is exposed via .storage."""
    assert table.storage is storage


def test_init_with_custom_cache_size(storage):
    """The constructor accepts a custom cache_size argument."""
    t = Table(storage, 'mytable', cache_size=5)
    assert t.name == 'mytable'


def test_init_with_persist_empty_writes_to_storage(storage):
    """persist_empty=True causes the table to be written to storage on init."""
    Table(storage, 'mytable', persist_empty=True)
    data = storage.read()
    assert data is not None
    assert 'mytable' in data


def test_default_document_class_is_document(table):
    """The default document_class is Document (as defined by class attribute)."""
    assert table.document_class is Document


def test_default_document_id_class_is_int(table):
    """The default document_id_class is int (as defined by class attribute)."""
    assert table.document_id_class is int


def test_default_query_cache_capacity_value():
    """The default query cache capacity is 10."""
    assert Table.default_query_cache_capacity == 10

def test_insert_returns_integer_id(table):
    """Inserting a plain mapping returns the ID of the new document as an int."""
    doc_id = table.insert({'a': 1})
    assert isinstance(doc_id, int)


def test_insert_returns_distinct_ids(table):
    """Two consecutive inserts return distinct IDs."""
    id1 = table.insert({'a': 1})
    id2 = table.insert({'a': 2})
    assert id1 != id2


def test_insert_makes_document_retrievable(table):
    """A document inserted via insert() becomes visible via all()."""
    table.insert({'foo': 'bar'})
    docs = table.all()
    assert len(docs) == 1
    assert docs[0]['foo'] == 'bar'


def test_insert_rejects_non_mapping(table):
    """Inserting a value that is not a Mapping raises ValueError."""
    with pytest.raises(ValueError):
        table.insert('not a mapping')


def test_insert_with_document_uses_explicit_doc_id(table):
    """Inserting a Document instance uses its explicit doc_id."""
    doc = Document({'a': 1}, doc_id=42)
    result = table.insert(doc)
    assert result == 42
    retrieved = table.all()
    assert retrieved[0].doc_id == 42
    assert retrieved[0]['a'] == 1


def test_insert_duplicate_document_id_raises(table):
    """Inserting a Document whose doc_id is already present raises ValueError."""
    table.insert(Document({'a': 1}, doc_id=5))
    with pytest.raises(ValueError):
        table.insert(Document({'a': 2}, doc_id=5))

def test_insert_multiple_returns_list_of_ids(table):
    """insert_multiple returns a list with one id per inserted document."""
    ids = table.insert_multiple([{'a': 1}, {'b': 2}])
    assert isinstance(ids, list)
    assert len(ids) == 2


def test_insert_multiple_inserts_all_documents(table):
    """insert_multiple inserts every document provided in the iterable."""
    table.insert_multiple([{'a': 1}, {'b': 2}, {'c': 3}])
    assert len(table.all()) == 3


def test_insert_multiple_with_empty_iterable(table):
    """insert_multiple with an empty iterable is a no-op and returns []."""
    assert table.insert_multiple([]) == []
    assert len(table.all()) == 0


def test_insert_multiple_rejects_non_mapping(table):
    """insert_multiple raises ValueError if any element is not a Mapping."""
    with pytest.raises(ValueError):
        table.insert_multiple([{'a': 1}, 'not a mapping'])


def test_insert_multiple_uses_explicit_document_ids(table):
    """insert_multiple with Document objects uses each Document's explicit doc_id."""
    docs = [Document({'a': 1}, doc_id=10), Document({'b': 2}, doc_id=20)]
    ids = table.insert_multiple(docs)
    assert sorted(ids) == [10, 20]


def test_insert_multiple_duplicate_document_id_raises(table):
    """insert_multiple raises ValueError when a Document's doc_id is already present."""
    table.insert_multiple([Document({'a': 1}, doc_id=10)])
    with pytest.raises(ValueError):
        table.insert_multiple([Document({'b': 2}, doc_id=10)])

def test_all_empty_table_returns_empty_list(table):
    """all() on an empty table returns an empty list."""
    assert table.all() == []


def test_all_returns_document_instances(table):
    """all() returns instances of the configured document_class."""
    table.insert({'a': 1})
    docs = table.all()
    assert all(isinstance(d, Document) for d in docs)

def test_search_returns_matching_documents(table):
    """search() returns only documents satisfying the query."""
    table.insert({'name': 'foo'})
    table.insert({'name': 'bar'})
    results = table.search(Query().name == 'foo')
    assert len(results) == 1
    assert results[0]['name'] == 'foo'


def test_search_no_match_returns_empty_list(table):
    """search() returns an empty list when no document matches."""
    table.insert({'name': 'foo'})
    assert table.search(Query().name == 'nope') == []


def test_search_returns_document_instances(table):
    """search() returns instances of the configured document_class."""
    table.insert({'a': 1})
    results = table.search(Query().a == 1)
    assert all(isinstance(d, Document) for d in results)


def test_search_after_insert_finds_newly_added_documents(table):
    """A search executed after an insert reflects the new document.

    Even with query-cache behavior, writes must discard the cache so subsequent
    searches see the new data.
    """
    table.insert({'name': 'foo'})
    assert len(table.search(Query().name == 'foo')) == 1
    table.insert({'name': 'foo'})
    assert len(table.search(Query().name == 'foo')) == 2

def test_get_by_doc_id_returns_document(table):
    """get(doc_id=X) returns the Document whose ID matches."""
    table.insert({'foo': 'bar'})
    doc_id = table.all()[0].doc_id
    result = table.get(doc_id=doc_id)
    assert result is not None
    assert isinstance(result, Document)
    assert result['foo'] == 'bar'
    assert result.doc_id == doc_id


def test_get_by_doc_id_returns_none_for_missing(table):
    """get(doc_id=X) returns None when no document has the given ID."""
    assert table.get(doc_id=9999) is None


def test_get_by_doc_ids_returns_list_of_documents(table):
    """get(doc_ids=[...]) returns a list of matching Documents."""
    table.insert({'a': 1})
    table.insert({'b': 2})
    all_ids = [d.doc_id for d in table.all()]
    results = table.get(doc_ids=all_ids)
    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(d, Document) for d in results)


def test_get_by_doc_ids_with_empty_list(table):
    """get(doc_ids=[]) returns an empty list (no documents match)."""
    assert table.get(doc_ids=[]) == []


def test_get_by_cond_returns_matching_document(table):
    """get(cond) returns the first Document satisfying the condition."""
    table.insert({'name': 'foo'})
    table.insert({'name': 'bar'})
    result = table.get(Query().name == 'foo')
    assert result is not None
    assert result['name'] == 'foo'


def test_get_by_cond_returns_none_when_no_match(table):
    """get(cond) returns None when no document satisfies the query."""
    assert table.get(Query().x == 1) is None


def test_get_with_no_args_raises_runtime_error(table):
    """get() with no arguments raises RuntimeError."""
    with pytest.raises(RuntimeError):
        table.get()

def test_contains_by_doc_id_returns_true(table):
    """contains(doc_id=X) is True for a document with that ID."""
    table.insert({'foo': 'bar'})
    doc_id = table.all()[0].doc_id
    assert table.contains(doc_id=doc_id) is True


def test_contains_by_doc_id_returns_false_for_missing(table):
    """contains(doc_id=X) is False when no document has that ID."""
    assert table.contains(doc_id=9999) is False


def test_contains_by_cond_returns_true_when_match(table):
    """contains(cond) is True when a document matches the query."""
    table.insert({'name': 'foo'})
    assert table.contains(Query().name == 'foo') is True


def test_contains_by_cond_returns_false_when_no_match(table):
    """contains(cond) is False when no document matches the query."""
    table.insert({'name': 'foo'})
    assert table.contains(Query().name == 'nope') is False


def test_contains_with_no_args_raises_runtime_error(table):
    """contains() with no arguments raises RuntimeError."""
    with pytest.raises(RuntimeError):
        table.contains()

def test_update_with_fields_mapping_by_doc_id(table):
    """update({...}, doc_ids=...) merges new fields into the targeted documents."""
    table.insert({'foo': 'bar'})
    doc_id = table.all()[0].doc_id
    table.update({'baz': 'qux'}, doc_ids=[doc_id])
    doc = table.get(doc_id=doc_id)
    assert doc['foo'] == 'bar'
    assert doc['baz'] == 'qux'


def test_update_with_callable_by_doc_id(table):
    """update(callable, doc_ids=...) invokes the callable on each targeted document."""
    table.insert({'foo': 1})
    doc_id = table.all()[0].doc_id
    table.update(lambda d: d.update({'foo': 99}), doc_ids=[doc_id])
    doc = table.get(doc_id=doc_id)
    assert doc['foo'] == 99


def test_update_by_cond_returns_updated_ids(table):
    """update({...}, cond) returns the list of IDs of updated documents."""
    table.insert({'type': 'a'})
    table.insert({'type': 'b'})
    updated = table.update({'updated': True}, Query().type == 'a')
    assert len(updated) == 1


def test_update_by_cond_applies_only_to_matching(table):
    """update({...}, cond) modifies only the documents matching the query."""
    table.insert({'type': 'a', 'val': 1})
    table.insert({'type': 'b', 'val': 2})
    table.update({'updated': True}, Query().type == 'a')
    docs_by_type = {d['type']: d for d in table.all()}
    assert docs_by_type['a']['updated'] is True
    assert 'updated' not in docs_by_type['b']


def test_update_by_cond_no_match_returns_empty(table):
    """update({...}, cond) returns [] when nothing matches."""
    table.insert({'type': 'a'})
    result = table.update({'updated': True}, Query().type == 'missing')
    assert result == []
    assert 'updated' not in table.all()[0]


def test_update_by_doc_ids_returns_provided_ids(table):
    """update({...}, doc_ids=[...]) returns the IDs provided."""
    table.insert({'a': 1})
    table.insert({'b': 2})
    ids_to_update = [d.doc_id for d in table.all()]
    updated = table.update({'updated': True}, doc_ids=ids_to_update)
    assert set(updated) == set(ids_to_update)
    for doc in table.all():
        assert doc['updated'] is True


def test_update_all_documents_with_no_filter(table):
    """update({...}) with neither cond nor doc_ids updates every document."""
    table.insert({'a': 1})
    table.insert({'b': 2})
    ids = table.update({'updated': True})
    assert len(ids) == 2
    for doc in table.all():
        assert doc['updated'] is True

def test_repr_includes_table_name(table):
    """repr() includes the table's name."""
    r = repr(table)
    assert "name='test'" in r


def test_repr_includes_total_count(table):
    """repr() includes the document count using the format 'total=N'."""
    table.insert({'x': 1})
    r = repr(table)
    assert 'total=1' in r


def test_repr_includes_storage_label(table):
    """repr() includes a 'storage=' segment for the underlying storage."""
    r = repr(table)
    assert 'storage=' in r

def test_data_persists_across_table_instances_sharing_storage(storage):
    """A new Table instance reading from the same storage sees previously inserted documents."""
    t1 = Table(storage, 'mytable')
    t1.insert({'x': 1})
    t2 = Table(storage, 'mytable')
    docs = t2.all()
    assert len(docs) == 1
    assert docs[0]['x'] == 1
