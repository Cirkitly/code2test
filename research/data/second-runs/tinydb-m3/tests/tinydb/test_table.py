import pytest
from tinydb.table import Table, Document
from tinydb.storages import MemoryStorage
from tinydb.queries import Query

@pytest.fixture
def storage():
    """A fresh in-memory storage for isolated tests."""
    return MemoryStorage()


@pytest.fixture
def table(storage):
    """An empty Table bound to a fresh storage."""
    return Table(storage, 'mytable')


@pytest.fixture
def populated_table(table):
    """A Table pre-populated with three documents (ids 1, 2, 3)."""
    table.insert({'name': 'John', 'age': 30})
    table.insert({'name': 'Jane', 'age': 25})
    table.insert({'name': 'Bob', 'age': 40})
    return table


def test_name_property_returns_table_name(storage):
    table = Table(storage, 'my_table')
    assert table.name == 'my_table'


def test_storage_property_returns_storage_instance(storage):
    table = Table(storage, 'my_table')
    assert table.storage is storage


def test_repr_includes_name_total_and_storage(table):
    rep = repr(table)
    assert 'name=' in rep
    assert 'total=0' in rep
    assert 'storage=' in rep
    assert 'mytable' in rep


def test_repr_shows_correct_total_after_insert(table):
    table.insert({'x': 1})
    assert 'total=1' in repr(table)


def test_persist_empty_creates_storage_entry(storage):
    Table(storage, 'my_table', persist_empty=True)
    data = storage.read()
    assert data is not None
    assert 'my_table' in data


def test_default_document_class_is_document(table):
    assert table.document_class is Document


def test_default_document_id_class_is_int(table):
    assert table.document_id_class is int


def test_insert_returns_integer_doc_id(table):
    doc_id = table.insert({'name': 'Alice'})
    assert isinstance(doc_id, int)


def test_insert_non_mapping_string_raises_value_error(table):
    with pytest.raises(ValueError):
        table.insert('not a mapping')


def test_insert_non_mapping_list_raises_value_error(table):
    with pytest.raises(ValueError):
        table.insert([1, 2, 3])


def test_insert_document_uses_provided_doc_id(table):
    doc = Document({'name': 'Bob'}, 42)
    assert table.insert(doc) == 42


def test_insert_duplicate_document_id_raises_value_error(table):
    table.insert(Document({'a': 1}, 5))
    with pytest.raises(ValueError):
        table.insert(Document({'a': 2}, 5))


def test_insert_multiple_returns_list_of_ids(table):
    ids = table.insert_multiple([{'x': 1}, {'x': 2}, {'x': 3}])
    assert isinstance(ids, list)
    assert len(ids) == 3
    assert all(isinstance(i, int) for i in ids)


def test_insert_multiple_non_mapping_raises_value_error(table):
    with pytest.raises(ValueError):
        table.insert_multiple(['not a mapping'])


def test_insert_multiple_duplicate_document_ids_raise_value_error(table):
    with pytest.raises(ValueError):
        table.insert_multiple([
            Document({'a': 1}, 1),
            Document({'a': 2}, 1),
        ])


def test_all_empty_table_returns_empty_list(table):
    assert table.all() == []


def test_all_returns_all_inserted_documents_wrapped_in_document_class(table):
    table.insert({'a': 1})
    table.insert({'b': 2})
    docs = table.all()
    assert len(docs) == 2
    for doc in docs:
        assert isinstance(doc, Document)


def test_search_returns_matching_documents(populated_table):
    results = populated_table.search(Query().name == 'John')
    assert len(results) == 1
    assert results[0]['name'] == 'John'


def test_search_returns_empty_list_when_no_match(populated_table):
    assert populated_table.search(Query().name == 'Nonexistent') == []


def test_search_results_are_document_instances(populated_table):
    results = populated_table.search(Query().age > 25)
    assert results
    for doc in results:
        assert isinstance(doc, Document)


def test_search_populates_query_cache(populated_table):
    q = Query().name == 'John'
    populated_table.search(q)
    assert q in populated_table._query_cache


def test_search_cached_call_yields_equal_results(populated_table):
    q = Query().name == 'Bob'
    first = populated_table.search(q)
    second = populated_table.search(q)
    assert first == second
    assert q in populated_table._query_cache


def test_get_by_doc_id_returns_document(populated_table):
    doc = populated_table.get(doc_id=1)
    assert doc is not None
    assert doc.doc_id == 1


def test_get_by_doc_id_returns_none_when_missing(populated_table):
    assert populated_table.get(doc_id=999) is None


def test_get_by_query_returns_first_match(populated_table):
    doc = populated_table.get(Query().name == 'Jane')
    assert doc is not None
    assert doc['name'] == 'Jane'


def test_get_by_query_returns_none_when_no_match(populated_table):
    assert populated_table.get(Query().name == 'Nobody') is None


def test_get_with_no_arguments_raises_runtime_error(populated_table):
    with pytest.raises(RuntimeError):
        populated_table.get()


def test_get_by_doc_ids_returns_list_of_matching_documents(populated_table):
    result = populated_table.get(doc_ids=[1, 2])
    assert isinstance(result, list)
    assert len(result) == 2


def test_get_by_doc_ids_omits_unknown_ids(populated_table):
    result = populated_table.get(doc_ids=[1, 999])
    assert isinstance(result, list)
    assert len(result) == 1


def test_contains_by_doc_id_returns_true_for_existing_id(populated_table):
    assert populated_table.contains(doc_id=1) is True


def test_contains_by_doc_id_returns_false_for_missing_id(populated_table):
    assert populated_table.contains(doc_id=999) is False


def test_contains_by_query_returns_true_for_match(populated_table):
    assert populated_table.contains(Query().name == 'John') is True


def test_contains_by_query_returns_false_for_no_match(populated_table):
    assert populated_table.contains(Query().name == 'Nobody') is False


def test_contains_with_no_arguments_raises_runtime_error(populated_table):
    with pytest.raises(RuntimeError):
        populated_table.contains()


def test_update_by_doc_ids_modifies_only_specified_documents(populated_table):
    populated_table.update({'age': 99}, doc_ids=[1])
    assert populated_table.get(doc_id=1)['age'] == 99
    assert populated_table.get(doc_id=2)['age'] == 25
    assert populated_table.get(doc_id=3)['age'] == 40


def test_update_by_query_modifies_matching_documents(populated_table):
    populated_table.update({'age': 31}, Query().name == 'John')
    assert populated_table.get(doc_id=1)['age'] == 31
    assert populated_table.get(doc_id=2)['age'] == 25


def test_update_with_no_filter_modifies_all_documents(populated_table):
    populated_table.update({'new_field': 'X'})
    for doc in populated_table.all():
        assert doc['new_field'] == 'X'


def test_update_with_callable_applies_function_per_document(populated_table):
    def increment_age(doc):
        doc['age'] = doc['age'] + 100

    populated_table.update(increment_age, doc_ids=[1])
    assert populated_table.get(doc_id=1)['age'] == 130  # 30 -> 130


def test_update_by_doc_ids_returns_the_updated_ids(populated_table):
    result = populated_table.update({'x': 1}, doc_ids=[1, 2])
    assert isinstance(result, list)
    assert sorted(result) == [1, 2]


def test_update_by_query_returns_updated_ids(populated_table):
    result = populated_table.update({'x': 1}, Query().name == 'John')
    assert result == [1]


def test_update_with_no_filter_returns_all_ids(populated_table):
    result = populated_table.update({'x': 1})
    assert isinstance(result, list)
    assert sorted(result) == [1, 2, 3]


def test_update_multiple_returns_list_of_ints(populated_table):
    updates = [
        ({'age': 100}, Query().name == 'John'),
        ({'age': 101}, Query().name == 'Jane'),
    ]
    result = populated_table.update_multiple(updates)
    assert isinstance(result, list)
    for doc_id in result:
        assert isinstance(doc_id, int)

