import pytest
from types import MappingProxyType
from collections import OrderedDict
from tinydb import TinyDB, Query
from tinydb.operations import set
from tinydb.operations import add
from tinydb.operations import delete
from tinydb.operations import increment
from tinydb.operations import subtract

@pytest.fixture
def users_table(tmp_path):
    """Provide an empty TinyDB ``users`` table stored in a JSON file under ``tmp_path``.

    The database file lives under pytest's ``tmp_path`` fixture so tests never touch
    the working directory, and the handle is closed when the test finishes.
    """
    db = TinyDB(str(tmp_path / 'db.json'))
    try:
        yield db.table('users')
    finally:
        db.close()

def test_set_returns_a_callable_transform():
    """``set(field, val)`` is an operation factory: it returns a ``transform`` callable."""
    transform = set('name', 'Alice')

    assert callable(transform)

def test_set_transform_assigns_value_to_existing_field():
    """The happy path: ``transform(doc)`` overwrites ``doc[field]`` with ``val``."""
    doc = {'name': 'Bob', 'age': 30}

    transform = set('name', 'Alice')
    transform(doc)

    assert doc['name'] == 'Alice'

def test_set_transform_creates_a_missing_field():
    """``set`` creates the key if it is not present in the document yet."""
    doc = {'age': 30}

    set('name', 'Alice')(doc)

    assert doc == {'age': 30, 'name': 'Alice'}
    assert doc['name'] == 'Alice'

def test_set_transform_returns_none():
    """The returned callable is a mutator: its return value is ``None``."""
    doc = {'name': 'Bob'}

    result = set('name', 'Alice')(doc)

    assert result is None

def test_set_transform_mutates_the_passed_document_in_place():
    """The very same dictionary object handed in is modified in place."""
    doc = {'age': 30}
    alias = doc

    set('name', 'Alice')(doc)

    assert doc is alias
    assert alias['name'] == 'Alice'

def test_set_leaves_unrelated_fields_untouched():
    """Only ``field`` is written; every other entry of the document is preserved."""
    doc = {'name': 'Bob', 'tags': ['a', 'b'], 'meta': {'x': 1}}

    set('name', 'Alice')(doc)

    assert doc == {'name': 'Alice', 'tags': ['a', 'b'], 'meta': {'x': 1}}

def test_set_can_overwrite_a_value_with_none():
    """A ``None`` value is still written and overwrites the previous content."""
    doc = {'name': 'Bob'}

    set('name', None)(doc)

    assert doc['name'] is None
    assert doc == {'name': None}

def test_set_can_overwrite_a_value_with_a_falsy_value():
    """Falsy values such as ``0``/``''``/``False``/``[]`` are written verbatim."""
    doc = {'count': 5, 'text': 'hello', 'flag': True, 'items': ['x']}

    set('count', 0)(doc)
    set('text', '')(doc)
    set('flag', False)(doc)
    set('items', [])(doc)

    assert doc['count'] == 0
    assert doc['text'] == ''
    assert doc['flag'] is False
    assert doc['items'] == []

@pytest.mark.parametrize('value', [
    0, 1, -7, 3.5, '', 'text', True, False, None,
    [1, 'a'], {'k': 'v'}, (1, 2)
])
def test_set_assigns_any_python_value_to_the_field(value):
    """Any value can be assigned; the operation performs no type checking."""
    doc = {}

    set('field', value)(doc)

    assert doc['field'] == value

@pytest.mark.parametrize('field', [
    'name', '', 'ünïcode', 'a.b', '$set', 'with space',
    0, 7, -1, True, None, (1, 2), frozenset({1, 2})
])
def test_set_supports_any_hashable_field_name(field):
    """``field`` is used as a dictionary key, so any hashable key is supported."""
    doc = {'name': 'Bob'}

    set(field, 'value')(doc)

    assert doc[field] == 'value'
    assert field in doc

def test_set_stores_the_exact_value_object_without_copying():
    """The value is stored by reference; the operation performs no deep copy."""
    value = {'nested': [1, 2]}
    doc = {}

    set('data', value)(doc)

    assert doc['data'] is value

def test_set_captures_the_value_at_factory_time():
    """The closure captures ``val`` when the factory is called."""
    val = 'first'
    transform = set('name', val)

    val = 'second'  # rebinding the local name must not affect the operation
    doc = {}
    transform(doc)

    assert doc['name'] == 'first'

def test_set_transform_is_stateless_and_reusable_across_documents():
    """One transform instance can be applied repeatedly to different documents."""
    transform = set('status', 'active')

    doc1 = {'id': 1}
    doc2 = {'id': 2}
    doc3 = {}

    transform(doc1)
    transform(doc2)
    transform(doc3)

    assert doc1 == {'id': 1, 'status': 'active'}
    assert doc2 == {'id': 2, 'status': 'active'}
    assert doc3 == {'status': 'active'}

def test_set_shares_the_value_reference_across_documents():
    """The same ``val`` reference is used for every application (no deep copy)."""
    value = [1]
    transform = set('items', value)

    doc1 = {}
    doc2 = {}
    transform(doc1)
    transform(doc2)

    value.append(2)

    assert doc1['items'] == [1, 2]
    assert doc1['items'] is doc2['items']
    assert doc2['items'] is value

def test_applying_set_twice_is_idempotent():
    """Applying the operation repeatedly to one document is idempotent."""
    doc = {'name': 'Bob'}
    transform = set('name', 'Alice')

    transform(doc)
    transform(doc)

    assert doc == {'name': 'Alice'}

def test_set_creates_the_key_so_later_reads_do_not_raise_key_error():
    """Assignment creates the key, so a later read never raises ``KeyError``."""
    doc = {}

    with pytest.raises(KeyError):
        doc['missing']

    set('missing', 1)(doc)

    assert doc['missing'] == 1

def test_set_factory_performs_no_validation_of_its_arguments():
    """The factory validates nothing: odd ``field``/``val`` arguments are accepted."""
    unhashable_field = ['not', 'hashable']
    unserializable_value = object()

    transform = set(unhashable_field, unserializable_value)  # must not raise

    assert callable(transform)

@pytest.mark.parametrize('field', [['a'], {'a': 1}, {1, 2}])
def test_set_with_unhashable_field_raises_type_error_when_transform_is_applied(field):
    """An unhashable ``field`` fails with ``TypeError`` when the document is written to."""
    transform = set(field, 'value')  # no error at factory time

    with pytest.raises(TypeError):
        transform({})

@pytest.mark.parametrize('doc', [
    None, 42, 3.14, True, b'bytes', 'a string', (1, 2), [1, 2],
    {1, 2}, frozenset({1}), object(), MappingProxyType({'name': 'Bob'})
])
def test_set_raises_when_document_is_not_a_mutable_mapping(doc):
    """A non-mutable-mapping document cannot be item-assigned to."""
    with pytest.raises((AttributeError, TypeError)):
        set('name', 'Alice')(doc)

def test_set_raises_for_object_without_item_assignment_support():
    """An arbitrary object that does not support item assignment raises."""

    class PlainObject:
        """A plain class without ``__setitem__``."""

    with pytest.raises((AttributeError, TypeError)):
        set('name', 'Alice')(PlainObject())

def test_set_works_with_duck_typed_mutable_mapping_documents():
    """Any mutable mapping implementation can be transformed by the operation."""
    doc = OrderedDict([('name', 'Bob'), ('age', 30)])

    set('name', 'Alice')(doc)
    set('city', 'Berlin')(doc)

    assert isinstance(doc, OrderedDict)
    assert list(doc.keys()) == ['name', 'age', 'city']
    assert doc['name'] == 'Alice'
    assert doc['city'] == 'Berlin'

def test_set_accepts_non_json_serializable_values_on_plain_documents():
    """Unserializable values are only detected later, when the document is stored."""
    payload = object()
    doc = {}

    set('payload', payload)(doc)  # must not raise

    assert doc['payload'] is payload

def test_set_operates_on_documents_returned_by_tinydb(users_table):
    """The operation can be applied to real TinyDB documents by hand."""
    users_table.insert({'name': 'Bob', 'status': 'old'})

    doc = users_table.all()[0]
    set('status', 'new')(doc)

    assert doc['status'] == 'new'
    assert doc['name'] == 'Bob'

def test_table_update_applies_set_only_to_matching_documents(users_table):
    """``table.update(set(...), cond)`` writes only into documents matching ``cond``."""
    users_table.insert_multiple([
        {'name': 'Alice', 'status': 'old'},
        {'name': 'Bob', 'status': 'old'},
    ])

    users_table.update(set('status', 'new'), Query().name == 'Alice')

    docs = [dict(doc) for doc in users_table.all()]
    assert docs == [
        {'name': 'Alice', 'status': 'new'},
        {'name': 'Bob', 'status': 'old'},
    ]

def test_table_update_applies_set_to_all_documents_without_condition(users_table):
    """Without a condition, the operation is applied to every stored document."""
    users_table.insert_multiple([
        {'name': 'Alice'},
        {'name': 'Bob'},
    ])

    users_table.update(set('active', True))

    docs = [dict(doc) for doc in users_table.all()]
    assert docs == [
        {'name': 'Alice', 'active': True},
        {'name': 'Bob', 'active': True},
    ]

def test_set_composes_with_other_operations_in_one_update(users_table):
    """The operation composes with the other operation factories in a single update."""
    users_table.insert({'name': 'Alice', 'visits': 1, 'obsolete': True})

    ops = [set('name', 'Alicia'), increment('visits'), delete('obsolete')]

    def apply_all_operations(doc):
        for op in ops:
            op(doc)

    users_table.update(apply_all_operations)

    docs = [dict(doc) for doc in users_table.all()]
    assert docs == [{'name': 'Alicia', 'visits': 2}]

def test_set_applied_via_upsert_updates_an_existing_matching_document(users_table):
    """``table.upsert(set(...), cond)`` updates documents matching ``cond``."""
    users_table.insert({'name': 'Alice', 'status': 'old'})

    doc_ids = users_table.upsert(set('status', 'new'), Query().name == 'Alice')

    assert len(doc_ids) == 1
    docs = [dict(doc) for doc in users_table.all()]
    assert docs == [{'name': 'Alice', 'status': 'new'}]

def test_set_persists_the_value_to_storage(tmp_path):
    """The applied value is persisted, so it can be read back from storage."""
    path = str(tmp_path / 'db.json')

    db = TinyDB(path)
    db.table('users').insert({'name': 'Alice'})
    db.table('users').update(set('role', 'admin'), Query().name == 'Alice')
    db.close()

    reopened = TinyDB(path)
    try:
        docs = [dict(doc) for doc in reopened.table('users').all()]
        assert docs == [{'name': 'Alice', 'role': 'admin'}]
    finally:
        reopened.close()

def test_table_update_with_non_serializable_value_raises_type_error(users_table):
    """Non-JSON-serializable values fail at write time, not at factory time."""
    users_table.insert({'name': 'Alice'})

    transform = set('payload', object())  # factory does not raise

    with pytest.raises(TypeError):
        users_table.update(transform, Query().name == 'Alice')
