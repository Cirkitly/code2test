import pytest
from tinydb.operations import decrement

def test_decrement_reduces_integer_field_by_one():
    """Decrementing an integer field reduces its value by exactly 1."""
    doc = {'count': 5}
    transform = decrement('count')
    transform(doc)
    assert doc['count'] == 4

def test_decrement_returns_callable_transform():
    """decrement must return a callable transform function."""
    transform = decrement('count')
    assert callable(transform)

def test_decrement_transform_modifies_doc_in_place():
    """The transform mutates the document in place and returns None implicitly."""
    doc = {'count': 7}
    transform = decrement('count')
    result = transform(doc)
    assert result is None
    assert doc['count'] == 6

def test_decrement_from_zero_yields_negative_one():
    """Decrementing a zero-valued field should yield -1."""
    doc = {'value': 0}
    transform = decrement('value')
    transform(doc)
    assert doc['value'] == -1

def test_decrement_from_one_yields_zero():
    """Decrementing a 1-valued field should yield 0."""
    doc = {'value': 1}
    transform = decrement('value')
    transform(doc)
    assert doc['value'] == 0

def test_decrement_negative_value_makes_more_negative():
    """Decrementing a negative-valued field should yield a smaller (more negative) number."""
    doc = {'value': -5}
    transform = decrement('value')
    transform(doc)
    assert doc['value'] == -6

def test_decrement_float_field_reduces_by_one():
    """Decrementing a float field should reduce its value by 1."""
    doc = {'value': 5.5}
    transform = decrement('value')
    transform(doc)
    assert doc['value'] == 4.5

def test_decrement_preserves_unrelated_fields():
    """Decrementing one field leaves other fields untouched."""
    doc = {'count': 10, 'name': 'foo', 'tags': ['a', 'b']}
    transform = decrement('count')
    transform(doc)
    assert doc == {'count': 9, 'name': 'foo', 'tags': ['a', 'b']}

def test_decrement_applied_multiple_times_is_cumulative():
    """Applying the same transform repeatedly is cumulative."""
    doc = {'count': 5}
    transform = decrement('count')
    transform(doc)
    transform(doc)
    transform(doc)
    assert doc['count'] == 2

def test_decrement_independent_transforms_target_different_fields():
    """Transforms built for different fields operate independently (closure capture)."""
    doc = {'a': 10, 'b': 20}
    transform_a = decrement('a')
    transform_b = decrement('b')
    transform_a(doc)
    transform_b(doc)
    assert doc == {'a': 9, 'b': 19}

def test_decrement_missing_field_raises_keyerror():
    """Decrementing a non-existent field raises KeyError."""
    doc = {'other': 5}
    transform = decrement('count')
    with pytest.raises(KeyError):
        transform(doc)

def test_decrement_on_empty_document_raises_keyerror():
    """Decrementing a field in an empty document raises KeyError."""
    doc = {}
    transform = decrement('count')
    with pytest.raises(KeyError):
        transform(doc)

def test_decrement_string_field_raises_typeerror():
    """Decrementing a string-valued field raises TypeError."""
    doc = {'name': 'foo'}
    transform = decrement('name')
    with pytest.raises(TypeError):
        transform(doc)

def test_decrement_none_field_raises_typeerror():
    """Decrementing a None-valued field raises TypeError."""
    doc = {'value': None}
    transform = decrement('value')
    with pytest.raises(TypeError):
        transform(doc)

def test_decrement_list_field_raises_typeerror():
    """Decrementing a list-valued field raises TypeError."""
    doc = {'items': [1, 2, 3]}
    transform = decrement('items')
    with pytest.raises(TypeError):
        transform(doc)
