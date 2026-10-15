import pytest
from tinydb.operations import add

import pytest

from tinydb.operations import add


def test_add_increments_numeric_field():
    """Primary happy path: add() should add n to a numeric field."""
    doc = {'count': 10}
    transform = add('count', 5)
    transform(doc)
    assert doc == {'count': 15}

def test_add_negative_value_decrements_field():
    """Edge case: a negative n should reduce the field value."""
    doc = {'count': 10}
    transform = add('count', -3)
    transform(doc)
    assert doc == {'count': 7}

def test_add_zero_leaves_field_unchanged():
    """Edge case: n=0 is a no-op."""
    doc = {'count': 10}
    transform = add('count', 0)
    transform(doc)
    assert doc == {'count': 10}

def test_add_with_float_value():
    """Edge case: float n and float field value should work."""
    doc = {'value': 1.5}
    transform = add('value', 2.5)
    transform(doc)
    assert doc == {'value': 4.0}

def test_add_returns_callable_transform():
    """The API should return a callable that performs the operation."""
    transform = add('count', 5)
    assert callable(transform)

def test_add_missing_field_raises_keyerror():
    """Error case: attempting to add to a non-existent field should raise KeyError."""
    doc = {'other': 10}
    transform = add('count', 5)
    with pytest.raises(KeyError):
        transform(doc)

def test_add_none_field_raises_typeerror():
    """Error case: adding to a None field should raise TypeError."""
    doc = {'count': None}
    transform = add('count', 5)
    with pytest.raises(TypeError):
        transform(doc)

def test_add_incompatible_types_raises_typeerror():
    """Error case: int field cannot be added to a string operand."""
    doc = {'count': 10}
    transform = add('count', 'abc')
    with pytest.raises(TypeError):
        transform(doc)

def test_add_concatenates_strings():
    """Edge case: += on strings performs concatenation."""
    doc = {'name': 'hello'}
    transform = add('name', ' world')
    transform(doc)
    assert doc == {'name': 'hello world'}

def test_add_extends_lists():
    """Edge case: += on lists performs in-place extension."""
    doc = {'items': [1, 2]}
    transform = add('items', [3, 4])
    transform(doc)
    assert doc == {'items': [1, 2, 3, 4]}

def test_add_mutates_document_in_place():
    """The transform should mutate the original document rather than returning a new one."""
    doc = {'count': 10}
    doc_id = id(doc)
    transform = add('count', 5)
    result = transform(doc)
    assert id(doc) == doc_id
    assert result is None
    assert doc == {'count': 15}

def test_add_transform_can_be_applied_multiple_times():
    """The transform should add n each time it is applied (no caching of initial value)."""
    doc = {'count': 10}
    transform = add('count', 5)
    transform(doc)
    transform(doc)
    transform(doc)
    assert doc == {'count': 25}

def test_add_uses_correct_field_name():
    """The transform should only modify the named field, leaving others untouched."""
    doc = {'count': 10, 'other': 100}
    transform = add('count', 5)
    transform(doc)
    assert doc == {'count': 15, 'other': 100}
