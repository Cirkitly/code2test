import pytest
from tinydb.operations import delete

def test_delete_returns_a_transform_callable():
    """`delete(field)` must return a callable (the transform) that takes a document."""
    transform = delete("name")

    assert callable(transform)


def test_delete_removes_specified_field_from_document():
    """The primary intent: the transform deletes the named field from the document."""
    doc = {"name": "Alice", "age": 30}

    delete("name")(doc)

    assert "name" not in doc


def test_delete_preserves_other_fields_in_document():
    """Only the targeted field is removed; every other field and its value is preserved."""
    doc = {"name": "Alice", "age": 30, "email": "alice@example.com"}

    delete("age")(doc)

    assert doc == {"name": "Alice", "email": "alice@example.com"}


def test_delete_raises_keyerror_when_field_is_absent():
    """`del doc[field]` raises KeyError when the field is not present in the document."""
    doc = {"name": "Alice"}

    with pytest.raises(KeyError):
        delete("age")(doc)


def test_delete_raises_keyerror_on_empty_document():
    """An empty document has no fields to delete; the operation must raise KeyError."""
    doc = {}

    with pytest.raises(KeyError):
        delete("any_field")(doc)


def test_delete_modifies_document_in_place():
    """The transform mutates the document dict in place; the same object is updated."""
    doc = {"name": "Alice", "age": 30}
    original_object_id = id(doc)

    delete("age")(doc)

    assert id(doc) == original_object_id
    assert "age" not in doc


def test_delete_cannot_be_reapplied_after_field_removed():
    """After a successful deletion the field is gone; a second application must fail."""
    doc = {"name": "Alice"}
    transform = delete("name")

    transform(doc)

    with pytest.raises(KeyError):
        transform(doc)


@pytest.mark.parametrize(
    "field_name",
    ["simple", "with space", "with.dot", "trailing.", ".leading"],
)
def test_delete_treats_field_name_as_literal_dict_key(field_name):
    """`del doc[field]` looks up the field as a literal key, not as a nested path."""
    doc = {
        "simple": 1,
        "with space": 2,
        "with.dot": 3,
        "trailing.": 4,
        ".leading": 5,
    }
    other_keys = {k for k in doc if k != field_name}

    delete(field_name)(doc)

    assert field_name not in doc
    # All other keys (including those containing dots/spaces that share substrings)
    # must remain untouched.
    assert other_keys == set(doc)
    assert set(doc.keys()) == other_keys


def test_delete_transform_closes_over_field_name_at_creation():
    """Each transform remembers the field it was created with (closure behavior)."""
    doc = {"a": 1, "b": 2, "c": 3}
    delete_a = delete("a")
    delete_b = delete("b")

    delete_a(doc)

    assert doc == {"b": 2, "c": 3}

    delete_b(doc)

    assert doc == {"c": 3}

