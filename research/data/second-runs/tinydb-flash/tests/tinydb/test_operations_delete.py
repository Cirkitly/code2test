import pytest
from tinydb.operations import delete

@pytest.fixture
def sample_document():
    """A simple flat document used by a few of the delete tests."""
    return {'name': 'John', 'age': 30, 'city': 'Berlin'}

import pytest

from tinydb.operations import delete


def test_delete_removes_the_given_field_from_the_document():
    """The primary happy path: the requested field is gone after the transform runs."""
    doc = {'name': 'John', 'age': 30, 'city': 'Berlin'}

    transform = delete('age')
    transform(doc)

    assert 'age' not in doc

import pytest

from tinydb.operations import delete


def test_delete_keeps_all_other_fields_untouched():
    """Deleting one field must not affect any of the other fields of the document."""
    doc = {'name': 'John', 'age': 30, 'city': 'Berlin'}

    delete('age')(doc)

    assert doc == {'name': 'John', 'city': 'Berlin'}

import pytest

from tinydb.operations import delete


def test_delete_mutates_the_document_in_place_and_returns_none():
    """The transform returns None and modifies the very dict instance it received."""
    doc = {'name': 'John', 'age': 30}

    result = delete('age')(doc)

    assert result is None
    assert 'age' not in doc

import pytest

from tinydb.operations import delete


@pytest.mark.parametrize('field', ['none_value', 'zero_value', 'empty_string', 'empty_list', 'false_value'])
def test_delete_removes_field_regardless_of_its_value(field):
    """A field is deleted based on its key existing, independent of the stored value."""
    doc = {
        'none_value': None,
        'zero_value': 0,
        'empty_string': '',
        'empty_list': [],
        'false_value': False,
        'keep': 'me',
    }

    delete(field)(doc)

    assert field not in doc
    assert doc['keep'] == 'me'

import pytest

from tinydb.operations import delete


def test_delete_raises_key_error_when_field_does_not_exist():
    """Error condition: the document has no such field, so deletion fails loudly."""
    doc = {'name': 'John', 'age': 30}

    with pytest.raises(KeyError) as exc_info:
        delete('missing')(doc)

    assert exc_info.value.args[0] == 'missing'

import pytest

from tinydb.operations import delete


def test_delete_raises_key_error_on_empty_document():
    """Deleting from an empty document cannot succeed and raises KeyError."""
    doc = {}

    with pytest.raises(KeyError):
        delete('anything')(doc)

    assert doc == {}

import pytest

from tinydb.operations import delete


def test_delete_leaves_document_unchanged_when_field_is_missing():
    """When the KeyError is raised the document keeps all of its original content."""
    doc = {'name': 'John', 'age': 30}

    with pytest.raises(KeyError):
        delete('nickname')(doc)

    assert doc == {'name': 'John', 'age': 30}

import pytest

from tinydb.operations import delete


def test_delete_field_can_be_an_integer_key():
    """The field argument is used directly as a dict key, so non-string keys work too."""
    doc = {1: 'one', 2: 'two'}

    delete(1)(doc)

    assert 1 not in doc
    assert doc == {2: 'two'}

import pytest

from tinydb.operations import delete


def test_delete_with_unhashable_field_raises_type_error():
    """Error condition: an unhashable 'field' cannot be deleted from a dict."""
    doc = {'a': 1}

    with pytest.raises(TypeError):
        delete(['a'])(doc)

    assert doc == {'a': 1}

import pytest

from tinydb.operations import delete


def test_delete_removes_only_the_top_level_key_matching_the_name():
    """delete(field) addresses the top-level key only, it does not recurse into nested dicts."""
    doc = {'user': {'name': 'John'}, 'name': 'document name'}

    delete('name')(doc)

    assert 'name' not in doc
    assert doc == {'user': {'name': 'John'}}

import pytest

from tinydb.operations import delete


def test_delete_removes_a_parent_key_together_with_its_nested_content():
    """Deleting a key holding a nested document discards that entire sub-document."""
    doc = {'user': {'name': 'John', 'tags': ['a', 'b']}, 'active': True}

    delete('user')(doc)

    assert 'user' not in doc
    assert doc == {'active': True}

import pytest

from tinydb.operations import delete, set


def test_delete_can_be_chained_with_other_operations():
    """Transforms are plain callables over the document and can be applied one after another."""
    doc = {'name': 'John'}

    set('age', 30)(doc)
    delete('name')(doc)

    assert doc == {'age': 30}

import pytest

from tinydb.operations import delete


def test_delete_works_on_a_dict_subclass_and_preserves_its_type():
    """Any mapping supporting 'del obj[key]' can be used; the instance type is unchanged."""
    class Doc(dict):
        pass

    doc = Doc({'name': 'John', 'age': 30})

    delete('age')(doc)

    assert isinstance(doc, Doc)
    assert 'age' not in doc
    assert doc['name'] == 'John'

import pytest

from tinydb.operations import delete


def test_delete_can_be_applied_to_independent_documents_reusing_one_transform():
    """The returned transform is a reusable function, not a one-shot closure over a document."""
    transform = delete('age')

    first = {'age': 30, 'name': 'John'}
    second = {'age': 40, 'name': 'Jane'}

    transform(first)
    transform(second)

    assert first == {'name': 'John'}
    assert second == {'name': 'Jane'}

import pytest

from tinydb.operations import delete


def test_delete_twice_on_the_same_field_raises_key_error_on_second_call():
    """Deleting is not idempotent: the second deletion of the same field fails."""
    doc = {'age': 30}

    delete('age')(doc)

    with pytest.raises(KeyError):
        delete('age')(doc)
