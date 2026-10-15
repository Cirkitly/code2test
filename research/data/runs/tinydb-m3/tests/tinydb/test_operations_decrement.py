import pytest
from tinydb.operations import decrement

def test_decrement_returns_callable_transform():
    """decrement(field) should return a callable closure."""
    from tinydb.operations import decrement
    transform = decrement('count')
    assert callable(transform)


def test_decrement_subtracts_one_from_field():
    """Applying the transform should subtract 1 from the named field."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': 5}
    transform(doc)
    assert doc['count'] == 4


def test_decrement_returns_none_and_mutates_in_place():
    """The transform should mutate the document in place and return None implicitly."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': 5}
    same_doc_before = doc
    result = transform(doc)
    assert result is None
    assert doc is same_doc_before
    assert doc['count'] == 4


def test_decrement_only_affects_named_field():
    """Decrementing one field should leave the rest of the document unchanged."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': 3, 'other': 100, 'name': 'foo'}
    transform(doc)
    assert doc['count'] == 2
    assert doc['other'] == 100
    assert doc['name'] == 'foo'


def test_decrement_can_be_applied_repeatedly():
    """The transform can be reapplied, decrementing by 1 each time."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': 5}
    transform(doc)
    transform(doc)
    transform(doc)
    assert doc['count'] == 2


def test_decrement_from_zero_produces_negative_one():
    """Decrementing 0 should produce -1 (numeric subtraction, no floor)."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': 0}
    transform(doc)
    assert doc['count'] == -1


def test_decrement_negative_value_becomes_more_negative():
    """Decrementing a negative value makes it one less."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': -5}
    transform(doc)
    assert doc['count'] == -6


def test_decrement_preserves_float_type():
    """Decrementing a float should produce a float result of value - 1."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': 3.0}
    transform(doc)
    assert doc['count'] == 2.0
    assert isinstance(doc['count'], float)


def test_decrement_raises_typeerror_on_string_field():
    """A non-numeric field value should raise TypeError on decrement."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': 'five'}
    with pytest.raises(TypeError):
        transform(doc)


def test_decrement_raises_typeerror_on_none_field():
    """A None field value should raise TypeError on decrement."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'count': None}
    with pytest.raises(TypeError):
        transform(doc)


def test_decrement_raises_keyerror_on_missing_field():
    """A missing field should raise KeyError when decrement is applied."""
    from tinydb.operations import decrement
    transform = decrement('count')
    doc = {'other': 5}
    with pytest.raises(KeyError):
        transform(doc)


def test_decrement_uses_captured_field_name():
    """The transform should decrement the field name captured at construction time."""
    from tinydb.operations import decrement
    transform = decrement('counter')
    doc = {'counter': 10, 'count': 100}
    transform(doc)
    assert doc['counter'] == 9
    assert doc['count'] == 100

