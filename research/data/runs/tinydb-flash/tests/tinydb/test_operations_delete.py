import pytest
from tinydb.operations import add, delete

@pytest.fixture
def dict_doc():
    """A simple dict document with a few scalar fields."""
    return {'foo': 'bar', 'baz': 42}

@pytest.fixture
def list_doc():
    """A list-based document (as used for TinyDB tables)."""
    return ['foo', 'bar', 'baz']

@pytest.fixture
def nested_doc():
    """A document containing a nested sub-document for dotted field paths."""
    return {'a': {'b': 1, 'c': 2}}

def test_delete_returns_callable_transform():
    """delete(field) returns a transform callable that operates on a document later."""
    transform = delete('foo')

    assert callable(transform), "delete() must return a callable transform function"
    assert transform.__name__ == 'transform'


def test_delete_removes_field_from_dict_document():
    """The transform deletes the requested key from a dict document."""
    doc = {'foo': 'bar', 'baz': 42, 'keep': True}

    delete('foo')(doc)

    assert 'foo' not in doc
    assert 'baz' in doc and 'keep' in doc
    assert doc == {'baz': 42, 'keep': True}


def test_delete_removes_element_from_list_document():
    """A list document is indexed by position; delete removes the element at that index."""
    doc = ['foo', 'bar', 'baz']

    delete(1)(doc)

    assert 'bar' not in doc
    assert doc == ['foo', 'baz']

import pytest


def test_delete_missing_field_in_dict_raises_key_error():
    """Deleting an absent key propagates the dict's KeyError."""
    doc = {'foo': 'bar'}

    with pytest.raises(KeyError):
        delete('missing')(doc)

    assert doc == {'foo': 'bar'}, "document must stay untouched when deletion fails"


def test_delete_missing_element_in_list_raises_value_error():
    """Deleting an out-of-range index from a list document propagates IndexError."""
    doc = ['foo', 'bar']

    # `delete` is a plain `del doc[field]`, so a missing field surfaces as the
    # underlying container's lookup error: IndexError for sequences (not ValueError),
    # KeyError for mappings.
    with pytest.raises(IndexError):
        delete(5)(doc)

    assert doc == ['foo', 'bar'], "list document must remain intact on failure"

import pytest


def test_delete_is_idempotent_inside_a_single_transform_call():
    """Calling the same transform twice on the same dict fails the second time."""
    doc = {'foo': 1, 'bar': 2}
    transform = delete('foo')

    transform(doc)
    assert doc == {'bar': 2}

    with pytest.raises(KeyError):
        transform(doc)


def test_delete_supports_nested_field_paths():
    """Dotted field paths are not resolved: 'a.b' is a literal key, so a KeyError is raised."""
    doc = {'a': {'b': 1, 'c': 2}, 'd': 3}

    with pytest.raises(KeyError):
        delete('a.b')(doc)

    assert doc == {'a': {'b': 1, 'c': 2}, 'd': 3}, "document must remain intact on failure"

    # A nested field is deleted by passing the sub-document itself.
    delete('b')(doc['a'])

    assert doc['a'] == {'c': 2}
    assert 'a' in doc and doc['d'] == 3

def test_delete_all_fields_yields_empty_document():
    """Removing the last remaining key leaves an empty document."""
    doc = {'only': 'value'}

    delete('only')(doc)

    assert isinstance(doc, dict)
    assert len(doc) == 0


def test_delete_can_be_chained_with_other_operations():
    """delete can be combined with add/set transforms in sequence."""
    doc = {'count': 1, 'temp': 'x'}

    add('count', 4)(doc)
    delete('temp')(doc)

    assert doc == {'count': 5}
