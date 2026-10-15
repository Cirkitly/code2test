import pytest
from tinydb.operations import subtract

def test_subtract_returns_a_transform_callable():
    """subtract(field, n) returns a transform function, not a mutation."""
    doc = {'value': 10}

    transform = subtract('value', 3)

    assert callable(transform), 'subtract should return a callable transform'
    # The document must still be untouched before the transform runs.
    assert doc == {'value': 10}, 'subtract must not mutate the document before the transform is called'


def test_subtract_happy_path_subtracts_n_from_numeric_field():
    """subtract(field, n) reduces the field's value by n."""
    doc = {'age': 30}

    subtract('age', 5)(doc)

    assert doc['age'] == 25, 'age should be reduced by the given n'


def test_subtract_leaves_other_fields_untouched():
    """Only the named field is modified; the rest of the document is preserved."""
    doc = {'name': 'alice', 'score': 50, 'active': True}

    subtract('score', 20)(doc)

    assert doc == {'name': 'alice', 'score': 30, 'active': True}


def test_subtract_mutates_document_in_place():
    """The transform mutates the passed document in place and returns None."""
    doc = {'count': 8}

    result = subtract('count', 3)(doc)

    assert doc['count'] == 5, 'subtract should reduce the field value in place'
    assert result is None, 'the transform does not return the document, it mutates it'

def test_subtract_can_target_nested_field_by_key():
    """The field argument is a literal key; nested dicts are not traversed."""
    doc = {'meta': {'hits': 9}, 'hits': 4}

    subtract('hits', 1)(doc)

    assert doc['hits'] == 3, 'top level key should be decremented'
    assert doc['meta'] == {'hits': 9}, 'nested document should be left alone'


def test_subtract_zero_is_a_no_op():
    """Subtracting 0 leaves the document value unchanged."""
    doc = {'level': 7}

    subtract('level', 0)(doc)

    assert doc['level'] == 7


def test_subtract_negative_n_actually_increases_the_value():
    """A negative n increases the value, since the operation is doc[field] -= n."""
    doc = {'level': 4}

    subtract('level', -3)(doc)

    assert doc['level'] == 7


def test_subtract_can_produce_negative_values():
    """The result may become negative; no clamping or error is raised."""
    doc = {'balance': 4}

    subtract('balance', 10)(doc)

    assert doc['balance'] == -6


def test_subtract_large_n_saturates_to_int_arithmetic():
    """Large n is handled with standard integer arithmetic and no error."""
    doc = {'count': 1_000_000}

    subtract('count', 999_999)(doc)

    assert doc['count'] == 1


def test_subtract_supports_float_values():
    """Float fields are supported via ordinary float arithmetic."""
    doc = {'price': 10.5}

    subtract('price', 2.25)(doc)

    assert doc['price'] == pytest.approx(8.25)


def test_subtract_raises_key_error_when_field_is_missing():
    """Applying subtract to an absent field raises KeyError."""
    doc = {'other': 1}

    with pytest.raises(KeyError):
        subtract('missing', 1)(doc)


def test_subtract_leaves_document_unchanged_when_field_is_missing():
    """A failed subtract does not alter any part of the document."""
    doc = {'other': 1, 'value': 5}

    with pytest.raises(KeyError):
        subtract('value_typo', 2)(doc)

    assert doc == {'other': 1, 'value': 5}, 'document must be untouched when the field lookup fails'


def test_subtract_raises_type_error_on_incompatible_value():
    """Non-numeric field values raise TypeError instead of silently failing."""
    doc = {'name': 'alice'}

    with pytest.raises(TypeError):
        subtract('name', 1)(doc)


def test_subtract_transform_is_reusable_across_documents():
    """The same transform can be applied to multiple documents."""
    transform = subtract('hp', 3)

    first = {'hp': 10}
    second = {'hp': 5}

    transform(first)
    transform(second)

    assert first['hp'] == 7
    assert second['hp'] == 2


def test_subtract_operations_can_be_composed():
    """subtract and add with the same n cancel each other out."""
    doc = {'value': 42}

    subtract('value', 8)(doc)
    assert doc['value'] == 34

    # Compose a second operation that reverses the change.
    def add(field, n):
        def transform(d):
            d[field] += n
        return transform

    add('value', 8)(doc)
    assert doc['value'] == 42


def test_subtract_matches_decrement_semantics_for_one():
    """subtract(field, 1) is equivalent to decrementing the field by one."""
    doc = {'count': 5}

    subtract('count', 1)(doc)

    assert doc['count'] == 4

