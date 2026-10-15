import pytest
from tinydb.operations import add

def test_add_returns_callable_transform():
    """`add(field, n)` returns a callable that mutates a document in place."""
    transform = add('count', 5)
    assert callable(transform)


def test_add_increments_integer_field_by_n():
    """Happy path: adding a positive integer to an integer field updates the value."""
    doc = {'count': 5}
    add('count', 3)(doc)
    assert doc['count'] == 8


def test_add_with_zero_leaves_field_unchanged():
    """Edge case: adding zero is a no-op for the field value."""
    doc = {'count': 5}
    add('count', 0)(doc)
    assert doc['count'] == 5


def test_add_negative_value_decrements_field():
    """Edge case: adding a negative number effectively decrements the field."""
    doc = {'count': 10}
    add('count', -3)(doc)
    assert doc['count'] == 7


def test_add_supports_float_arithmetic():
    """Adding a float to a numeric field results in float arithmetic."""
    doc = {'price': 5.0}
    add('price', 2.5)(doc)
    assert doc['price'] == 7.5


def test_add_returns_none_and_mutates_in_place():
    """The transform mutates the document and does not return a value."""
    doc = {'value': 1}
    result = add('value', 5)(doc)
    assert result is None
    assert doc == {'value': 6}


def test_add_is_repeatable_on_same_document():
    """Applying the same transform twice accumulates the addition."""
    doc = {'count': 5}
    transform = add('count', 3)
    transform(doc)
    transform(doc)
    assert doc['count'] == 11


def test_add_each_call_returns_independent_transform():
    """Two transforms built with the same arguments are independent closures that can target different documents."""
    doc_a = {'count': 1}
    doc_b = {'count': 100}
    transform = add('count', 10)
    transform(doc_a)
    transform(doc_b)
    assert doc_a['count'] == 11
    assert doc_b['count'] == 110


def test_add_missing_field_raises_keyerror():
    """Error: applying transform to a document lacking the field raises KeyError."""
    doc = {'other': 5}
    with pytest.raises(KeyError):
        add('count', 3)(doc)


def test_add_to_non_numeric_field_raises_typeerror():
    """Error: adding a number to a string field raises TypeError."""
    doc = {'name': 'Alice'}
    with pytest.raises(TypeError):
        add('name', 3)(doc)


def test_add_to_none_field_raises_typeerror():
    """Error: adding a number to a None field raises TypeError."""
    doc = {'value': None}
    with pytest.raises(TypeError):
        add('value', 1)(doc)
