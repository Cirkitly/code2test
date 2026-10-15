import pytest
from tinydb.operations import set

def test_set_factory_returns_callable():
    """The factory should return a callable inner transform function."""
    transform = set('field', 'value')
    assert callable(transform)


def test_set_transform_assigns_value_to_field():
    """Primary happy path: transform should set doc[field] = val on a new doc."""
    transform = set('name', 'Alice')
    doc = {}
    transform(doc)
    assert doc['name'] == 'Alice'


def test_set_transform_returns_none_implicitly():
    """The transform should implicitly return None (no explicit return statement)."""
    transform = set('name', 'Alice')
    doc = {}
    result = transform(doc)
    assert result is None


def test_set_transform_adds_field_not_in_document():
    """The transform should add a new field that did not previously exist."""
    transform = set('new_field', 42)
    doc = {'existing': 'value'}
    transform(doc)
    assert 'new_field' in doc
    assert doc['new_field'] == 42


def test_set_transform_overwrites_existing_field():
    """The transform should overwrite an existing field's value."""
    transform = set('name', 'Bob')
    doc = {'name': 'Alice', 'age': 30}
    transform(doc)
    assert doc['name'] == 'Bob'
    assert doc['age'] == 30


def test_set_transform_preserves_other_fields():
    """Setting a field should not affect other fields in the document."""
    transform = set('name', 'Bob')
    doc = {'name': 'Alice', 'age': 30, 'city': 'NYC'}
    transform(doc)
    assert doc == {'name': 'Bob', 'age': 30, 'city': 'NYC'}


def test_set_transform_with_none_value():
    """The transform should accept None as a value, adding the field with None."""
    transform = set('field', None)
    doc = {}
    transform(doc)
    assert 'field' in doc
    assert doc['field'] is None


def test_set_transform_with_list_value():
    """The transform should accept a list as a value, storing it under the field."""
    transform = set('items', [1, 2, 3])
    doc = {}
    transform(doc)
    assert doc['items'] == [1, 2, 3]


def test_set_transform_with_dict_value():
    """The transform should accept a nested dict as a value."""
    transform = set('nested', {'a': 1, 'b': 2})
    doc = {}
    transform(doc)
    assert doc['nested'] == {'a': 1, 'b': 2}


def test_set_transform_with_integer_value():
    """The transform should accept an integer value."""
    transform = set('count', 42)
    doc = {}
    transform(doc)
    assert doc['count'] == 42
    assert isinstance(doc['count'], int)


def test_set_transform_with_float_value():
    """The transform should accept a float value."""
    transform = set('ratio', 3.14)
    doc = {}
    transform(doc)
    assert doc['ratio'] == 3.14


def test_set_transform_with_integer_field():
    """The transform should accept a hashable non-string field name (int)."""
    transform = set(0, 'first')
    doc = {}
    transform(doc)
    assert doc[0] == 'first'


def test_set_transform_with_tuple_field():
    """The transform should accept a hashable tuple as a field name."""
    transform = set(('a', 'b'), 'value')
    doc = {}
    transform(doc)
    assert doc[('a', 'b')] == 'value'


def test_set_transform_mutates_in_place():
    """The transform should mutate the same document object in place (no replacement)."""
    transform = set('x', 1)
    doc = {}
    original_id = id(doc)
    transform(doc)
    assert id(doc) == original_id
    assert doc == {'x': 1}


def test_set_transform_is_idempotent_on_repeated_calls():
    """Calling the same transform repeatedly should leave the same final value."""
    transform = set('x', 1)
    doc = {}
    transform(doc)
    transform(doc)
    transform(doc)
    assert doc == {'x': 1}


def test_set_creates_independent_transforms_per_call():
    """Each call to set() should create an independent transform with its own closure."""
    transform1 = set('a', 1)
    transform2 = set('a', 2)
    doc = {}
    transform1(doc)
    assert doc == {'a': 1}
    transform2(doc)
    assert doc == {'a': 2}


def test_set_transform_closure_captures_val():
    """The transform's closure should retain the original val even if mutated later."""
    value = ['original']
    transform = set('data', value)
    value.append('mutated')
    doc = {}
    transform(doc)
    # The transform captured a reference to the same list, so mutations are visible
    assert doc['data'] == ['original', 'mutated']


@pytest.mark.parametrize('field', [[1, 2, 3], {'key': 'val'}])
def test_set_transform_with_unhashable_field_raises_typeerror(field):
    """Using an unhashable field (list, dict) should raise TypeError on apply."""
    transform = set(field, 'value')
    doc = {}
    with pytest.raises(TypeError):
        transform(doc)


@pytest.mark.parametrize('doc', [42, None, [1, 2, 3], (1, 2, 3)])
def test_set_transform_with_non_dict_document_raises_typeerror(doc):
    """Passing a non-subscriptable / non-assignable document should raise TypeError."""
    transform = set('x', 1)
    with pytest.raises(TypeError):
        transform(doc)
