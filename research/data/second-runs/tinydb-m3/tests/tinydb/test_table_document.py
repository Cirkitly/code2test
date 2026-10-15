import pytest
from tinydb.table import Document

def test_document_creation_stores_content_and_doc_id():
    """
    Primary happy path: a Document is constructed with a mapping and a
    doc_id. The mapping's content is accessible as a dict and the doc_id
    is accessible as an instance attribute.
    """
    value = {"name": "John", "age": 30}
    doc = Document(value, 42)

    assert doc.doc_id == 42
    assert dict(doc) == {"name": "John", "age": 30}


def test_document_provides_access_to_content_and_id():
    """
    The intent of Document is to provide a way to access both a document's
    content and its ID. The content is accessed via dict-style indexing and
    the ID via the ``doc_id`` attribute.
    """
    doc = Document({"name": "Alice"}, 5)

    # Access content via dict-style indexing
    assert doc["name"] == "Alice"
    # Access ID via the doc_id attribute
    assert doc.doc_id == 5


def test_document_is_a_dict_subclass():
    """Document is a subclass of dict, so it is a mapping itself."""
    doc = Document({}, 1)

    assert isinstance(doc, dict)


def test_document_content_is_independent_of_input_mapping():
    """
    The Document's internal storage is initialized from the input mapping
    via ``super().__init__(value)``, which creates a new dict rather than
    holding a reference. Mutating the input must not affect the Document.
    """
    original = {"a": 1, "b": 2}
    doc = Document(original, 1)

    original["c"] = 3

    assert "c" not in doc
    assert len(doc) == 2
    assert dict(doc) == {"a": 1, "b": 2}


def test_document_get_item_returns_value():
    """Document supports dict-style item access via ``__getitem__``."""
    doc = Document({"key": "value"}, 1)

    assert doc["key"] == "value"


def test_document_raises_keyerror_for_missing_key():
    """
    Accessing a non-existent key raises ``KeyError``, consistent with
    dict's behavior.
    """
    doc = Document({"key": "value"}, 1)

    with pytest.raises(KeyError):
        _ = doc["missing"]


def test_document_supports_in_operator():
    """Document supports the ``in`` operator to check for key existence."""
    doc = Document({"key": "value"}, 1)

    assert "key" in doc
    assert "missing" not in doc


def test_document_supports_iteration_over_keys():
    """Iterating over a Document yields its keys, like a dict."""
    doc = Document({"a": 1, "b": 2, "c": 3}, 1)

    assert set(doc) == {"a", "b", "c"}


def test_document_supports_len():
    """Document supports ``len()`` returning the number of items."""
    doc = Document({"a": 1, "b": 2, "c": 3}, 1)

    assert len(doc) == 3


def test_document_with_empty_mapping():
    """A Document can wrap an empty mapping; doc_id is still accessible."""
    doc = Document({}, 7)

    assert doc.doc_id == 7
    assert len(doc) == 0
    assert dict(doc) == {}


def test_document_with_zero_doc_id():
    """
    Edge case: ``doc_id`` can be zero. The value must be preserved
    faithfully even though 0 is falsy in Python.
    """
    doc = Document({"key": "value"}, 0)

    assert doc.doc_id == 0
    assert "key" in doc


def test_document_preserves_nested_data():
    """
    Document stores the mapping's content as-is, so nested data structures
    are preserved and remain accessible through chained indexing.
    """
    nested = {"user": {"name": "Alice", "tags": ["admin", "user"]}}
    doc = Document(nested, 100)

    assert doc["user"]["name"] == "Alice"
    assert "admin" in doc["user"]["tags"]
    assert len(doc["user"]["tags"]) == 2


def test_document_supports_item_mutation():
    """
    Document inherits dict's mutability. Items can be added and updated
    through standard dict operations.
    """
    doc = Document({"a": 1}, 1)

    doc["b"] = 2
    doc["a"] = 10

    assert doc["a"] == 10
    assert doc["b"] == 2
    assert len(doc) == 2


def test_document_raises_typeerror_when_value_not_mapping():
    """
    The constructor requires a Mapping for ``value``. Passing a non-mapping,
    non-iterable value causes ``dict.__init__`` to raise ``TypeError``.
    """
    with pytest.raises(TypeError):
        Document(123, 1)


def test_document_equality_ignores_doc_id():
    """
    Two Documents with the same content compare equal regardless of their
    ``doc_id`` values, because ``doc_id`` is an instance attribute and not
    part of the dict's items.
    """
    doc1 = Document({"a": 1}, 1)
    doc2 = Document({"a": 1}, 999)  # same content, different doc_id

    assert doc1 == doc2
    assert doc1.doc_id != doc2.doc_id  # doc_ids differ, but equality is on content


def test_document_equal_to_plain_dict_with_same_content():
    """
    Because Document is a dict subclass, a Document with the same items
    as a plain dict compares equal to it.
    """
    doc = Document({"a": 1, "b": 2}, 99)

    assert doc == {"a": 1, "b": 2}

