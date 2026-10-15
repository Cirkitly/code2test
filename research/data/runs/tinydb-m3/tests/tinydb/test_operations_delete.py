import pytest
from tinydb.operations import delete

import pytest

from tinydb.operations import delete


def test_delete_returns_callable_transform():
    transform = delete('name')

    assert callable(transform)

import pytest

from tinydb.operations import delete


def test_delete_removes_specified_field_from_document():
    document = {'name': 'Alice', 'age': 30, 'city': 'Wonderland'}

    transform = delete('age')
    transform(document)

    assert 'age' not in document
    assert document == {'name': 'Alice', 'city': 'Wonderland'}

import pytest

from tinydb.operations import delete


def test_delete_transform_returns_none():
    document = {'name': 'Alice'}

    transform = delete('name')
    result = transform(document)

    assert result is None

import pytest

from tinydb.operations import delete


def test_delete_modifies_document_in_place():
    document = {'name': 'Alice', 'age': 30}
    document_id = id(document)

    delete('age')(document)

    # The object identity is unchanged; the original dict was mutated in place.
    assert id(document) == document_id
    assert 'age' not in document

import pytest

from tinydb.operations import delete


def test_delete_only_removes_specified_field_preserving_others():
    document = {
        'name': 'Alice',
        'age': 30,
        'city': 'Wonderland',
        'email': 'alice@example.com',
    }
    original_other_fields = {
        'name': 'Alice',
        'city': 'Wonderland',
        'email': 'alice@example.com',
    }

    delete('age')(document)

    assert 'age' not in document
    assert document == original_other_fields

import pytest

from tinydb.operations import delete


def test_delete_raises_keyerror_for_missing_field():
    document = {'name': 'Alice'}
    transform = delete('nonexistent')

    with pytest.raises(KeyError):
        transform(document)

import pytest

from tinydb.operations import delete


def test_delete_raises_keyerror_on_empty_document():
    document = {}

    with pytest.raises(KeyError):
        delete('any_field')(document)

import pytest

from tinydb.operations import delete


def test_delete_factory_does_not_mutate_until_transform_called():
    document = {'name': 'Alice', 'age': 30}

    # Calling the factory alone should not touch the document.
    _ = delete('age')

    assert document == {'name': 'Alice', 'age': 30}

import pytest

from tinydb.operations import delete


def test_delete_can_be_reused_across_multiple_documents():
    transform = delete('temp_field')

    doc1 = {'temp_field': 1, 'value': 'a'}
    doc2 = {'temp_field': 2, 'value': 'b'}

    transform(doc1)
    transform(doc2)

    assert 'temp_field' not in doc1
    assert 'temp_field' not in doc2
    assert doc1 == {'value': 'a'}
    assert doc2 == {'value': 'b'}

import pytest

from tinydb.operations import delete


def test_delete_field_value_can_be_any_type_including_none():
    document = {
        'none_field': None,
        'zero_field': 0,
        'empty_str_field': '',
        'empty_list_field': [],
        'empty_dict_field': {},
        'keep_field': 'keep_me',
    }

    delete('none_field')(document)
    delete('zero_field')(document)
    delete('empty_str_field')(document)
    delete('empty_list_field')(document)
    delete('empty_dict_field')(document)

    assert document == {'keep_field': 'keep_me'}
