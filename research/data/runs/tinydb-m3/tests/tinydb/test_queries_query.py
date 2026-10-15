import re
import pytest
from tinydb.queries import Query, QueryInstance, where

def test_create_empty_query_has_empty_path():
    """A freshly created Query has no path components."""
    q = Query()
    assert q._path == ()


def test_query_repr_returns_class_name():
    """Repr uses the class name with empty parens."""
    assert repr(Query()) == 'Query()'


def test_where_shorthand_builds_query_with_path():
    """where(...) is the documented shorthand for Query()[key]."""
    q = where('name')
    assert isinstance(q, Query)
    assert q._path == ('name',)


def test_empty_query_raises_when_called():
    """Evaluating an empty Query raises RuntimeError (notest guard)."""
    with pytest.raises(RuntimeError, match='Empty query was evaluated'):
        Query()({'a': 1})


def test_query_with_only_path_still_raises_when_called():
    """A Query that has a path but no terminal comparison is still not callable."""
    with pytest.raises(RuntimeError, match='Empty query was evaluated'):
        Query().name({'name': 'John'})


@pytest.mark.parametrize('op_callable', [
    lambda q: q == 1,
    lambda q: q != 1,
    lambda q: q < 1,
    lambda q: q <= 1,
    lambda q: q > 1,
    lambda q: q >= 1,
])
def test_comparison_operators_on_empty_path_raise_value_error(op_callable):
    """Every comparison requires a non-empty path."""
    q = Query()
    with pytest.raises(ValueError, match='Query has no path'):
        op_callable(q)


def test_exists_on_empty_path_raises_value_error():
    """exists() also requires a path."""
    with pytest.raises(ValueError, match='Query has no path'):
        Query().exists()


def test_attribute_access_creates_subquery_with_path():
    """Attribute access returns a new Query that extends the path."""
    q = Query().name
    assert isinstance(q, Query)
    assert q._path == ('name',)


def test_getitem_creates_subquery_with_path():
    """Bracket access works as an alternative to dot access."""
    q = Query()['name']
    assert isinstance(q, Query)
    assert q._path == ('name',)


def test_getitem_avoids_method_resolution_for_test_name():
    """Critical edge case: __getitem__ calls __getattr__ directly to skip method lookup."""
    q = Query()['test']
    # 'test' is a method on Query; __getitem__ must bypass it.
    assert isinstance(q, Query)
    assert q._path == ('test',)


def test_chained_attribute_access_builds_nested_path():
    """Each access appends one component to the path."""
    q = Query().a.b.c
    assert q._path == ('a', 'b', 'c')


def test_attribute_access_does_not_mutate_original_query():
    """Path extension creates an independent Query object."""
    parent = Query()
    child = parent.name
    assert parent._path == ()
    assert child._path == ('name',)
    assert parent is not child


def test_equality_returns_query_instance():
    """Comparison operators yield a QueryInstance, not a plain Query."""
    q = Query().a == 1
    assert isinstance(q, QueryInstance)
    assert callable(q)


def test_equality_matches_equal_values():
    """== operator matches documents whose field value equals rhs."""
    q = Query().name == 'John'
    assert q({'name': 'John'}) is True


def test_equality_returns_false_for_different_values():
    """== operator returns False when values differ."""
    q = Query().name == 'John'
    assert q({'name': 'Jane'}) is False


def test_equality_returns_false_for_missing_key():
    """== returns False for documents that lack the key."""
    q = Query().name == 'John'
    assert q({'other': 1}) is False
    assert q({}) is False


def test_inequality_matches_unequal_values():
    """!= operator matches documents whose field value differs from rhs."""
    q = Query().name != 'John'
    assert q({'name': 'Jane'}) is True
    assert q({'name': 'John'}) is False


def test_less_than_compares_numerically():
    """< operator uses strict less-than semantics."""
    q = Query().age < 30
    assert q({'age': 20}) is True
    assert q({'age': 30}) is False
    assert q({'age': 40}) is False


def test_less_than_or_equal_includes_equal_boundary():
    """<= operator matches values less than or equal to rhs."""
    q = Query().age <= 30
    assert q({'age': 20}) is True
    assert q({'age': 30}) is True
    assert q({'age': 40}) is False


def test_greater_than_compares_numerically():
    """> operator uses strict greater-than semantics."""
    q = Query().age > 30
    assert q({'age': 40}) is True
    assert q({'age': 30}) is False
    assert q({'age': 20}) is False


def test_greater_than_or_equal_includes_equal_boundary():
    """>= operator matches values greater than or equal to rhs."""
    q = Query().age >= 30
    assert q({'age': 40}) is True
    assert q({'age': 30}) is True
    assert q({'age': 20}) is False


def test_nested_path_comparison():
    """Comparison walks through nested dictionaries via the path."""
    q = Query().a.b == 1
    assert q({'a': {'b': 1}}) is True
    assert q({'a': {'b': 2}}) is False


def test_nested_path_returns_false_when_intermediate_missing():
    """Walking a nested path with a missing sub-key returns False."""
    q = Query().a.b == 1
    assert q({'a': {}}) is False


def test_nested_path_returns_false_when_intermediate_not_dict():
    """Trying to subscript a non-dict value returns False."""
    q = Query().a.b == 1
    assert q({'a': 1}) is False


def test_exists_returns_true_when_field_present():
    """exists() matches documents containing the field."""
    q = Query().name.exists()
    assert q({'name': 'John'}) is True


def test_exists_returns_false_when_field_missing():
    """exists() returns False when the key is absent (KeyError caught)."""
    q = Query().name.exists()
    assert q({'other': 1}) is False
    assert q({}) is False


def test_matches_requires_full_string_match():
    """re.match anchors at the start and requires the entire value to match."""
    q = Query().name.matches(r'^\w+$')
    assert q({'name': 'John'}) is True
    assert q({'name': 'John Doe'}) is False


def test_matches_returns_false_for_non_string_values():
    """matches() guards against non-string values."""
    q = Query().name.matches(r'.*')
    assert q({'name': 42}) is False
    assert q({'name': None}) is False


def test_matches_honors_regex_flags():
    """The flags argument is forwarded to re.match."""
    q = Query().name.matches(r'john', flags=re.IGNORECASE)
    assert q({'name': 'JOHN'}) is True
    assert q({'name': 'jane'}) is False


def test_search_matches_substring():
    """re.search matches the regex at any position in the string."""
    q = Query().name.search(r'John')
    assert q({'name': 'John Doe'}) is True
    assert q({'name': 'Jane'}) is False


def test_search_returns_false_for_non_string_values():
    """search() guards against non-string values."""
    q = Query().name.search(r'.*')
    assert q({'name': 42}) is False


def test_custom_test_receives_resolved_value():
    """test() runs the user's predicate on the resolved value."""
    q = Query().age.test(lambda v: v % 2 == 0)
    assert q({'age': 4}) is True
    assert q({'age': 5}) is False


def test_custom_test_forwards_extra_args():
    """Extra positional args to test() are passed through to the function."""
    q = Query().age.test(lambda v, threshold: v > threshold, 10)
    assert q({'age': 20}) is True
    assert q({'age': 5}) is False


def test_custom_test_returns_false_on_missing_key():
    """Missing key means test() never runs the user function."""
    q = Query().age.test(lambda v: True)
    assert q({}) is False


def test_any_with_subquery_matches_if_any_element_matches():
    """any(query) walks the list and applies the subquery to each element."""
    q = Query().items.any(Query().value == 1)
    assert q({'items': [{'value': 1}, {'value': 2}]}) is True
    assert q({'items': [{'value': 2}, {'value': 3}]}) is False


def test_any_with_list_matches_overlap():
    """any(list) requires at least one common element."""
    q = Query().items.any([1, 2, 3])
    assert q({'items': [1, 5]}) is True
    assert q({'items': [4, 5]}) is False


def test_any_returns_false_for_non_sequence_value():
    """Non-sequence values fail the is_sequence check inside any()."""
    q = Query().items.any([1, 2])
    assert q({'items': 42}) is False
    assert q({'items': None}) is False


def test_all_with_subquery_matches_when_all_elements_match():
    """all(query) walks the list and requires every element to match."""
    q = Query().items.all(Query().value == 1)
    assert q({'items': [{'value': 1}, {'value': 1}]}) is True
    assert q({'items': [{'value': 1}, {'value': 2}]}) is False


def test_all_with_list_requires_containment():
    """all(list) requires the list to be a subset of the value."""
    q = Query().items.all([1, 2, 3])
    assert q({'items': [1, 2, 3, 4]}) is True
    assert q({'items': [1, 2]}) is False


def test_all_returns_false_for_non_sequence_value():
    """Non-sequence values fail the is_sequence check inside all()."""
    q = Query().items.all([1, 2])
    assert q({'items': 42}) is False


def test_one_of_matches_value_in_list():
    """one_of() uses 'in' semantics against the items list."""
    q = Query().name.one_of(['John', 'Jane'])
    assert q({'name': 'John'}) is True
    assert q({'name': 'Jane'}) is True


def test_one_of_returns_false_when_value_not_in_list():
    """Values not in the items list do not match."""
    q = Query().name.one_of(['John', 'Jane'])
    assert q({'name': 'Bob'}) is False


def test_fragment_matches_superset_documents():
    """fragment() treats the supplied mapping as a required subset."""
    q = Query().fragment({'a': 1})
    assert q({'a': 1, 'b': 2}) is True


def test_fragment_returns_false_when_shared_value_differs():
    """If any overlapping key has a different value, fragment() fails."""
    q = Query().fragment({'a': 1})
    assert q({'a': 2, 'b': 2}) is False


def test_fragment_returns_false_when_key_missing():
    """Documents lacking any fragment key do not match."""
    q = Query().fragment({'a': 1})
    assert q({'b': 1}) is False


def test_fragment_works_on_empty_query_path():
    """fragment() bypasses the usual empty-path ValueError."""
    q = Query().fragment({'a': 1})
    assert isinstance(q, QueryInstance)
    assert q({'a': 1, 'b': 2}) is True
    assert q({'a': 2}) is False


def test_noop_always_evaluates_true():
    """noop() is a useful base value that always matches."""
    q = Query().noop()
    assert isinstance(q, QueryInstance)
    assert q({'any': 'thing'}) is True
    assert q({}) is True


def test_and_operator_combines_with_conjunction():
    """& produces AND semantics between two query instances."""
    combined = (Query().a == 1) & (Query().b == 2)
    assert combined({'a': 1, 'b': 2}) is True
    assert combined({'a': 1, 'b': 3}) is False
    assert combined({'a': 0, 'b': 2}) is False


def test_or_operator_combines_with_disjunction():
    """| produces OR semantics between two query instances."""
    combined = (Query().a == 1) | (Query().b == 2)
    assert combined({'a': 1, 'b': 3}) is True
    assert combined({'a': 3, 'b': 2}) is True
    assert combined({'a': 3, 'b': 3}) is False


def test_map_returns_a_query_with_callable_in_path():
    """map() keeps the object a Query so it can be further chained."""
    fn = str.upper
    q = Query().name.map(fn)
    assert isinstance(q, Query)
    assert q._path == ('name', fn)


def test_map_then_comparison_applies_function():
    """A mapped callable runs during path resolution."""
    q = Query().name.map(str.upper) == 'JOHN'
    assert q({'name': 'john'}) is True
    assert q({'name': 'bob'}) is False


def test_map_disables_caching_hash():
    """map() clears the cache hash because callables may be mutable."""
    q = Query().data.map(str.upper)
    assert q._hash is None


def test_generated_query_instance_is_cacheable():
    """Comparison-generated query instances carry a hash for caching."""
    q = Query().name == 'John'
    assert q.is_cacheable() is True

