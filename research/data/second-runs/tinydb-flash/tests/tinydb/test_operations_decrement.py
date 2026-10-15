import pytest
from collections import defaultdict
from fractions import Fraction
from tinydb.operations import decrement

@pytest.fixture
def sample_doc():
    """A plain ``dict`` document holding a numeric field to decrement."""
    return {'counter': 10, 'name': 'widget'}


@pytest.fixture
def nested_document():
    """A mapping that resolves dotted field paths, like TinyDB's ``Document``.

    ``Document`` is not importable from ``tinydb.utils`` in this project, so the
    double below implements exactly the dotted ``__getitem__``/``__setitem__``
    behaviour that ``decrement`` relies on when the field name contains a dot.
    """
    class Document(dict):
        def __getitem__(self, item):
            if '.' in item:
                first, rest = item.split('.', 1)
                return dict.__getitem__(self, first)[rest]
            return dict.__getitem__(self, item)

        def __setitem__(self, key, value):
            if '.' in key:
                first, rest = key.split('.', 1)
                dict.__getitem__(self, first)[rest] = value
            else:
                dict.__setitem__(self, key, value)

    return Document({'a': Document({'b': 3})})

def test_decrement_happy_path_decreases_field_by_one():
    """The primary intent: the targeted field's value is reduced by exactly 1."""
    transform = decrement('counter')
    doc = {'counter': 10}

    transform(doc)

    assert doc['counter'] == 9

def test_decrement_returns_a_callable_transform():
    """decrement(field) builds and returns a callable transform function."""
    transform = decrement('counter')

    assert callable(transform)

def test_decrement_transform_returns_none_and_mutates_in_place(sample_doc):
    """The transform mutates the given document in place and returns None."""
    transform = decrement('counter')

    assert transform(sample_doc) is None
    assert sample_doc['counter'] == 9

def test_decrement_leaves_other_fields_untouched():
    """Only the targeted field changes; every other field keeps its value."""
    doc = {'counter': 3, 'name': 'widget'}

    decrement('counter')(doc)

    assert doc == {'counter': 2, 'name': 'widget'}

def test_decrement_does_not_add_or_remove_keys(sample_doc):
    """Decrementing an existing field neither adds nor removes keys."""
    decrement('counter')(sample_doc)

    assert set(sample_doc.keys()) == {'counter', 'name'}
    assert len(sample_doc) == 2

def test_decrement_applied_repeatedly_subtracts_one_each_time():
    """Applying the same transform several times subtracts 1 each time."""
    doc = {'counter': 3}
    transform = decrement('counter')

    transform(doc)
    transform(doc)
    transform(doc)

    assert doc['counter'] == 0

def test_decrement_transform_can_be_reused_across_documents():
    """A single transform instance can be applied to several documents."""
    transform = decrement('counter')
    first = {'counter': 1}
    second = {'counter': 100}

    transform(first)
    transform(second)

    assert first['counter'] == 0
    assert second['counter'] == 99

def test_decrement_does_not_touch_document_until_transform_is_applied():
    """Creating the transform does not modify any document; only calling it does."""
    doc = {'counter': 5}

    transform = decrement('counter')

    assert doc['counter'] == 5

    transform(doc)

    assert doc['counter'] == 4

def test_decrement_supports_empty_string_field_name():
    """Any key may be used as the field name, including the empty string."""
    doc = {'': 5}

    decrement('')(doc)

    assert doc[''] == 4

@pytest.mark.parametrize('start, expected', [
    (0, -1),
    (1, 0),
    (42, 41),
    (-5, -6),
    (1.5, 0.5),
    (2.0, 1.0),
    (10 ** 18, 10 ** 18 - 1),
])
def test_decrement_subtracts_exactly_one_from_numbers(start, expected):
    """Integers, zero, negative numbers, floats and huge integers all lose exactly 1."""
    doc = {'counter': start}

    decrement('counter')(doc)

    assert doc['counter'] == expected

def test_decrement_treats_booleans_as_integers():
    """With '-= 1' semantics, True becomes 0 and False becomes -1."""
    true_doc = {'flag': True}
    decrement('flag')(true_doc)

    false_doc = {'flag': False}
    decrement('flag')(false_doc)

    assert true_doc['flag'] == 0
    assert false_doc['flag'] == -1

def test_decrement_preserves_numeric_type_of_the_field():
    """The field keeps its numeric type: Fraction(1, 2) - 1 stays a Fraction."""
    doc = {'counter': Fraction(1, 2)}

    decrement('counter')(doc)

    assert doc['counter'] == Fraction(-1, 2)

def test_decrement_on_defaultdict_treats_a_missing_field_as_zero():
    """A mapping that fabricates missing keys decrements 0 instead of raising."""
    doc = defaultdict(int)

    decrement('counter')(doc)

    assert doc['counter'] == -1

def test_decrement_nested_field_on_document(nested_document):
    """Dotted field paths address nested values of a dotted-path mapping."""
    decrement('a.b')(nested_document)

    assert nested_document['a']['b'] == 2
    assert nested_document['a.b'] == 2

def test_decrement_nested_field_keeps_the_nested_document_type(nested_document):
    """Decrementing a nested field does not downgrade the nested mapping."""
    decrement('a.b')(nested_document)

    assert isinstance(nested_document['a'], dict)
    assert type(nested_document['a']) is type(nested_document)

def test_decrement_missing_field_raises_key_error():
    """Decrementing an absent field fails loudly with a KeyError."""
    doc = {'other': 1}

    with pytest.raises(KeyError):
        decrement('counter')(doc)

def test_decrement_missing_field_leaves_the_document_unchanged():
    """A failing decrement does not modify the document."""
    doc = {'other': 1}

    with pytest.raises(KeyError):
        decrement('counter')(doc)

    assert doc == {'other': 1}

def test_decrement_dotted_field_on_plain_dict_raises_key_error():
    """Plain dicts have no dotted-path support, so 'a.b' is a missing key."""
    doc = {'a': {'b': 3}}

    with pytest.raises(KeyError):
        decrement('a.b')(doc)

    assert doc == {'a': {'b': 3}}

def test_decrement_missing_field_on_document_raises_key_error(nested_document):
    """A dotted-path mapping behaves like a mapping: an absent field raises KeyError."""
    with pytest.raises(KeyError):
        decrement('counter')(nested_document)

    assert nested_document['a']['b'] == 3

@pytest.mark.parametrize('value', ['abc', None, [1], {'k': 1}, (1,)])
def test_decrement_non_numeric_value_raises_type_error(value):
    """Non-numeric values cannot be decremented: '-= 1' raises TypeError."""
    doc = {'counter': value}

    with pytest.raises(TypeError):
        decrement('counter')(doc)

def test_decrement_on_non_mapping_document_raises_type_error():
    """Applying the transform to a non-mapping object raises TypeError."""
    with pytest.raises(TypeError):
        decrement('counter')(['counter'])

def test_decrement_transform_is_reusable_after_a_failed_application():
    """The transform keeps no state and remains usable after an error."""
    transform = decrement('counter')

    with pytest.raises(KeyError):
        transform({})

    doc = {'counter': 7}
    transform(doc)

    assert doc['counter'] == 6
