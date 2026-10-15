import collections.abc
import pytest
from tinydb.queries import Query, where
from tinydb.table import Document, Table
from tinydb.storages import MemoryStorage
from tinydb.utils import LRUCache

@pytest.fixture
def storage() -> MemoryStorage:
    """A fresh in-memory storage instance, one per test."""
    return MemoryStorage()


@pytest.fixture
def table(storage: MemoryStorage) -> Table:
    """An empty table named ``items`` backed by an in-memory storage."""
    return Table(storage, 'items')

def test_insert_returns_sequential_ids_starting_at_one():
    table = Table(MemoryStorage(), 'items')

    assert table.insert({'a': 1}) == 1
    assert table.insert({'a': 2}) == 2
    assert table.insert({'a': 3}) == 3

    assert table.all() == [{'a': 1}, {'a': 2}, {'a': 3}]

def test_inserted_documents_are_document_instances_with_doc_id():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    docs = table.all()

    assert len(docs) == 2
    assert all(isinstance(doc, Document) for doc in docs)
    assert [doc.doc_id for doc in docs] == [1, 2]

def test_insert_copies_the_document_instead_of_referencing_it():
    table = Table(MemoryStorage(), 'items')
    source = {'a': 1}

    table.insert(source)
    source['b'] = 2

    assert table.all() == [{'a': 1}]

def test_insert_requires_a_mapping_document():
    table = Table(MemoryStorage(), 'items')

    with pytest.raises(ValueError):
        table.insert(42)

    with pytest.raises(ValueError):
        table.insert(None)

    with pytest.raises(ValueError):
        table.insert([{'a': 1}])

    assert table.all() == []

def test_insert_accepts_any_mapping_implementation():
    class MappingLike(collections.abc.Mapping):
        def __init__(self, data):
            self._data = dict(data)

        def __getitem__(self, key):
            return self._data[key]

        def __iter__(self):
            return iter(self._data)

        def __len__(self):
            return len(self._data)

    table = Table(MemoryStorage(), 'items')

    assert table.insert(MappingLike({'a': 1})) == 1
    assert table.all() == [{'a': 1}]
    assert type(table.all()[0]) is Document

def test_insert_of_document_uses_its_explicit_id():
    table = Table(MemoryStorage(), 'items')

    assert table.insert(Document({'a': 'explicit'}, 42)) == 42
    assert table.all() == [{'a': 'explicit'}]
    assert table.all()[0].doc_id == 42

def test_insert_of_document_resets_the_generated_id_counter():
    table = Table(MemoryStorage(), 'items')
    table.insert(Document({'a': 'explicit'}, 42))

    # The generated-ID counter is reset after inserting a Document, so the
    # next generated ID is derived from the highest existing ID.
    assert table.insert({'a': 'generated'}) == 43
    assert [doc['a'] for doc in table.all()] == ['explicit', 'generated']

def test_insert_of_document_with_duplicate_id_raises_value_error():
    table = Table(MemoryStorage(), 'items')
    table.insert(Document({'a': 1}, 1))

    with pytest.raises(ValueError):
        table.insert(Document({'a': 2}, 1))

    assert table.all() == [{'a': 1}]

def test_insert_multiple_returns_all_inserted_ids():
    table = Table(MemoryStorage(), 'items')

    doc_ids = table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    assert doc_ids == [1, 2, 3]
    assert table.all() == [{'a': 1}, {'a': 2}, {'a': 3}]

def test_insert_multiple_accepts_documents_with_explicit_ids():
    table = Table(MemoryStorage(), 'items')

    doc_ids = table.insert_multiple([
        Document({'a': 'first'}, 10),
        {'a': 'second'},
        Document({'a': 'third'}, 11),
    ])

    # Explicit IDs are honored, the plain mapping gets the next free ID (1)
    assert doc_ids == [10, 1, 11]
    assert doc_ids[0] == 10
    assert doc_ids[-1] == 11
    # Documents are stored (and returned by ``all()``) in insertion order
    assert [doc['a'] for doc in table.all()] == ['first', 'second', 'third']

def test_insert_multiple_is_atomic_when_a_document_is_invalid():
    table = Table(MemoryStorage(), 'items')

    with pytest.raises(ValueError):
        table.insert_multiple([{'a': 1}, 'not a mapping'])

    assert table.all() == []

def test_insert_multiple_rejects_duplicate_document_ids():
    table = Table(MemoryStorage(), 'items')

    with pytest.raises(ValueError):
        table.insert_multiple([
            Document({'a': 1}, 1),
            Document({'a': 2}, 1),
        ])

    assert table.all() == []

def test_all_returns_an_empty_list_for_an_empty_table():
    table = Table(MemoryStorage(), 'items')

    assert table.all() == []

def test_all_returns_documents_in_insertion_order():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'b': 2}, {'c': 3}])

    assert table.all() == [{'a': 1}, {'b': 2}, {'c': 3}]
    assert [doc.doc_id for doc in table.all()] == [1, 2, 3]

def test_search_returns_documents_matching_the_condition():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 1}])

    results = table.search(where('a') == 1)

    assert results == [{'a': 1}, {'a': 1}]
    assert [doc.doc_id for doc in results] == [1, 3]

def test_search_returns_empty_list_when_nothing_matches():
    table = Table(MemoryStorage(), 'items')
    table.insert({'a': 1})

    assert table.search(where('a') == 99) == []
    assert len(table.search(Query().a.exists())) == 1

def test_search_uses_the_query_cache_for_repeated_queries():
    class CountingCondition:
        def __init__(self):
            self.calls = 0

        def __call__(self, value):
            self.calls += 1
            return True

    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    cond = CountingCondition()

    assert len(table.search(cond)) == 2
    calls_after_first_search = cond.calls
    assert calls_after_first_search == 2

    # The second search must be served from the cache
    assert len(table.search(cond)) == 2
    assert cond.calls == calls_after_first_search

def test_search_does_not_cache_queries_that_are_not_cacheable():
    class UncacheableCondition:
        def __init__(self):
            self.calls = 0

        def is_cacheable(self):
            return False

        def __call__(self, value):
            self.calls += 1
            return True

    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    cond = UncacheableCondition()

    assert len(table.search(cond)) == 2
    calls_after_first_search = cond.calls

    assert len(table.search(cond)) == 2
    assert cond.calls == calls_after_first_search + 2

def test_query_cache_is_cleared_when_documents_are_written():
    class CountingCondition:
        def __init__(self):
            self.calls = 0

        def __call__(self, value):
            self.calls += 1
            return True

    table = Table(MemoryStorage(), 'items')
    table.insert({'a': 1})

    cond = CountingCondition()
    assert len(table.search(cond)) == 1
    calls_after_search = cond.calls

    table.insert({'a': 2})

    assert len(table.search(cond)) == 2
    assert cond.calls == calls_after_search + 2

def test_search_returns_a_copy_of_the_cached_results():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 1}])

    first_result = table.search(where('a') == 1)
    assert len(first_result) == 2

    first_result.clear()

    assert len(table.search(where('a') == 1)) == 2

def test_query_cache_evicts_least_recently_used_entries():
    class CountingCondition:
        def __init__(self):
            self.calls = 0

        def __call__(self, value):
            self.calls += 1
            return True

    table = Table(MemoryStorage(), 'items', cache_size=1)
    table.insert({'a': 1})

    first = CountingCondition()
    second = CountingCondition()

    table.search(first)
    calls_after_first_search = first.calls
    table.search(second)

    # The first condition was evicted from the size-1 cache
    table.search(first)
    assert first.calls == calls_after_first_search + 1

def test_get_by_doc_id_returns_the_document_or_none():
    table = Table(MemoryStorage(), 'items')
    table.insert({'a': 1})

    doc = table.get(doc_id=1)

    assert doc == {'a': 1}
    assert isinstance(doc, Document)
    assert doc.doc_id == 1
    assert table.get(doc_id=99) is None

def test_get_by_doc_ids_returns_only_the_requested_documents():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    docs = table.get(doc_ids=[1, 3])

    assert [doc.doc_id for doc in docs] == [1, 3]
    assert docs == [{'a': 1}, {'a': 3}]

    assert table.get(doc_ids=[99]) == []
    assert table.get(doc_ids=[]) == []

def test_get_by_condition_returns_the_first_match_or_none():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 1}])

    doc = table.get(where('a') == 1)

    assert doc == {'a': 1}
    assert doc.doc_id == 1
    assert table.get(where('a') == 99) is None

def test_get_doc_id_takes_precedence_over_condition():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    doc = table.get(where('a') == 1, doc_id=2)

    assert doc == {'a': 2}
    assert doc.doc_id == 2

def test_get_without_arguments_raises_runtime_error():
    table = Table(MemoryStorage(), 'items')

    with pytest.raises(RuntimeError):
        table.get()

def test_contains_by_doc_id():
    table = Table(MemoryStorage(), 'items')
    table.insert({'a': 1})

    assert table.contains(doc_id=1) is True
    assert table.contains(doc_id=2) is False

def test_contains_by_condition():
    table = Table(MemoryStorage(), 'items')
    table.insert({'a': 1})

    assert table.contains(where('a') == 1) is True
    assert table.contains(where('a') == 99) is False

def test_contains_without_arguments_raises_runtime_error():
    table = Table(MemoryStorage(), 'items')

    with pytest.raises(RuntimeError):
        table.contains()

def test_update_without_condition_updates_all_documents():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    updated_ids = table.update({'b': True})

    assert updated_ids == [1, 2]
    assert table.all() == [{'a': 1, 'b': True}, {'a': 2, 'b': True}]

def test_update_with_condition_updates_only_matching_documents():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    updated_ids = table.update({'b': True}, where('a') == 1)

    assert updated_ids == [1]
    assert table.all() == [{'a': 1, 'b': True}, {'a': 2}]
    assert table.update({'b': True}, where('a') == 99) == []
    assert table.all() == [{'a': 1, 'b': True}, {'a': 2}]

def test_update_with_doc_ids_updates_only_those_documents():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    updated_ids = table.update({'b': True}, doc_ids=[3, 1])

    assert updated_ids == [3, 1]
    assert table.all() == [{'a': 1, 'b': True}, {'a': 2}, {'a': 3, 'b': True}]

def test_update_with_unknown_doc_id_raises_key_error():
    table = Table(MemoryStorage(), 'items')
    table.insert({'a': 1})

    with pytest.raises(KeyError):
        table.update({'b': True}, doc_ids=[99])

    assert table.all() == [{'a': 1}]

def test_update_accepts_a_callable_to_modify_documents():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    def increment(doc):
        doc['a'] += 1

    updated_ids = table.update(increment, where('a') == 1)

    assert updated_ids == [1]
    assert table.all() == [{'a': 2}, {'a': 2}]

def test_update_multiple_applies_all_pairs():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}, {'a': 3}])

    updated_ids = table.update_multiple([
        ({'x': 1}, where('a') == 1),
        ({'x': 2}, where('a') == 2),
    ])

    assert updated_ids == [1, 2]
    assert table.all() == [{'a': 1, 'x': 1}, {'a': 2, 'x': 2}, {'a': 3}]

def test_update_multiple_accepts_callables():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    def set_flag(doc):
        doc['flag'] = True

    updated_ids = table.update_multiple([(set_flag, where('a') == 1)])

    assert updated_ids == [1]
    assert table.all() == [{'a': 1, 'flag': True}, {'a': 2}]

def test_update_multiple_without_matches_returns_empty_list():
    table = Table(MemoryStorage(), 'items')
    table.insert({'a': 1})

    updated_ids = table.update_multiple([({'x': 1}, where('a') == 99)])

    assert updated_ids == []
    assert table.all() == [{'a': 1}]

def test_table_exposes_its_name_and_storage():
    storage = MemoryStorage()
    table = Table(storage, 'my-table')

    assert table.name == 'my-table'
    assert table.storage is storage

def test_repr_contains_name_total_and_storage():
    table = Table(MemoryStorage(), 'items')
    table.insert_multiple([{'a': 1}, {'a': 2}])

    result = repr(table)

    assert result.startswith("<Table name='items', total=2, storage=")
    assert result.endswith('>')

def test_len_and_iteration_yield_stored_documents():
    table = Table(MemoryStorage(), 'items')
    assert len(table) == 0

    table.insert_multiple([{'a': 1}, {'a': 2}])

    assert len(table) == 2
    assert [doc.doc_id for doc in table] == [1, 2]
    assert all(isinstance(doc, Document) for doc in table)

def test_persist_empty_writes_the_empty_table_to_storage():
    storage = MemoryStorage()

    Table(storage, 'empty', persist_empty=True)

    assert storage.read() == {'empty': {}}

def test_table_is_not_written_to_storage_without_persist_empty():
    storage = MemoryStorage()
    table = Table(storage, 'lazy')

    assert storage.read() is None

    table.insert({'a': 1})

    assert storage.read() == {'lazy': {'1': {'a': 1}}}

def test_persist_empty_table_can_be_filled_afterwards():
    storage = MemoryStorage()
    table = Table(storage, 'items', persist_empty=True)

    table.insert({'a': 1})

    assert storage.read() == {'items': {'1': {'a': 1}}}
    assert table.all() == [{'a': 1}]

def test_customization_class_variables_have_documented_defaults():
    assert Table.document_class is Document
    assert Table.document_id_class is int
    assert Table.query_cache_class is LRUCache
    assert Table.default_query_cache_capacity == 10
