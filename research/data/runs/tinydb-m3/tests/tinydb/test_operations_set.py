import pytest
from tinydb.operations import set as set_op

def test_set_returns_a_callable_transformer():
    """set() must be a factory that returns a callable transformer, not a value."""
    transformer = set_op('field', 'value')
    assert callable(transformer)

def test_set_does_not_immediately_apply_transformation():
    """set() returns a function; it must not eagerly produce a dict or any modified value."""
    result = set_op('name', 'Alice')
    # The return value is a function, not a transformed document
    assert callable(result)
    assert not isinstance(result, dict)

def test_set_transformer_sets_field_on_empty_document():
    """Primary happy path: the transformer sets doc[field] = val on an empty doc."""
    doc = {}
    transformer = set_op('name', 'Alice')
    transformer(doc)
    assert doc == {'name': 'Alice'}

def test_set_transformer_returns_none():
    """The transformer implicitly returns None (TinyDB's in-place mutation convention)."""
    doc = {'name': 'Bob'}
    transformer = set_op('name', 'Alice')
    result = transformer(doc)
    assert result is None
    # And the doc was still updated in place despite the None return
    assert doc == {'name': 'Alice'}

def test_set_transformer_modifies_document_in_place():
    """The transformer mutates the same document object (same identity), no copy is made."""
    doc = {'existing': 'value'}
    original_id = id(doc)
    original_size_before = len(doc)

    transformer = set_op('new_field', 'new_value')
    transformer(doc)

    # Same object identity — mutation happened on the original
    assert id(doc) == original_id
    # The new field was added in place
    assert doc == {'existing': 'value', 'new_field': 'new_value'}
    assert len(doc) == original_size_before + 1

def test_set_transformer_overwrites_existing_field():
    """Setting an existing field overwrites its prior value."""
    doc = {'name': 'Bob', 'age': 30}
    transformer = set_op('name', 'Alice')
    transformer(doc)
    assert doc == {'name': 'Alice', 'age': 30}

def test_set_transformer_preserves_other_fields():
    """Setting one field leaves every other field untouched."""
    doc = {'a': 1, 'b': 2, 'c': 3}
    transformer = set_op('b', 20)
    transformer(doc)
    assert doc == {'a': 1, 'b': 20, 'c': 3}

@pytest.mark.parametrize("value", [
    None,
    0,
    False,
    '',
    [],
    {},
    'a string',
    42,
    3.14,
    True,
    [1, 2, 3],
    {'nested': 'dict'},
    (1, 2, 3),
])
def test_set_accepts_various_value_types(value):
    """The transformer accepts any value type and stores it on the field as-is."""
    doc = {}
    transformer = set_op('field', value)
    transformer(doc)
    assert doc == {'field': value}
    # The value is the same object (stored by reference, not copied)
    assert doc['field'] is value

def test_set_transformer_is_reusable_across_multiple_documents():
    """The same transformer instance can be reused across multiple distinct documents."""
    transformer = set_op('status', 'active')

    doc_a = {}
    doc_b = {'status': 'pending'}
    doc_c = {'name': 'test', 'other': 'data'}

    transformer(doc_a)
    transformer(doc_b)
    transformer(doc_c)

    assert doc_a == {'status': 'active'}
    assert doc_b == {'status': 'active'}
    assert doc_c == {'name': 'test', 'other': 'data', 'status': 'active'}

def test_set_can_be_chained_sequentially_on_same_document():
    """Multiple set transformers can be applied in sequence to the same document."""
    doc = {}
    set_op('a', 1)(doc)
    set_op('b', 2)(doc)
    set_op('c', 3)(doc)
    assert doc == {'a': 1, 'b': 2, 'c': 3}

def test_set_closure_captures_value_at_creation_time():
    """The val parameter is captured by the closure at factory creation time."""
    val = 'captured'
    transformer = set_op('field', val)
    # Rebinding 'val' in the outer scope must NOT affect the closure.
    val = 'rebound'
    doc = {}
    transformer(doc)
    assert doc == {'field': 'captured'}

def test_set_closure_captures_field_at_creation_time():
    """The field parameter is captured by the closure at factory creation time."""
    field = 'first'
    transformer = set_op(field, 'value')
    # Rebinding 'field' in the outer scope must NOT affect the closure.
    field = 'second'
    doc = {'first': 'old', 'second': 'other'}
    transformer(doc)
    # The transformer used 'first' (captured), not 'second' (current binding).
    assert doc == {'first': 'value', 'second': 'other'}

def test_set_stores_callable_value_without_invoking():
    """A callable val is stored on the doc as a value, not invoked."""
    inner_transformer = set_op('inner_field', 'inner_value')
    outer_transformer = set_op('outer_field', inner_transformer)

    doc = {}
    outer_transformer(doc)

    # The outer transformer stored the inner transformer object as a value,
    # it did NOT call it.
    assert doc == {'outer_field': inner_transformer}
    assert doc['outer_field'] is inner_transformer
    assert 'inner_field' not in doc

@pytest.mark.parametrize("field_name", [1, 0, 42, ('a', 'b'), (1, 2, 3)])
def test_set_accepts_hashable_non_string_field_names(field_name):
    """Hashable non-string field names work as document keys."""
    doc = {}
    transformer = set_op(field_name, 'value')
    transformer(doc)
    assert doc[field_name] == 'value'
    assert len(doc) == 1

def test_set_with_unhashable_field_name_raises_typeerror():
    """An unhashable field name raises TypeError when the transformer runs."""
    # The factory itself does not validate; the failure surfaces when transform(doc)
    # attempts doc[unhashable] = val, which dict forbids.
    transformer = set_op(['a', 'b'], 'value')  # list is unhashable
    with pytest.raises(TypeError):
        transformer({})

@pytest.mark.parametrize("bad_doc", [None, 123, 3.14, 'a string', object()])
def test_set_on_non_dict_document_raises_error(bad_doc):
    """Applying the transformer to a non-dict-like value raises TypeError/AttributeError."""
    transformer = set_op('field', 'value')
    with pytest.raises((TypeError, AttributeError)):
        transformer(bad_doc)

def test_set_on_list_with_string_field_raises_typeerror():
    """A list doc with a string field raises TypeError (str is not a valid list index)."""
    transformer = set_op('field', 'value')
    with pytest.raises(TypeError):
        transformer([])
