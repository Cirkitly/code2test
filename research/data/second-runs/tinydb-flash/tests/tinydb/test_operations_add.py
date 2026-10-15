import pytest
from tinydb.operations import add
from tinydb.operations import decrement
from tinydb.operations import increment
from tinydb.operations import set
from tinydb.operations import subtract

@pytest.fixture
def numeric_doc():
    """A simple mutable mapping used as a document with a single numeric field."""
    return {'value': 1}

def test_add_increases_numeric_field_by_n():
    """``add`` returns a transform that adds ``n`` to the given field of the document."""
    doc = {'value': 1}

    transform = add('value', 3)
    transform(doc)

    assert doc['value'] == 4

def test_add_returns_a_callable_transform():
    """``add`` is a higher-order function returning a transform callable."""
    transform = add('value', 1)

    assert callable(transform)

def test_add_mutates_document_in_place_and_returns_none():
    """The transform changes the document in place and has no return value."""
    doc = {'value': 10}

    result = add('value', 5)(doc)

    assert result is None
    assert doc == {'value': 15}

def test_add_creates_no_new_fields_and_leaves_other_fields_untouched():
    """Adding to one field must not modify any other field of the document."""
    doc = {'value': 1, 'other': 'unchanged', 'third': 100}

    add('value', 2)(doc)

    assert doc == {'value': 3, 'other': 'unchanged', 'third': 100}

def test_add_with_zero_is_a_no_op_for_numeric_field():
    """Adding ``0`` keeps the current value of the field."""
    doc = {'value': 42}

    add('value', 0)(doc)

    assert doc['value'] == 42

def test_add_with_zero_on_zero_value_keeps_zero():
    """Adding ``0`` to a ``0``-valued field still yields ``0``."""
    doc = {'value': 0}

    add('value', 0)(doc)

    assert doc['value'] == 0

def test_add_with_negative_n_reduces_the_value():
    """A negative ``n`` decreases the value of the field."""
    doc = {'value': 10}

    add('value', -4)(doc)

    assert doc['value'] == 6

def test_add_supports_negative_field_values():
    """Negative values are supported because the transform uses plain ``+=``."""
    doc = {'value': -5}

    add('value', 8)(doc)

    assert doc['value'] == 3

def test_add_works_with_float_field_and_float_n():
    """Floats are added to floats just like integers."""
    doc = {'value': 1.5}

    add('value', 2.25)(doc)

    assert doc['value'] == pytest.approx(3.75)

def test_add_casts_int_n_onto_float_field():
    """Mixing an integer ``n`` with a float field value is allowed."""
    doc = {'value': 0.5}

    add('value', 1)(doc)

    assert doc['value'] == pytest.approx(1.5)
    assert isinstance(doc['value'], float)

def test_add_concatenates_strings_when_n_is_a_string():
    """String fields concatenate with a string ``n`` instead of raising."""
    doc = {'value': 'a'}

    add('value', 'b')(doc)

    assert doc['value'] == 'ab'

def test_add_raises_key_error_for_missing_field():
    """A missing field cannot be added to; the transform raises ``KeyError``."""
    doc = {'other': 1}

    with pytest.raises(KeyError):
        add('value', 1)(doc)

def test_add_leaves_document_unchanged_when_field_is_missing():
    """A failing transform must not corrupt the document."""
    doc = {'other': 1}

    with pytest.raises(KeyError):
        add('value', 1)(doc)

    assert doc == {'other': 1}
    assert 'value' not in doc

def test_add_raises_type_error_for_string_field_with_int_n():
    """Incompatible operand types are rejected by the ``+=`` operation."""
    doc = {'value': 'text'}

    with pytest.raises(TypeError):
        add('value', 1)(doc)

def test_add_raises_type_error_for_list_field_with_int_n():
    """A list field cannot be increased by an integer amount."""
    doc = {'value': [1, 2]}

    with pytest.raises(TypeError):
        add('value', 1)(doc)

def test_add_raises_type_error_for_string_field_with_none_n():
    """``n`` must be a value compatible with the field's current type."""
    doc = {'value': 1}

    with pytest.raises(TypeError):
        add('value', None)(doc)

def test_add_applies_operations_to_falsy_field_values():
    """Falsy stored values are real values and are added to, not rejected."""
    doc = {'zero': 0, 'empty_string': ''}

    add('zero', 5)(doc)

    assert doc['zero'] == 5
    assert doc['empty_string'] == ''

def test_add_can_be_applied_repeatedly_accumulating_values():
    """Reusing the same transform accumulates changes on the same document."""
    doc = {'value': 0}
    transform = add('value', 2)

    transform(doc)
    transform(doc)
    transform(doc)

    assert doc['value'] == 6

def test_transforms_from_different_fields_and_values_are_independent():
    """Separately created transforms do not share captured state."""
    doc = {'a': 1, 'b': 1}

    add_a = add('a', 10)
    add_b = add('b', 100)

    add_b(doc)
    add_a(doc)

    assert doc == {'a': 11, 'b': 101}

def test_add_is_composable_with_other_field_operations():
    """``add`` produces a plain transform usable together with other operations."""
    doc = {'value': 0}

    increment('value')(doc)
    add('value', 10)(doc)
    decrement('value')(doc)
    subtract('value', 5)(doc)
    set('value', 1)(doc)

    assert doc['value'] == 1
