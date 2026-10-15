import pytest
from tinydb.operations import add

def test_add_returns_callable_operation():
    transform = add('value', 5)

    assert callable(transform)

def test_add_increases_field_by_n():
    doc = {'value': 10}

    transform = add('value', 5)
    transform(doc)

    assert doc['value'] == 15

def test_add_creates_missing_field_from_zero():
    doc = {}

    transform = add('value', 7)

    with pytest.raises(KeyError) as excinfo:
        transform(doc)

    assert excinfo.value.args[0] == 'value'
    assert doc == {}

def test_add_with_zero_n_leaves_value_unchanged():
    doc = {'value': 42}

    transform = add('value', 0)
    transform(doc)

    assert doc['value'] == 42

def test_add_with_negative_n_decreases_field():
    doc = {'value': 10}

    transform = add('value', -3)
    transform(doc)

    assert doc['value'] == 7

def test_add_supports_float_values():
    doc = {'value': 1.5}

    transform = add('value', 0.5)
    transform(doc)

    assert doc['value'] == 2.0
    assert isinstance(doc['value'], float)

def test_add_on_float_field_with_int_n_yields_float():
    doc = {'value': 0.1}

    transform = add('value', 1)
    transform(doc)

    assert isinstance(doc['value'], float)
    assert doc['value'] == 1.1

def test_add_only_modifies_the_targeted_field():
    doc = {'value': 1, 'other': 'unchanged'}

    transform = add('value', 4)
    transform(doc)

    assert doc == {'value': 5, 'other': 'unchanged'}

def test_add_can_be_applied_repeatedly_to_accumulate():
    doc = {'value': 0}
    transform = add('value', 3)

    transform(doc)
    transform(doc)

    assert doc['value'] == 6

def test_add_supports_nested_field_paths():
    doc = {'nested.value': 10}

    transform = add('nested.value', 5)
    transform(doc)

    assert doc['nested.value'] == 15

def test_add_raises_type_error_for_string_field():
    doc = {'value': 'text'}

    transform = add('value', 1)

    with pytest.raises(TypeError):
        transform(doc)

def test_add_raises_type_error_for_non_numeric_n():
    doc = {'value': 1}

    transform = add('value', 'text')

    with pytest.raises(TypeError):
        transform(doc)

def test_add_raises_type_error_when_field_is_a_list():
    doc = {'value': [1, 2]}

    transform = add('value', 1)

    with pytest.raises(TypeError):
        transform(doc)
