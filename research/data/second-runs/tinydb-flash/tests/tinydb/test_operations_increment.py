import pytest
from collections import defaultdict
from tinydb.operations import increment
from tinydb.operations import add

@pytest.fixture
def sample_doc():
    """A minimal document holding a single integer field named ``counter``."""
    return {'counter': 0}


@pytest.fixture
def rich_doc():
    """A document with several fields of different types, used to check that
    ``increment`` only touches the requested field."""
    return {'counter': 41, 'name': 'alice', 'ratio': 1.5, 'flag': True}

def test_increment_returns_a_callable_transform():
    transform = increment('counter')

    assert callable(transform)


def test_increment_adds_one_to_the_given_field(sample_doc):
    transform = increment('counter')

    transform(sample_doc)

    assert sample_doc['counter'] == 1


def test_increment_is_relative_to_the_current_value(sample_doc):
    sample_doc['counter'] = 7

    increment('counter')(sample_doc)

    assert sample_doc['counter'] == 8


def test_increment_supports_negative_values():
    doc = {'counter': -3}

    increment('counter')(doc)

    assert doc['counter'] == -2


def test_increment_mutates_the_document_in_place(sample_doc):
    doc_before = dict(sample_doc)

    increment('counter')(sample_doc)

    assert sample_doc != doc_before


def test_increment_transform_returns_none(sample_doc):
    transform = increment('counter')

    result = transform(sample_doc)

    assert result is None


def test_increment_applied_twice_adds_two(sample_doc):
    transform = increment('counter')

    transform(sample_doc)
    transform(sample_doc)

    assert sample_doc['counter'] == 2


def test_increment_does_not_add_new_fields_to_the_document(rich_doc):
    fields_before = set(rich_doc)

    increment('counter')(rich_doc)

    assert set(rich_doc) == fields_before


def test_increment_leaves_other_fields_untouched(rich_doc):
    increment('counter')(rich_doc)

    assert rich_doc['name'] == 'alice'
    assert rich_doc['ratio'] == 1.5
    assert rich_doc['flag'] is True


def test_increment_only_changes_the_requested_field(rich_doc):
    increment('ratio')(rich_doc)

    assert rich_doc['ratio'] == 2.5
    assert rich_doc['counter'] == 41


def test_increment_works_for_float_fields():
    doc = {'ratio': 0.25}

    increment('ratio')(doc)

    assert doc['ratio'] == 1.25


def test_increment_works_for_boolean_fields():
    doc = {'flag': True}

    increment('flag')(doc)

    assert doc['flag'] == 2


def test_increment_composes_with_add_operation():
    doc = {'counter': 1}

    add('counter', 5)(doc)
    increment('counter')(doc)

    assert doc['counter'] == 7


def test_increment_on_missing_field_raises_key_error():
    doc = {'other': 1}

    with pytest.raises(KeyError):
        increment('missing')(doc)


def test_increment_on_empty_document_raises_key_error():
    with pytest.raises(KeyError):
        increment('counter')({})


def test_increment_on_nested_path_raises_key_error():
    doc = {'a': {'b': 1}}

    with pytest.raises(KeyError):
        increment('a.b')(doc)


def test_increment_on_string_field_raises_type_error():
    doc = {'name': 'alice'}

    with pytest.raises(TypeError):
        increment('name')(doc)


def test_increment_on_none_field_raises_type_error():
    doc = {'value': None}

    with pytest.raises(TypeError):
        increment('value')(doc)


def test_increment_on_list_field_raises_type_error():
    doc = {'items': [1, 2]}

    with pytest.raises(TypeError):
        increment('items')(doc)


def test_increment_with_auto_creating_mapping_creates_the_field():
    doc = defaultdict(int)

    increment('counter')(doc)

    assert doc['counter'] == 1
    assert 'counter' in doc


def test_increment_transform_is_reusable_across_documents():
    transform = increment('counter')

    first = {'counter': 1}
    second = {'counter': 10}

    transform(first)
    transform(second)

    assert first['counter'] == 2
    assert second['counter'] == 11


def test_increment_on_zero_initial_value_produces_one(sample_doc):
    sample_doc['counter'] = 0

    increment('counter')(sample_doc)

    assert sample_doc['counter'] == 1


def test_increment_preserves_document_field_types_after_increment():
    doc = {'ratio': 2.0}

    increment('ratio')(doc)

    assert isinstance(doc['ratio'], float)
    assert doc['ratio'] == 3.0


def test_increment_can_target_any_existing_key_name():
    doc = {'some odd key!': 4}

    increment('some odd key!')(doc)

    assert doc['some odd key!'] == 5
