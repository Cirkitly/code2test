import pytest
from tinydb.operations import increment

@pytest.fixture
def doc():
    """A simple document with a single integer field."""
    return {'value': 0}


@pytest.fixture
def nested_doc():
    """A document with a nested integer field addressed via a dotted path."""
    return {'stats': {'hits': 0}}


@pytest.fixture
def float_doc():
    """A document holding a floating point counter."""
    return {'ratio': 0.0}

def test_increment_adds_one_to_existing_integer_field(doc):
    """The transform increases an existing integer field by 1."""
    increment('value')(doc)

    assert doc['value'] == 1


def test_increment_returns_a_callable_transform():
    """increment(field) is a factory returning a callable transformation."""
    transform = increment('value')

    assert callable(transform)


def test_increment_transform_returns_none(doc):
    """The transform mutates the document in place and returns None."""
    result = increment('value')(doc)

    assert result is None


def test_increment_mutates_the_same_document_object_in_place(doc):
    """The document passed in is the very object that gets modified."""
    original = doc
    increment('value')(doc)

    assert doc is original
    assert doc['value'] == 1


def test_increment_applied_repeatedly_increments_by_one_each_time(doc):
    """Reusing the transform three times yields +3, and the transform stays reusable."""
    transform = increment('value')

    transform(doc)
    transform(doc)
    transform(doc)

    assert doc['value'] == 3


def test_increment_from_non_zero_starting_value():
    """The field is incremented relative to its existing value."""
    doc = {'value': 41}

    increment('value')(doc)

    assert doc['value'] == 42


def test_increment_negative_value_crosses_into_positive():
    """A negative integer counter is incremented correctly."""
    doc = {'value': -1}

    increment('value')(doc)

    assert doc['value'] == 0


def test_increment_negative_value_moves_further_from_zero():
    """Incrementing a deeply negative value simply adds 1."""
    doc = {'value': -5}

    increment('value')(doc)

    assert doc['value'] == -4


def test_increment_float_field_preserves_type(float_doc):
    """A float field is incremented and keeps its numeric type."""
    increment('ratio')(float_doc)

    assert float_doc['ratio'] == 1.0
    assert isinstance(float_doc['ratio'], float)


def test_increment_accumulates_fractional_value(float_doc):
    """Incrementing a float counter adds 1.0 to the current value."""
    float_doc['ratio'] = 0.5

    increment('ratio')(float_doc)

    assert float_doc['ratio'] == 1.5


def test_increment_missing_top_level_field_raises_keyerror(doc):
    """Incrementing an absent field is an error, not a silent insert."""
    with pytest.raises(KeyError):
        increment('does_not_exist')(doc)


def test_increment_missing_field_does_not_create_the_key(doc):
    """A failing increment does not add the missing key to the document."""
    with pytest.raises(KeyError):
        increment('missing')(doc)

    assert 'missing' not in doc
    assert doc['value'] == 0


def test_increment_field_with_none_value_raises_typeerror():
    """An uninitialized (None) field cannot be incremented."""
    doc = {'value': None}

    with pytest.raises(TypeError):
        increment('value')(doc)


def test_increment_string_field_raises_typeerror():
    """A string field is not a valid increment target."""
    doc = {'value': 'not a number'}

    with pytest.raises(TypeError):
        increment('value')(doc)


def test_increment_nested_field_via_dotted_path(nested_doc):
    """A dotted path is treated as a literal top-level key, so it is not found."""
    with pytest.raises(KeyError) as excinfo:
        increment('stats.hits')(nested_doc)

    assert excinfo.value.args[0] == 'stats.hits'
    assert nested_doc == {'stats': {'hits': 0}}

def test_increment_nested_field_preserves_sibling_keys(nested_doc):
    """Only the addressed top-level key changes; siblings and structure survive."""
    nested_doc['other'] = 7

    increment('hits')(nested_doc['stats'])

    assert nested_doc['stats']['hits'] == 1
    assert nested_doc['other'] == 7
    assert nested_doc == {'stats': {'hits': 1}, 'other': 7}

def test_increment_nested_path_with_missing_intermediate_key_raises_keyerror():
    """A dotted path through a non-existent sub-document raises KeyError."""
    doc = {'value': 0}

    with pytest.raises(KeyError):
        increment('stats.hits')(doc)


def test_increment_nested_path_with_missing_leaf_key_raises_keyerror():
    """A dotted path whose leaf is missing raises KeyError."""
    doc = {'stats': {'other': 0}}

    with pytest.raises(KeyError):
        increment('stats.hits')(doc)


def test_increment_nested_path_with_none_intermediate_raises_typeerror():
    """A None intermediate is never traversed: the literal dotted key is missing."""
    doc = {'stats': None}

    with pytest.raises(KeyError) as excinfo:
        increment('stats.hits')(doc)

    assert excinfo.value.args[0] == 'stats.hits'
    assert doc == {'stats': None}

def test_increment_does_not_add_the_field_to_the_document():
    """Incrementing never introduces a new field into the document."""
    doc = {}

    with pytest.raises(KeyError):
        increment('counter')(doc)

    assert len(doc) == 0


def test_increment_on_empty_document_raises_keyerror():
    """An empty document offers no field to increment."""
    with pytest.raises(KeyError):
        increment('value')({})


def test_increment_only_modifies_the_targeted_field(doc):
    """Unrelated fields are left untouched by the increment."""
    doc['other'] = 10
    doc['name'] = 'item'

    increment('value')(doc)

    assert doc['value'] == 1
    assert doc['other'] == 10
    assert doc['name'] == 'item'


def test_increment_on_boolean_field_uses_integer_arithmetic():
    """A boolean field is treated as an integer by the += 1 operation."""
    doc = {'flag': False}

    increment('flag')(doc)

    assert doc['flag'] == 1


def test_increment_operations_are_composable_with_other_operations():
    """A freshly initialized counter can then be incremented normally."""
    from tinydb.operations import set as set_operation

    doc = {}
    set_operation('value', 0)(doc)
    increment('value')(doc)

    assert doc['value'] == 1


def test_increment_of_zero_field_becomes_one():
    """The default counter state 0 becomes 1 after a single increment."""
    doc = {'value': 0}

    increment('value')(doc)

    assert doc['value'] == 1


def test_increment_handles_large_integer_values():
    """Large counters are incremented without any numeric overflow."""
    doc = {'value': 2 ** 64 - 1}

    increment('value')(doc)

    assert doc['value'] == 2 ** 64

