import pytest
from tinydb.table import Document

import pytest

from tinydb.table import Document


def test_document_is_a_dict_subclass():
    doc = Document({'name': 'John'}, 1)

    assert isinstance(doc, dict)
    assert doc == {'name': 'John'}

import pytest

from tinydb.table import Document


def test_document_exposes_doc_id():
    doc = Document({'name': 'John'}, 42)

    assert doc.doc_id == 42

import pytest

from tinydb.table import Document


def test_document_copies_content_from_mapping():
    doc = Document({'name': 'John', 'age': 22, 'tags': ['a', 'b']}, 1)

    assert doc['name'] == 'John'
    assert doc['age'] == 22
    assert doc['tags'] == ['a', 'b']
    assert len(doc) == 3

import pytest

from tinydb.table import Document
from tinydb.utils import FrozenDict


def test_document_accepts_any_mapping():
    source = FrozenDict({'name': 'John'})

    doc = Document(source, 7)

    assert doc == {'name': 'John'}
    assert doc.doc_id == 7
    # The original mapping is untouched and still immutable
    with pytest.raises(TypeError):
        source['name'] = 'Jane'

import pytest

from tinydb.table import Document


def test_document_with_empty_mapping():
    doc = Document({}, 3)

    assert len(doc) == 0
    assert doc == {}
    assert doc.doc_id == 3

import pytest

from tinydb.table import Document


def test_document_doc_id_is_not_part_of_the_mapping():
    doc = Document({'name': 'John'}, 12)

    assert 'doc_id' not in doc
    assert list(doc.keys()) == ['name']
    assert len(doc) == 1

import pytest

from tinydb.table import Document


def test_document_supports_mapping_operations():
    doc = Document({'a': 1, 'b': 2}, 1)

    assert doc.get('a') == 1
    assert doc.get('missing') is None
    assert 'b' in doc
    assert sorted(doc.keys()) == ['a', 'b']
    assert sorted(doc.values()) == [1, 2]
    assert sorted(doc.items()) == [('a', 1), ('b', 2)]
    assert list(iter(doc)) == ['a', 'b']

import pytest

from tinydb.table import Document


def test_document_is_mutable_after_construction():
    doc = Document({'name': 'John'}, 5)

    doc['age'] = 22
    doc['name'] = 'Jane'

    assert doc['age'] == 22
    assert doc['name'] == 'Jane'

    del doc['age']

    assert 'age' not in doc
    assert doc.doc_id == 5

import pytest

from tinydb.table import Document


def test_document_instances_have_independent_doc_ids():
    first = Document({'value': 1}, 1)
    second = Document({'value': 1}, 2)

    assert first.doc_id == 1
    assert second.doc_id == 2
    assert first is not second

import pytest

from tinydb.table import Document


def test_document_supports_zero_doc_id():
    doc = Document({'name': 'John'}, 0)

    assert doc.doc_id == 0
    assert doc.doc_id is not None

import pytest

from tinydb.table import Document


def test_document_supports_negative_doc_id():
    doc = Document({'name': 'John'}, -3)

    assert doc.doc_id == -3

import pytest

from tinydb.table import Document


def test_document_supports_large_doc_id():
    big_id = 2 ** 63

    doc = Document({'name': 'John'}, big_id)

    assert doc.doc_id == big_id

import pytest

from tinydb.table import Document


def test_document_copies_content_instead_of_aliasing_the_source_mapping():
    source = {'name': 'John'}
    doc = Document(source, 1)

    source['name'] = 'Jane'

    assert doc['name'] == 'John'

import pytest

from tinydb.table import Document


def test_document_missing_key_raises_key_error():
    doc = Document({'name': 'John'}, 1)

    with pytest.raises(KeyError):
        doc['does_not_exist']

def test_document_requires_mapping_value():
    # Document.__init__ forwards `value` to dict(), which accepts any
    # iterable of key/value pairs -- no runtime type check is performed.
    doc = Document([('name', 'John')], 1)

    assert doc == {'name': 'John'}
    assert doc.doc_id == 1

import pytest

from tinydb.table import Document


def test_document_requires_two_arguments():
    with pytest.raises(TypeError):
        Document()

    with pytest.raises(TypeError):
        Document({'name': 'John'})

import pytest

from tinydb.table import Document
from tinydb.queries import QueryInstance


def test_document_used_as_mapping_by_query_instance():
    doc = Document({'name': 'John'}, 1)
    query = QueryInstance(lambda value: value['name'] == 'John', None)

    assert query(doc) is True

import pytest

from tinydb.table import Document, Table
from tinydb.storages import MemoryStorage


def test_document_returned_by_table_all_carries_doc_id():
    table = Table(MemoryStorage(), 'people')
    table.insert({'name': 'John'})
    table.insert({'name': 'Jane'})

    docs = table.all()

    assert all(isinstance(doc, Document) for doc in docs)
    assert len(docs) == 2
    assert {doc['name'] for doc in docs} == {'John', 'Jane'}
    assert sorted(doc.doc_id for doc in docs) == [1, 2]

import pytest

from tinydb.table import Document, Table
from tinydb.storages import MemoryStorage


def test_document_returned_by_table_get():
    table = Table(MemoryStorage(), 'people')
    doc_id = table.insert({'name': 'John', 'age': 22})

    doc = table.get(doc_id=doc_id)

    assert isinstance(doc, Document)
    assert doc.doc_id == doc_id
    assert doc == {'name': 'John', 'age': 22}
    assert table.get(doc_id=doc_id + 100) is None
