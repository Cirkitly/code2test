import pytest
import re
import pytest
from tinydb.queries import Query, where

def test_query_orm_style_attribute_access_comparison():
    """ORM-style usage: ``Query().f1 == 42`` matches the matching document."""
    query = Query()
    test = query.f1 == 42

    assert test({'f1': 42, 'f2': 'other'}) is True
    assert test({'f1': 43, 'f2': 'other'}) is False

def test_query_item_access_is_equivalent_to_attribute_access():
    """``Query()['f1']`` is a different syntax for ``Query().f1``."""
    assert (Query()['f1'] == 1)({'f1': 1}) is True
    assert (Query()['f1'] == 1)({'f1': 0}) is False

    # Nested access via repeated item access
    assert (Query()['f1']['f2'] == 1)({'f1': {'f2': 1}}) is True
    assert (Query()['f1']['f2'] == 1)({'f1': {'f2': 0}}) is False

def test_query_where_shorthand_matches_query_item_access():
    """``where('value')`` is equivalent to ``Query()['value']``."""
    assert (where('value') == True)({'value': True}) is True  # noqa: E712
    assert (where('value') == True)({'value': False}) is False  # noqa: E712

def test_query_repr_shows_class_name():
    """The repr of a Query object is its class name followed by parentheses."""
    assert repr(Query()) == 'Query()'

class MyQuery(Query):
    pass


def test_query_subclass_is_preserved_by_path_access():
    """Query subclasses keep their type when a path is built."""
    query = MyQuery()
    assert isinstance(query, MyQuery)
    assert isinstance(query.some_field, MyQuery)
    assert isinstance(query.some_field.other, MyQuery)

def test_query_empty_query_raises_runtime_error_when_evaluated():
    """An empty query must not be evaluated silently."""
    with pytest.raises(RuntimeError) as exc_info:
        Query()({'f1': 1})

    assert 'Empty query was evaluated' in str(exc_info.value)

def test_query_test_on_empty_path_raises_value_error():
    """A query test without a field path is a programming error."""
    query = Query()

    with pytest.raises(ValueError) as exc_info:
        query.exists()

    assert 'Query has no path' in str(exc_info.value)

def test_query_missing_key_returns_false_instead_of_raising():
    """A document that lacks the queried field does not match."""
    assert (Query().f1 == 1)({'f2': 1}) is False
    assert (Query().f1 == 1)({}) is False
    assert Query().f1.exists()({'f2': 1}) is False

def test_query_non_mapping_document_returns_false():
    """Resolving a path against a non-mapping document yields False."""
    assert (Query().f1 == 1)(42) is False
    assert (Query().f1 == 1)(None) is False
    assert (Query().f1 == 1)('some string') is False
    assert Query().f1.exists()(42) is False

def test_query_comparison_operators_across_all_comparisons():
    """All comparison operators are supported on resolved field values."""
    assert (Query().f == 1)({'f': 1}) is True
    assert (Query().f != 1)({'f': 2}) is True
    assert (Query().f < 2)({'f': 1}) is True
    assert (Query().f < 2)({'f': 2}) is False
    assert (Query().f <= 2)({'f': 2}) is True
    assert (Query().f > 2)({'f': 3}) is True
    assert (Query().f > 2)({'f': 2}) is False
    assert (Query().f >= 2)({'f': 2}) is True

def test_query_comparison_with_non_comparable_types_raises():
    """Ordered comparisons against incompatible types are an error."""
    with pytest.raises(TypeError):
        (Query().f < 1)({'f': 'string value'})

def test_query_exists_matches_present_and_present_none_fields():
    """``exists`` only cares about the presence of the key."""
    assert Query().f.exists()({'f': None}) is True
    assert Query().f.exists()({'f': 1}) is True
    assert Query().f.exists()({'other': 1}) is False
    assert Query()['f'].exists()({}) is False

def test_query_matches_requires_whole_string_to_match():
    """``matches`` uses ``re.match`` semantics: anchored at the start of the value."""
    # The pattern has to match at the beginning of the string ...
    assert Query().f.matches(r'\w+')({'f': 'hello'}) is True
    assert Query().f.matches(r'\w+')({'f': 'hello world'}) is True
    assert Query().f.matches(r'hello')({'f': 'hello world'}) is True

    # ... but not further down the string (use ``search`` for that)
    assert Query().f.matches(r'world')({'f': 'hello world'}) is False

    # A pattern that never matches at the start does not match at all
    assert Query().f.matches(r'\d+')({'f': 'abc'}) is False

    # Non-string values never match
    assert Query().f.matches(r'\w+')({'f': 42}) is False
    assert Query().f.matches(r'.*')({'f': ['hello']}) is False

def test_query_matches_returns_false_for_non_string_values():
    """``matches`` returns False (instead of raising) for non-strings."""
    assert Query().f.matches(r'\\w+')({'f': 42}) is False
    assert Query().f.matches(r'\\w+')({'f': None}) is False
    assert Query().f.matches(r'\\w+')({'f': ['a']}) is False

def test_query_matches_honors_regex_flags():
    """Regex flags are forwarded to the underlying ``re`` call."""
    assert Query().f.matches(r'^abc$')({'f': 'ABC'}) is False
    assert Query().f.matches(r'^abc$', flags=re.IGNORECASE)({'f': 'ABC'}) is True

def test_query_search_matches_substring_anywhere():
    """``search`` uses ``re.search`` semantics (substring match)."""
    assert Query().f.search(r'ello')({'f': 'hello world'}) is True
    assert Query().f.search(r'^hello')({'f': 'well hello'}) is False
    assert Query().f.search(r'zzz')({'f': 'hello world'}) is False

def test_query_search_returns_false_for_non_string_values():
    """``search`` returns False (instead of raising) for non-strings."""
    assert Query().f.search(r'\\w+')({'f': 42}) is False
    assert Query().f.search(r'\\w+')({'f': None}) is False

def test_query_test_runs_user_defined_function_with_extra_args():
    """``test`` calls the supplied function with the value and extra args."""
    def test_func(value, factor=1):
        return value * factor > 10

    assert Query().f.test(test_func)({'f': 6}) is False
    assert Query().f.test(test_func, 2)({'f': 6}) is True

def test_query_any_with_query_condition_matches_if_one_element_matches():
    """``any`` with a query needs at least one matching element."""
    query = Query().f1.any(Query().f2 == 1)

    assert query({'f1': [{'f2': 1}, {'f2': 0}]}) is True
    assert query({'f1': [{'f2': 0}, {'f2': 2}]}) is False
    assert query({'f1': []}) is False

def test_query_any_with_list_condition_checks_membership():
    """``any`` with a list matches if one of the listed items is present."""
    query = Query().f1.any([1, 2, 3])

    assert query({'f1': [1, 2]}) is True
    assert query({'f1': [3, 4, 5]}) is True
    assert query({'f1': [4, 5]}) is False

def test_query_any_returns_false_for_non_sequence_values():
    """``any`` only applies to sequence values."""
    assert Query().f1.any([1, 2])({'f1': 42}) is False
    assert Query().f1.any([1, 2])({'f1': 'string'}) is False
    assert Query().f1.any(Query().f2 == 1)({'f1': 42}) is False

def test_query_all_with_query_condition_requires_every_element_to_match():
    """``all`` with a query needs every element to satisfy the condition."""
    query = Query().f1.all(Query().f2 == 1)

    assert query({'f1': [{'f2': 1}, {'f2': 1}]}) is True
    assert query({'f1': [{'f2': 1}, {'f2': 0}]}) is False
    assert query({'f1': []}) is True

def test_query_all_with_list_condition_requires_containment():
    """``all`` with a list matches if the tested list contains all items."""
    query = Query().f1.all([1, 2, 3])

    assert query({'f1': [1, 2, 3, 4, 5]}) is True
    assert query({'f1': [1, 2]}) is False

def test_query_all_returns_false_for_non_sequence_values():
    """``all`` only applies to sequence values, so scalars never match."""
    # A scalar is not a sequence, so the condition is never evaluated and the
    # query simply does not match -- no matter what condition is used
    assert Query().f1.all([1, 2])({'f1': 42}) is False
    assert Query().f1.all(Query().f2 == 1)({'f1': 42}) is False

    # Strings do count as sequences, so a query condition is applied to the
    # single characters and simply does not match
    assert Query().f1.all(Query().f2 == 1)({'f1': 'string'}) is False

    # Mixing a list condition with a string value propagates the TypeError of
    # Python's ``in`` operator (ints cannot be searched in a string)
    with pytest.raises(TypeError):
        Query().f1.all([1, 2])({'f1': 'string'})

def test_query_one_of_checks_membership_in_given_items():
    """``one_of`` matches documents whose value is in the given list."""
    query = Query().f1.one_of(['value 1', 'value 2'])

    assert query({'f1': 'value 1'}) is True
    assert query({'f1': 'value 2'}) is True
    assert query({'f1': 'value 3'}) is False

def test_query_fragment_matches_documents_containing_given_mapping():
    """``fragment`` matches documents that contain all given key/value pairs."""
    query = Query().fragment({'f1': 1, 'f2': 2})

    assert query({'f1': 1, 'f2': 2, 'f3': 3}) is True
    assert query({'f1': 1}) is False
    assert query({'f1': 1, 'f2': 3}) is False

def test_query_fragment_can_be_used_without_a_path():
    """``fragment`` allows an empty query path."""
    query = Query().fragment({'f1': 1})

    assert query({'f1': 1}) is True
    assert query({'f2': 1}) is False

def test_query_fragment_with_empty_document_matches_everything():
    """An empty fragment has no conditions, so it matches any mapping."""
    query = Query().fragment({})

    assert query({}) is True
    assert query({'f1': 1}) is True

def test_query_noop_always_evaluates_to_true():
    """``noop`` is always True and needs no query path."""
    query = Query().noop()

    assert query({}) is True
    assert query({'f1': 1}) is True
    # ``noop`` does not need a path, so it works on a bare Query
    assert Query().noop()({'anything': 'goes'}) is True

def test_query_map_applies_callable_to_field_value():
    """``map`` adds a callable to the query path like ``__getattr__``."""
    query = Query().map(lambda value: value['inner'])

    assert (query == 1)({'inner': 1}) is True
    assert (query == 1)({'inner': 2}) is False

    # ``map`` can be combined with field access
    nested = Query().f1.map(lambda value: value * 2)
    assert (nested == 4)({'f1': 2}) is True
    assert (nested == 4)({'f1': 3}) is False

def test_query_map_returns_query_instance_of_same_type():
    """``map`` returns a new Query object so more path parts can follow."""
    query = Query().map(str)

    assert isinstance(query, Query)

def test_query_map_result_is_not_cacheable():
    """A query containing a callable in its path must not be cached."""
    def fn(value):
        return value

    query = Query().map(fn)
    assert query.is_cacheable() is False

    # Comparing two queries with equal paths stays cacheable
    assert (Query().f1 == 1).is_cacheable() is True

    # Different callables are not considered equal even for the same path
    assert Query().map(fn) != Query().map(fn)

def test_query_equality_and_hash_based_on_on_path_and_condition():
    """Queries with the same path and condition compare equal and hash equal."""
    assert Query().f1 == Query().f1
    assert (Query().f1 == 1) == (Query().f1 == 1)
    assert (Query().f1 == 1) != (Query().f1 == 2)
    assert (Query().f1 == 1) != (Query().f2 == 1)
    assert (Query().f1 == 1) != (Query().f1 != 1)

    assert hash(Query().f1 == 1) == hash(Query().f1 == 1)

def test_query_unhashable_conditions_do_not_raise():
    """Conditions that are not hashable are frozen before being hashed."""
    # A list as the right-hand side of == is not hashable ...
    query = Query().f1 == [1, 2]
    # ... but building the query still works and hashing does not raise
    assert hash(query) == hash(Query().f1 == [1, 2])
    assert query({'f1': [1, 2]}) is True
    assert query({'f1': [3]}) is False

def test_query_binary_and_operator_combines_conditions():
    """Queries can be combined with the binary AND operator."""
    query = (Query().f1.exists()) & (Query().f2 == 5)

    assert query({'f1': 1, 'f2': 5}) is True
    assert query({'f1': 1, 'f2': 6}) is False
    assert query({'f2': 5}) is False
    assert query({}) is False

def test_query_binary_or_operator_combines_conditions():
    """Queries can be combined with the binary OR operator."""
    query = (Query().f1.exists()) | (Query().f2 == 5)

    assert query({'f1': 1, 'f2': 6}) is True
    assert query({'f2': 5}) is True
    assert query({'f2': 6}) is False
    assert query({}) is False

def test_query_where_shortcut_is_usable_in_combinations():
    """The documented ``where`` based composition syntax works."""
    query = (where('field1').exists()) & (where('field2') == 5)

    assert query({'field1': True, 'field2': 5}) is True
    assert query({'field1': True, 'field2': 0}) is False

    query_or = (where('field1').exists()) | (where('field2') == 5)
    assert query_or({'field2': 5}) is True
    assert query_or({}) is False

def test_query_nested_path_resolves_through_multiple_levels():
    """Nested query paths resolve through several document levels."""
    query = Query().a.b.c == 1

    assert query({'a': {'b': {'c': 1}}}) is True
    assert query({'a': {'b': {'c': 2}}}) is False
    assert query({'a': {'b': {}}}) is False
    assert query({'a': 1}) is False

def test_query_any_with_non_mapping_elements_evaluates_to_false():
    """Query conditions applied to non-mapping elements do not match."""
    query = Query().f1.any(Query().f2 == 1)

    assert query({'f1': [1, 2, 3]}) is False
    assert query({'f1': ['a', 'b']}) is False
