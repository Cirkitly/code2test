from tinydb.table import Document
from collections.abc import Mapping
import pytest

def test_document_stores_value_and_doc_id():
    """A Document stores its mapping value as dict contents and exposes doc_id."""
    doc = Document({"name": "Alice", "age": 30}, doc_id=42)

    # Content is accessible like a dict
    assert doc["name"] == "Alice"
    assert doc["age"] == 30

    # doc_id is accessible as an attribute
    assert doc.doc_id == 42

def test_document_is_a_dict_subclass():
    """Document is a dict subclass and behaves as a Mapping."""
    doc = Document({"a": 1}, doc_id=1)

    assert isinstance(doc, dict)
    assert isinstance(doc, Mapping)

def test_document_supports_basic_dict_operations():
    """Document supports len, get (with default), membership, and iteration over keys."""
    doc = Document({"a": 1, "b": 2}, doc_id=1)

    assert len(doc) == 2
    assert doc.get("a") == 1
    assert doc.get("missing", "default") == "default"
    assert "a" in doc
    assert "missing" not in doc
    assert set(iter(doc)) == {"a", "b"}

def test_document_keys_values_items_methods():
    """Document's keys(), values(), and items() reflect the contents passed to the constructor."""
    doc = Document({"a": 1, "b": 2}, doc_id=1)

    assert set(doc.keys()) == {"a", "b"}
    assert set(doc.values()) == {1, 2}
    assert set(doc.items()) == {("a", 1), ("b", 2)}

def test_document_with_empty_mapping():
    """A Document with an empty mapping behaves like an empty dict but still has doc_id."""
    doc = Document({}, doc_id=0)

    assert len(doc) == 0
    assert list(doc.keys()) == []
    assert doc == {}
    assert doc.doc_id == 0

def test_document_equality_ignores_doc_id():
    """Two Documents with identical contents are equal even when doc_ids differ."""
    doc1 = Document({"a": 1, "b": 2}, doc_id=1)
    doc2 = Document({"a": 1, "b": 2}, doc_id=999)

    assert doc1 == doc2

def test_document_equality_with_plain_dict_when_contents_match():
    """A Document compares equal to a plain dict with the same contents."""
    doc = Document({"a": 1, "b": 2}, doc_id=7)

    assert doc == {"a": 1, "b": 2}

def test_document_allows_item_mutation():
    """Document supports item assignment and deletion."""
    doc = Document({"a": 1}, doc_id=1)

    doc["b"] = 2
    assert doc["b"] == 2
    assert len(doc) == 2

    doc["a"] = 10
    assert doc["a"] == 10

    del doc["a"]
    assert "a" not in doc
    assert len(doc) == 1

def test_document_supports_pop():
    """Document supports dict's pop method, with and without a default."""
    doc = Document({"a": 1, "b": 2}, doc_id=1)

    assert doc.pop("a") == 1
    assert "a" not in doc

    assert doc.pop("missing", "default") == "default"

def test_document_content_independent_of_source_mapping():
    """Mutating a Document does not affect the original mapping passed in."""
    source = {"a": 1, "b": 2}
    doc = Document(source, doc_id=1)

    doc["c"] = 3
    doc["a"] = 100

    # Source unchanged
    assert source == {"a": 1, "b": 2}

    # Document reflects mutations
    assert doc == {"a": 100, "b": 2, "c": 3}

@pytest.mark.parametrize("doc_id", [0, 1, -1, 10**9])
def test_document_supports_various_doc_id_values(doc_id):
    """doc_id is stored verbatim for any integer value, including zero, negative, and large."""
    doc = Document({"x": 1}, doc_id=doc_id)

    assert doc.doc_id == doc_id
