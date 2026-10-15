from tinydb.operations import increment
import pytest

def test_increment_increments_integer_field_by_one():
    """Increment should add 1 to an existing integer field."""
    doc = {'count': 5}
    increment('count')(doc)
    assert doc == {'count': 6}

def test_increment_from_zero():
    """Increment should correctly handle a field whose value is zero."""
    doc = {'count': 0}
    increment('count')(doc)
    assert doc == {'count': 1}

def test_increment_negative_number():
    """Increment should add 1 to a negative integer field."""
    doc = {'count': -5}
    increment('count')(doc)
    assert doc == {'count': -4}

def test_increment_float_field():
    """Increment should add 1 to a float field, preserving float type."""
    doc = {'value': 1.5}
    increment('value')(doc)
    assert doc == {'value': 2.5}

def test_increment_can_be_applied_multiple_times():
    """The returned transform should be reusable, adding 1 on each call."""
    doc = {'count': 5}
    transform = increment('count')
    transform(doc)
    transform(doc)
    transform(doc)
    assert doc == {'count': 8}

def test_increment_missing_field_raises_keyerror():
    """Increment should raise KeyError when the field does not exist in the document."""
    doc = {}
    with pytest.raises(KeyError):
        increment('count')(doc)

def test_increment_string_field_raises_typeerror():
    """Increment should raise TypeError when the field holds a non-numeric string."""
    doc = {'name': 'alice'}
    with pytest.raises(TypeError):
        increment('name')(doc)

def test_increment_none_field_raises_typeerror():
    """Increment should raise TypeError when the field value is None."""
    doc = {'value': None}
    with pytest.raises(TypeError):
        increment('value')(doc)

def test_increment_list_field_raises_typeerror():
    """Increment should raise TypeError when the field holds a list."""
    doc = {'items': [1, 2, 3]}
    with pytest.raises(TypeError):
        increment('items')(doc)

def test_transform_returns_none():
    """The transform returned by increment should return None and mutate the doc in place."""
    doc = {'count': 5}
    result = increment('count')(doc)
    assert result is None
    assert doc == {'count': 6}
