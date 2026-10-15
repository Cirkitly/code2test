import pytest
from tinydb.operations import subtract

def test_subtract_returns_callable_transform():
    """`subtract` should return a callable transform that closes over field and n."""
    transform = subtract("count", 1)
    assert callable(transform)


def test_subtract_decrements_field_by_n():
    """The primary behavior: subtracting n reduces the field's value by n."""
    doc = {"count": 10}
    transform = subtract("count", 3)
    transform(doc)
    assert doc["count"] == 7


def test_subtract_supports_float_values():
    """Subtracting a float should produce a correct float result."""
    doc = {"value": 5.5}
    transform = subtract("value", 2.0)
    transform(doc)
    assert doc["value"] == 3.5
    assert isinstance(doc["value"], float)


def test_subtract_by_zero_leaves_field_unchanged():
    """Edge case: subtracting zero leaves the field untouched."""
    doc = {"count": 42}
    transform = subtract("count", 0)
    transform(doc)
    assert doc["count"] == 42


def test_subtract_negative_n_increases_field():
    """Edge case: subtracting a negative number should increase the field value."""
    doc = {"count": 10}
    transform = subtract("count", -5)
    transform(doc)
    assert doc["count"] == 15


def test_subtract_mutates_document_in_place_and_returns_none():
    """The transform should mutate the doc in place and implicitly return None."""
    doc = {"count": 10, "name": "foo"}
    transform = subtract("count", 3)
    result = transform(doc)
    assert result is None
    assert doc == {"count": 7, "name": "foo"}


def test_subtract_transform_is_reusable_across_documents():
    """A single transform instance should correctly modify multiple documents."""
    transform = subtract("count", 2)
    doc1 = {"count": 10, "id": 1}
    doc2 = {"count": 20, "id": 2}
    transform(doc1)
    transform(doc2)
    assert doc1["count"] == 8
    assert doc2["count"] == 18
    assert doc1["id"] == 1
    assert doc2["id"] == 2


def test_subtract_raises_keyerror_when_field_missing():
    """Subtracting from a missing field should raise KeyError."""
    doc = {"other": 10}
    transform = subtract("count", 1)
    with pytest.raises(KeyError):
        transform(doc)


def test_subtract_raises_typeerror_on_non_numeric_field():
    """Subtracting a number from a string field should raise TypeError."""
    doc = {"name": "foo"}
    transform = subtract("name", 1)
    with pytest.raises(TypeError):
        transform(doc)


def test_subtract_does_not_affect_other_fields():
    """Other fields in the document should be untouched by the transform."""
    doc = {"count": 10, "name": "foo", "tags": ["a", "b"], "nested": {"k": 1}}
    transform = subtract("count", 3)
    transform(doc)
    assert doc == {
        "count": 7,
        "name": "foo",
        "tags": ["a", "b"],
        "nested": {"k": 1},
    }


def test_subtract_only_targets_specified_field():
    """Only the field passed to `subtract` is decremented; other numeric fields are untouched."""
    doc = {"a": 100, "b": 200, "c": 300}
    transform = subtract("b", 50)
    transform(doc)
    assert doc == {"a": 100, "b": 150, "c": 300}

