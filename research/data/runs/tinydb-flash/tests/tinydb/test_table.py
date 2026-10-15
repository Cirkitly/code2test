import pytest
from collections.abc import Mapping
from tinydb.table import Table
from tinydb.queries import QueryInstance, where
from tinydb.storages import MemoryStorage
from tinydb.utils import LRUCache

class CountingQuery:
    """A cacheable (or explicitly non-cacheable) query that counts evaluations."""

    def __init__(self, cacheable: bool = True):
        self.calls = 0
        self._cacheable = cacheable

    def __call__(self, value) -> bool:
        self.calls += 1
        return True

    def is_cacheable(self) -> bool:
        return self._cacheable


class CustomMapping(Mapping):
    """A Mapping implementation that is not a dict."""

    def __init__(self, data):
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return 'CustomMapping({!r})'.format(self._data)

@pytest.fixture
def storage():
    """A fresh in-memory storage for every test."""
    return MemoryStorage()

@pytest.fixture
def table(storage):
    """A Table named '_default' backed by the in-memory storage fixture."""
    return Table(storage, '_default')

def test_table_exposes_name_and_storage(storage, table):
    """The table exposes the name and storage it was created with."""
    assert table.name == '_default'
    assert table.storage is storage

def test_table_default_class_attributes():
    """The documented customization class variables have the documented defaults."""
    assert Table.document_id_class is int
    assert issubclass(Table.document_class, dict)
    assert Table.default_query_cache_capacity == 10
    assert issubclass(Table.query_cache_class, LRUCache)

def test_insert_assigns_incrementing_ids_starting_at_one(table):
    """IDs are handed out incrementally, starting at 1."""
    assert table.insert({'a': 1}) == 1
    assert table.insert({'a': 2}) == 2
    assert table.get(doc_id=1) == {'a': 1}
    assert table.get(doc_id=2) == {'a': 2}

def test_insert_returns_document_id_and_persists_document(table):
    """The returned ID identifies the stored document."""
    doc_id = table.insert({'a': 1, 'b': 2})

    assert doc_id == 1

    stored = table.get(doc_id=1)
    assert isinstance(stored, Table.document_class)
    assert stored.doc_id == 1
    assert stored == {'a': 1, 'b': 2}
    assert len(table) == 1

def test_insert_rejects_non_mapping_documents(table):
    """Inserting something that is not a Mapping raises ValueError."""
    with pytest.raises(ValueError, match='Document is not a Mapping'):
        table.insert([1, 2, 3])

    assert table.all() == []

def test_insert_uses_id_of_document_instances(table):
    """Document objects are stored using their own ``doc_id``."""
    doc = Table.document_class({'a': 1}, 12)

    assert table.insert(doc) == 12
    assert table.get(doc_id=12) == {'a': 1}
    assert len(table) == 1

def test_insert_rejects_duplicate_document_id(table):
    """A document ID that is already in use is rejected."""
    table.insert(Table.document_class({'a': 1}, 5))

    with pytest.raises(ValueError, match='Document with ID 5 already exists'):
        table.insert(Table.document_class({'a': 2}, 5))

    assert table.get(doc_id=5) == {'a': 1}
    assert len(table) == 1

def test_inserting_document_instance_recomputes_next_id(table):
    """After an explicit ID insert, the next free ID is recomputed."""
    table.insert({'a': 1})
    table.insert({'a': 2})
    table.insert(Table.document_class({'a': 3}, 5))

    # The stored next ID was discarded, so it is derived from the
    # highest ID currently in use (5) -> 6
    assert table.insert({'a': 4}) == 6

def test_insert_converts_custom_mappings_to_plain_dicts(storage, table):
    """Non-dict Mappings are converted to plain dicts before being stored."""
    doc_id = table.insert(CustomMapping({'a': 1}))

    raw_document = storage.read()['_default'][str(doc_id)]
    assert type(raw_document) is dict
    assert raw_document == {'a': 1}

def test_insert_multiple_returns_all_inserted_ids(table):
    """insert_multiple stores every document and returns all IDs."""
    doc_ids = table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    assert doc_ids == [1, 2, 3]
    assert table.all() == [{'a': 1}, {'a': 2}, {'a': 3}]

def test_insert_multiple_uses_ids_of_document_instances(table):
    """Mixed inserts honour existing IDs and generate new ones for plain dicts."""
    doc_ids = table.insert_multiple([Table.document_class({'a': 1}, 7), {'a': 2}])

    # The ``Document`` instance is stored under its own ID (7). The plain
    # ``dict`` gets the next free ID as determined from the *stored* table,
    # which is still empty while the whole insert operation is running, so
    # the generated ID starts at 1.
    assert doc_ids == [7, 1]
    assert table.get(doc_id=7) == {'a': 1}
    assert table.get(doc_id=1) == {'a': 2}

def test_insert_multiple_rejects_non_mapping_documents(table):
    """A batch containing a non-Mapping is rejected completely."""
    with pytest.raises(ValueError, match='Document is not a Mapping'):
        table.insert_multiple([{'a': 1}, 'not a mapping'])

    assert table.all() == []

def test_insert_multiple_rejects_duplicate_document_ids(table):
    """A document ID that is already in use is rejected inside a batch."""
    table.insert({'a': 1})

    with pytest.raises(ValueError, match='Document with ID 1 already exists'):
        table.insert_multiple([Table.document_class({'a': 2}, 1)])

    assert table.get(doc_id=1) == {'a': 1}
    assert len(table) == 1

def test_insert_multiple_with_no_documents_adds_nothing(table):
    """Inserting an empty iterable is a no-op."""
    assert table.insert_multiple([]) == []
    assert table.all() == []
    assert len(table) == 0

def test_all_returns_documents_with_ids(table):
    """all() returns document-class instances that carry their document ID."""
    table.insert({'a': 1})
    table.insert({'a': 2})

    docs = table.all()

    assert len(docs) == 2
    assert all(isinstance(doc, Table.document_class) for doc in docs)
    assert sorted(doc.doc_id for doc in docs) == [1, 2]
    assert sorted(doc['a'] for doc in docs) == [1, 2]

def test_all_on_empty_table_returns_empty_list(table):
    """An empty table contains no documents."""
    assert table.all() == []

def test_len_and_iteration_over_table(table):
    """len() counts the documents and iteration yields them with their IDs."""
    table.insert({'a': 1})
    table.insert({'a': 2})

    assert len(table) == 2

    docs = list(table)
    assert [doc.doc_id for doc in docs] == [1, 2]
    assert docs == table.all()

def test_search_returns_matching_documents(table):
    """search() returns all documents matching the query."""
    table.insert_multiple([
        {'name': 'a', 'val': 1},
        {'name': 'b', 'val': 2},
        {'name': 'c', 'val': 3},
    ])

    results = table.search(where('val') == 2)

    assert len(results) == 1
    assert results[0] == {'name': 'b', 'val': 2}
    assert isinstance(results[0], Table.document_class)
    assert results[0].doc_id == 2

def test_search_returns_empty_list_when_nothing_matches(table):
    """A query without matches returns an empty list."""
    table.insert({'val': 1})

    assert table.search(where('val') == 99) == []

def test_search_accepts_plain_callable_queries(table):
    """Any callable may be used as a condition; custom queries are cacheable."""
    table.insert_multiple([{'a': 1}, {'a': 2}])

    calls = []

    def cond(doc):
        calls.append(doc)
        return doc['a'] == 2

    results = table.search(cond)
    assert results == [{'a': 2}]

    calls_after_first_search = len(calls)
    assert calls_after_first_search == 2

    # Custom query objects are treated as cacheable by default, so the
    # condition is not evaluated again
    assert table.search(cond) == [{'a': 2}]
    assert len(calls) == calls_after_first_search

def test_search_caches_results_of_cacheable_queries(table):
    """Cacheable queries are evaluated once and their results are reused."""
    table.insert({'a': 1})
    table.insert({'a': 2})

    query = CountingQuery()

    first = table.search(query)
    calls_after_first_search = query.calls
    assert calls_after_first_search == 2

    second = table.search(query)

    assert query.calls == calls_after_first_search
    assert second == first
    assert len(second) == 2

def test_search_does_not_cache_non_cacheable_queries(table):
    """Queries that report is_cacheable() == False are never cached."""
    table.insert({'a': 1})

    query = CountingQuery(cacheable=False)
    table.search(query)
    calls_after_first_search = query.calls

    results = table.search(query)

    assert query.calls > calls_after_first_search
    assert len(results) == 1

def test_search_returns_copy_of_cached_results(table):
    """The caller never gets a reference to the cached list itself."""
    table.insert({'a': 1})

    query = CountingQuery()
    results = table.search(query)
    results.clear()

    assert table.search(query) == [{'a': 1}]

def test_query_cache_is_cleared_when_data_changes(table):
    """Writing data invalidates the query cache so searches see new data."""
    table.insert({'a': 1})

    query = CountingQuery()
    table.search(query)
    calls_before_write = query.calls

    table.insert({'a': 2})
    results = table.search(query)

    assert query.calls > calls_before_write
    assert len(results) == 2

def test_search_results_are_refreshed_after_update(table):
    """Updating a document invalidates cached search results."""
    table.insert({'a': 1})

    assert table.search(where('a') == 1) == [{'a': 1}]

    table.update({'a': 2}, where('a') == 1)

    assert table.search(where('a') == 2) == [{'a': 2}]
    assert table.search(where('a') == 1) == []

def test_query_cache_is_an_lru_cache(table):
    """The table uses an LRUCache as documented."""
    assert isinstance(table._query_cache, LRUCache)

def test_query_cache_respects_cache_size(storage):
    """The query cache evicts entries once ``cache_size`` is reached."""
    small_table = Table(storage, '_small', cache_size=1)
    small_table.insert({'a': 1})

    small_table.search(CountingQuery())
    small_table.search(CountingQuery())

    # ``LRUCache.length`` is a property (an ``int``), not a method
    assert small_table._query_cache.length == 1

def test_query_instance_without_hash_value_is_not_cacheable(table):
    """QueryInstance.is_cacheable() reports False without a hash value."""
    table.insert({'a': 1})
    table.insert({'a': 2})

    calls = []

    def test_func(doc):
        calls.append(doc)
        return True

    query = QueryInstance(test_func, None)
    assert query.is_cacheable() is False

    table.search(query)
    calls_after_first_search = len(calls)
    assert calls_after_first_search == 2

    table.search(query)
    assert len(calls) > calls_after_first_search

def test_get_by_doc_id(table):
    """A document can be fetched by its ID."""
    table.insert_multiple([{'a': 1}, {'a': 2}])

    doc = table.get(doc_id=2)

    assert doc == {'a': 2}
    assert isinstance(doc, Table.document_class)
    assert doc.doc_id == 2

def test_get_by_doc_id_returns_none_for_unknown_id(table):
    """Unknown document IDs return None."""
    table.insert({'a': 1})

    assert table.get(doc_id=99) is None

def test_get_by_doc_ids_returns_matching_documents(table):
    """Multiple document IDs can be fetched at once."""
    table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    docs = table.get(doc_ids=[1, 3])

    assert len(docs) == 2
    assert sorted(doc.doc_id for doc in docs) == [1, 3]
    assert sorted(doc['a'] for doc in docs) == [1, 3]

def test_get_by_doc_ids_ignores_unknown_ids(table):
    """Unknown IDs inside ``doc_ids`` are ignored."""
    table.insert_multiple([{'a': 1}, {'a': 2}])

    docs = table.get(doc_ids=[1, 99])

    assert docs == [{'a': 1}]
    assert len(docs) == 1

def test_get_with_empty_doc_ids_returns_empty_list(table):
    """An empty ``doc_ids`` list yields an empty list."""
    table.insert({'a': 1})

    docs = table.get(doc_ids=[])

    assert docs == []
    assert isinstance(docs, list)

def test_get_by_condition(table):
    """A document can be fetched by a condition."""
    table.insert_multiple([{'a': 1}, {'a': 2}])

    doc = table.get(where('a') == 2)

    assert doc == {'a': 2}
    assert doc.doc_id == 2


def test_get_by_condition_returns_none_when_nothing_matches(table):
    """A condition without matches returns None."""
    table.insert({'a': 1})

    assert table.get(where('a') == 42) is None

def test_get_without_arguments_raises_runtime_error(table):
    """get() requires at least one of cond, doc_id or doc_ids."""
    with pytest.raises(RuntimeError, match='You have to pass either cond or doc_id or doc_ids'):
        table.get()

def test_contains_by_doc_id_and_by_condition(table):
    """contains() reports whether a document exists for an ID or condition."""
    table.insert_multiple([{'a': 1}, {'a': 2}])

    assert table.contains(doc_id=1) is True
    assert table.contains(doc_id=99) is False
    assert table.contains(where('a') == 2) is True
    assert table.contains(where('a') == 99) is False

def test_contains_without_arguments_raises_runtime_error(table):
    """contains() requires either cond or doc_id."""
    with pytest.raises(RuntimeError, match='You have to pass either cond or doc_id'):
        table.contains()

def test_update_sets_fields_on_documents_matching_condition(table):
    """Matching documents get the new fields, non-matching ones are untouched."""
    table.insert_multiple([{'a': 1, 'b': 1}, {'a': 2, 'b': 2}])

    updated_ids = table.update({'b': 10}, where('a') == 1)

    assert updated_ids == [1]
    assert table.get(doc_id=1) == {'a': 1, 'b': 10}
    assert table.get(doc_id=2) == {'a': 2, 'b': 2}

def test_update_with_callable_fields(table):
    """A callable is called with every matching document to perform the update."""
    table.insert_multiple([{'a': 1, 'b': 1}, {'a': 2, 'b': 2}])

    updated_ids = table.update(lambda doc: doc.update({'b': 10}), where('a') == 1)

    assert updated_ids == [1]
    assert table.get(doc_id=1) == {'a': 1, 'b': 10}
    assert table.get(doc_id=2) == {'a': 2, 'b': 2}

def test_update_by_doc_ids(table):
    """Documents can be updated by an explicit list of document IDs."""
    table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    updated_ids = table.update({'x': True}, doc_ids=[1, 3])

    assert updated_ids == [1, 3]
    assert table.get(doc_id=1) == {'a': 1, 'x': True}
    assert table.get(doc_id=2) == {'a': 2}
    assert table.get(doc_id=3) == {'a': 3, 'x': True}

def test_update_without_condition_updates_all_documents(table):
    """Without cond or doc_ids, every document is updated."""
    table.insert_multiple([{'a': 1}, {'a': 2}])

    updated_ids = table.update({'x': True})

    assert sorted(updated_ids) == [1, 2]
    docs = table.all()
    assert len(docs) == 2
    assert all(doc['x'] is True for doc in docs)

def test_update_returns_empty_list_when_nothing_matches(table):
    """A condition without matches updates nothing."""
    table.insert({'a': 1})

    assert table.update({'x': 1}, where('a') == 99) == []
    assert table.get(doc_id=1) == {'a': 1}

def test_update_multiple_applies_all_given_updates(table):
    """Each (fields, condition) pair is applied to the matching documents."""
    table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    updated_ids = table.update_multiple([
        ({'x': 'one'}, where('a') == 1),
        ({'x': 'two'}, where('a') == 2),
    ])

    assert sorted(updated_ids) == [1, 2]
    assert table.get(doc_id=1) == {'a': 1, 'x': 'one'}
    assert table.get(doc_id=2) == {'a': 2, 'x': 'two'}
    assert table.get(doc_id=3) == {'a': 3}

def test_update_multiple_with_callable_fields(table):
    """A callable can be used as the update payload of update_multiple."""
    table.insert_multiple([{'a': 1}, {'a': 2}])

    updated_ids = table.update_multiple([
        (lambda doc: doc.update({'x': 1}), where('a') == 2),
    ])

    assert updated_ids == [2]
    assert table.get(doc_id=2) == {'a': 2, 'x': 1}
    assert table.get(doc_id=1) == {'a': 1}

def test_repr_contains_name_total_and_storage(table):
    """The repr contains name, document count and storage."""
    table.insert({'a': 1})

    representation = repr(table)

    assert representation.startswith('<Table ')
    assert "name='_default'" in representation
    assert 'total=1' in representation
    assert 'storage=' in representation

def test_repr_uses_subclass_name(storage):
    """The repr uses the concrete class name, supporting customization."""
    class MyTable(Table):
        pass

    assert repr(MyTable(storage, 'custom')).startswith('<MyTable ')

def test_persist_empty_stores_empty_table_in_storage():
    """With persist_empty the (empty) table is written to the storage."""
    storage = MemoryStorage()

    table = Table(storage, '_persisted', persist_empty=True)

    assert storage.read() == {'_persisted': {}}
    assert table.all() == []
    assert len(table) == 0

def test_table_is_not_stored_until_a_write_happens(storage):
    """Without persist_empty nothing is written before the first write operation."""
    Table(storage, '_lazy')

    assert storage.read() is None

def test_tables_with_different_names_are_isolated(storage):
    """Tables with different names store their documents separately."""
    first = Table(storage, '_first')
    second = Table(storage, '_second')

    first.insert({'a': 1})

    assert first.all() == [{'a': 1}]
    assert second.all() == []
    assert second.insert({'a': 2}) == 1
    assert first.all() == [{'a': 1}]
    assert second.all() == [{'a': 2}]

def test_custom_document_class_is_used_for_reads_and_writes(storage):
    """The ``document_class`` class variable can be customized."""

    class CustomDocument(Table.document_class):
        pass

    class CustomTable(Table):
        document_class = CustomDocument

    custom_table = CustomTable(storage, '_custom')
    custom_table.insert({'a': 1})

    docs = custom_table.all()
    assert type(docs[0]) is CustomDocument
    assert docs[0].doc_id == 1
    assert docs[0] == {'a': 1}

def test_custom_document_id_class_is_used_for_conversion(storage):
    """The ``document_id_class`` class variable is used when converting IDs."""

    class CustomTable(Table):
        document_id_class = str

    custom_table = CustomTable(storage, '_custom_ids')
    custom_table.insert({'a': 1})

    docs = custom_table.all()
    assert len(docs) == 1
    assert docs[0].doc_id == '1'
    assert docs[0] == {'a': 1}
