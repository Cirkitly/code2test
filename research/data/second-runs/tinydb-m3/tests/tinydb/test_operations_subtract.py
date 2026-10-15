from tinydb.operations import subtract
import pytest

def test_subtract_basic():
    """Subtracting a positive n from a numeric field reduces the field by n."""
    transform = subtract('count', 5)
    doc = {'count': 10}

    transform(doc)

    assert doc == {'count': 5}

def test_subtract_returns_callable_transform():
    """subtract() returns a callable that performs the operation on a document."""
    transform = subtract('count', 5)

    assert callable(transform)

def test_subtract_modifies_doc_in_place_and_returns_none():
    """The transform mutates the dict in place and returns None."""
    transform = subtract('count', 3)
    doc = {'count': 10}

    result = transform(doc)

    assert result is None
    assert doc == {'count': 7}

def test_subtract_with_zero_leaves_value_unchanged():
    """Subtracting 0 is a no-op on the field value."""
    transform = subtract('count', 0)
    doc = {'count': 42}

    transform(doc)

    assert doc == {'count': 42}

def test_subtract_with_negative_n_effectively_adds():
    """Subtracting a negative n is equivalent to adding |n|."""
    transform = subtract('count', -3)
    doc = {'count': 10}

    transform(doc)

    assert doc == {'count': 13}

def test_subtract_with_float_preserves_float_arithmetic():
    """Subtracting works with float field values and float n."""
    transform = subtract('price', 2.5)
    doc = {'price': 10.0}

    transform(doc)

    assert doc['price'] == 7.5

def test_subtract_missing_field_raises_key_error():
    """A missing target field raises KeyError on subtraction."""
    transform = subtract('count', 5)
    doc = {'other': 10}

    with pytest.raises(KeyError):
        transform(doc)

def test_subtract_non_numeric_field_raises_type_error():
    """A non-numeric field raises TypeError on subtraction."""
    transform = subtract('name', 5)
    doc = {'name': 'Alice'}

    with pytest.raises(TypeError):
        transform(doc)

def test_subtract_on_list_field_raises_type_error():
    """A list field raises TypeError on subtraction."""
    transform = subtract('items', 1)
    doc = {'items': [1, 2, 3]}

    with pytest.raises(TypeError):
        transform(doc)

def test_subtract_transform_is_reusable_across_documents():
    """The returned transform can be reused on multiple documents."""
    transform = subtract('count', 2)
    doc1 = {'count': 10}
    doc2 = {'count': 20}

    transform(doc1)
    transform(doc2)

    assert doc1 == {'count': 8}
    assert doc2 == {'count': 18}
