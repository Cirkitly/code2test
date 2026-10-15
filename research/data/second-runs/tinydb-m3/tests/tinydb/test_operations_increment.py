import pytest
from tinydb.operations import increment

def test_increment_returns_callable():
    """increment() should return a callable transform function."""
    transform = increment('count')

    assert callable(transform)

def test_increment_existing_integer_field_by_one():
    """Incrementing an existing integer field must increase it by exactly 1."""
    doc = {'count': 5}
    transform = increment('count')

    transform(doc)

    assert doc['count'] == 6

def test_increment_zero_value():
    """Incrementing a zero-valued field should yield 1."""
    doc = {'count': 0}
    transform = increment('count')

    transform(doc)

    assert doc['count'] == 1

def test_increment_negative_value():
    """Incrementing a negative integer should add 1 to it."""
    doc = {'count': -3}
    transform = increment('count')

    transform(doc)

    assert doc['count'] == -2

def test_increment_float_value():
    """Incrementing a float field should produce a float incremented by 1."""
    doc = {'price': 2.5}
    transform = increment('price')

    transform(doc)

    assert doc['price'] == 3.5
    assert isinstance(doc['price'], float)

def test_increment_modifies_document_in_place():
    """The transform must mutate the document in place and return None."""
    doc = {'count': 10}
    transform = increment('count')

    result = transform(doc)

    # Transform returns nothing (None) but mutates doc
    assert result is None
    # Original dict object has been modified
    assert doc == {'count': 11}

def test_increment_does_not_affect_other_fields():
    """Other fields must remain unchanged after incrementing one field."""
    doc = {'count': 1, 'name': 'alice', 'tags': ['a', 'b']}
    transform = increment('count')

    transform(doc)

    assert doc == {'count': 2, 'name': 'alice', 'tags': ['a', 'b']}

def test_increment_can_be_applied_repeatedly():
    """The transform must work correctly when called multiple times."""
    doc = {'count': 0}
    transform = increment('count')

    transform(doc)
    transform(doc)
    transform(doc)

    assert doc['count'] == 3

def test_increment_missing_field_raises_keyerror():
    """Incrementing a field that does not exist must raise KeyError."""
    doc = {'other': 1}
    transform = increment('missing')

    with pytest.raises(KeyError):
        transform(doc)

def test_increment_string_field_raises_typeerror():
    """Incrementing a string field must raise TypeError (cannot add int to str)."""
    doc = {'name': 'alice'}
    transform = increment('name')

    with pytest.raises(TypeError):
        transform(doc)

def test_increment_none_field_raises_typeerror():
    """Incrementing a None-valued field must raise TypeError."""
    doc = {'count': None}
    transform = increment('count')

    with pytest.raises(TypeError):
        transform(doc)

def test_increment_empty_document_raises_keyerror():
    """Incrementing any field on an empty document must raise KeyError."""
    doc = {}
    transform = increment('count')

    with pytest.raises(KeyError):
        transform(doc)

def test_increment_independent_transforms_do_not_share_state():
    """Each call to increment() should return an independent closure."""
    transform_a = increment('a')
    transform_b = increment('b')

    doc = {'a': 10, 'b': 20}
    transform_a(doc)
    transform_b(doc)

    assert doc == {'a': 11, 'b': 21}
