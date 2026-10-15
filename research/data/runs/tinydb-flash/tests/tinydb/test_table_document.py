import pytest
from tinydb.table import Document

def test_document_content_is_accessible_as_a_mapping():
    doc = Document({'name': 'John', 'age': 30}, doc_id=1)

    assert doc['name'] == 'John'
    assert doc['age'] == 30
    assert set(doc.keys()) == {'name', 'age'}
    assert dict(doc) == {'name': 'John', 'age': 30}
    assert doc.get('missing') is None

def test_document_doc_id_attribute_holds_the_given_id():
    doc = Document({'char': 'v'}, doc_id=42)

    assert doc.doc_id == 42
    assert isinstance(doc.doc_id, int)

def test_document_doc_id_is_not_part_of_the_dict_content():
    doc = Document({'name': 'John'}, doc_id=7)

    assert 'doc_id' not in doc
    assert 'doc_id' not in list(doc.keys())
    assert 7 not in list(doc.values())
    assert ('doc_id', 7) not in list(doc.items())

def test_document_length_counts_only_content_fields():
    doc = Document({'a': 1, 'b': 2, 'c': 3}, doc_id=99)

    assert len(doc) == 3

def test_document_equals_plain_dict_with_same_content():
    doc = Document({'name': 'John', 'age': 30}, doc_id=1)

    assert doc == {'name': 'John', 'age': 30}

def test_document_supports_normal_dict_mutation_methods():
    doc = Document({'a': 1}, doc_id=5)

    doc['b'] = 2
    doc.update({'c': 3})

    assert dict(doc) == {'a': 1, 'b': 2, 'c': 3}
    assert doc.pop('c') == 3
    assert dict(doc) == {'a': 1, 'b': 2}
    assert doc.doc_id == 5

def test_document_accepts_an_empty_mapping():
    doc = Document({}, doc_id=3)

    assert len(doc) == 0
    assert dict(doc) == {}
    assert doc.doc_id == 3

def test_document_from_mapping_constructor_is_usable_as_an_iterable():
    doc = Document({'a': 1, 'b': 2}, doc_id=0)

    pairs = list(doc.items())

    assert sorted(pairs) == [('a', 1), ('b', 2)]

def test_document_is_a_dict_subclass():
    doc = Document({'a': 1}, doc_id=1)

    assert isinstance(doc, dict)

def test_document_stores_nested_values_by_reference():
    nested = {'inner': [1, 2]}
    doc = Document({'nested': nested}, doc_id=1)

    nested['inner'].append(3)

    assert doc['nested']['inner'] == [1, 2, 3]

def test_document_mutation_of_original_mapping_does_not_affect_document():
    source = {'a': 1}
    doc = Document(source, doc_id=1)

    source['a'] = 99
    source['b'] = 2

    assert dict(doc) == {'a': 1}
    assert len(doc) == 1

def test_document_accessing_a_missing_key_raises_key_error():
    doc = Document({'a': 1}, doc_id=1)

    with pytest.raises(KeyError):
        doc['does_not_exist']

def test_document_pop_without_default_raises_key_error():
    doc = Document({'a': 1}, doc_id=1)

    with pytest.raises(KeyError):
        doc.pop('missing')

def test_document_unhashable_like_a_plain_dict():
    doc = Document({'a': 1}, doc_id=1)

    with pytest.raises(TypeError):
        hash(doc)

def test_document_equality_ignores_doc_id():
    doc_a = Document({'a': 1}, doc_id=1)
    doc_b = Document({'a': 1}, doc_id=2)

    assert doc_a == doc_b
    assert doc_a.doc_id == 1
    assert doc_b.doc_id == 2

def test_document_id_is_exposed_via_get_with_default():
    doc = Document({'a': 1}, doc_id=17)

    assert doc.get('doc_id', None) is None
    assert doc.doc_id == 17
