import re
import pytest
from tinydb.queries import Query, QueryInstance, where

def test_query_creation_has_empty_path():
    """A fresh Query() should start with an empty path tuple."""
    q = Query()
    assert q._path == ()


def test_query_repr_uses_class_name():
    """Query's repr should be the class name followed by parentheses."""
    assert repr(Query()) == 'Query()'


def test_query_is_hashable():
    """Query instances should be hashable in all their forms."""
    # Empty query
    assert isinstance(hash(Query()), int)
    # Query with a path
    assert isinstance(hash(Query().name), int)
    # QueryInstance returned from a comparison
    assert isinstance(hash(Query().name == 'John'), int)


def test_empty_query_raises_runtime_error_when_called():
    """Calling a Query with no path and no test should raise RuntimeError."""
    q = Query()
    with pytest.raises(RuntimeError, match='Empty query was evaluated'):
        q({'any': 'document'})


def test_subclass_uses_own_type_for_path_building():
    """A Query subclass should preserve its own type when building paths."""
    class MyQuery(Query):
        pass

    q = MyQuery().name
    assert isinstance(q, MyQuery)
    assert q._path == ('name',)


def test_subclass_repr_uses_subclass_name():
    """A Query subclass's repr should use the subclass name."""
    class MyQuery(Query):
        pass

    assert repr(MyQuery()) == 'MyQuery()'

def test_attribute_access_appends_to_path():
    """Accessing an attribute should append the attribute name to the path."""
    q = Query().name
    assert q._path == ('name',)

def test_eq_operator_matches_equal_value():
    """The == operator should match documents where the field equals the value."""
    q = Query().name == 'John'
    assert q({'name': 'John'}) is True


def test_eq_operator_does_not_match_unequal_value():
    """The == operator should return False when the field value differs."""
    q = Query().name == 'John'
    assert q({'name': 'Jane'}) is False


def test_eq_operator_returns_false_for_missing_key():
    """The == operator should return False when the key is missing from the document."""
    q = Query().name == 'John'
    assert q({}) is False


def test_ne_operator_matches_inequality():
    """The != operator should match documents where the field is not equal."""
    q = Query().name != 'John'
    assert q({'name': 'Jane'}) is True
    assert q({'name': 'John'}) is False


def test_ne_operator_returns_false_for_missing_key():
    """The != operator should return False when the key is missing (path error)."""
    q = Query().name != 'John'
    assert q({}) is False


def test_lt_operator_tests_less_than():
    """The < operator should test strict less-than comparisons."""
    q = Query().age < 30
    assert q({'age': 25}) is True
    assert q({'age': 30}) is False
    assert q({'age': 35}) is False


def test_le_operator_tests_less_than_or_equal():
    """The <= operator should test less-than-or-equal comparisons."""
    q = Query().age <= 30
    assert q({'age': 25}) is True
    assert q({'age': 30}) is True
    assert q({'age': 35}) is False


def test_gt_operator_tests_greater_than():
    """The > operator should test strict greater-than comparisons."""
    q = Query().age > 30
    assert q({'age': 35}) is True
    assert q({'age': 30}) is False
    assert q({'age': 25}) is False


def test_ge_operator_tests_greater_than_or_equal():
    """The >= operator should test greater-than-or-equal comparisons."""
    q = Query().age >= 30
    assert q({'age': 35}) is True
    assert q({'age': 30}) is True
    assert q({'age': 25}) is False


def test_comparison_with_empty_query_raises_value_error():
    """Applying a comparison operator to an empty Query should raise ValueError."""
    q = Query()
    with pytest.raises(ValueError, match='Query has no path'):
        q == 'value'
    with pytest.raises(ValueError, match='Query has no path'):
        q != 'value'
    with pytest.raises(ValueError, match='Query has no path'):
        q < 10
    with pytest.raises(ValueError, match='Query has no path'):
        q <= 10
    with pytest.raises(ValueError, match='Query has no path'):
        q > 10
    with pytest.raises(ValueError, match='Query has no path'):
        q >= 10


def test_comparison_with_nested_path():
    """Comparisons should resolve nested paths through the document."""
    q = Query().user.age == 25
    assert q({'user': {'age': 25}}) is True
    assert q({'user': {'age': 30}}) is False


def test_comparison_returns_false_for_missing_nested_key():
    """A comparison should return False (not raise) when any nested key is missing."""
    q = Query().user.name == 'John'
    assert q({'user': {}}) is False
    assert q({}) is False


def test_comparison_returns_query_instance():
    """A comparison on a Query should return a QueryInstance."""
    assert isinstance(Query().name == 'John', QueryInstance)
    assert isinstance(Query().age > 10, QueryInstance)

def test_exists_method_matches_present_key():
    """exists() should return True whenever the key is present, regardless of value."""
    q = Query().name.exists()
    assert q({'name': 'John'}) is True
    assert q({'name': None}) is True
    assert q({'name': 0}) is True
    assert q({'name': ''}) is True
    assert q({'name': False}) is True


def test_exists_method_does_not_match_missing_key():
    """exists() should return False when the key is not present in the document."""
    q = Query().name.exists()
    assert q({}) is False
    assert q({'other': 'value'}) is False


def test_exists_returns_query_instance():
    """exists() should return a QueryInstance, not a Query."""
    result = Query().name.exists()
    assert isinstance(result, QueryInstance)


def test_exists_is_cacheable():
    """A exists() query should be cacheable (has a hash)."""
    assert Query().name.exists().is_cacheable() is True

def test_matches_whole_string():
    """matches() should test whether the entire string matches the regex (full match)."""
    q = Query().name.matches(r'^\w+$')
    assert q({'name': 'John'}) is True
    # Contains a space, so the full string does not match
    assert q({'name': 'John Doe'}) is False


def test_matches_returns_false_for_non_string():
    """matches() should return False for non-string values."""
    q = Query().age.matches(r'^\d+$')
    assert q({'age': 25}) is False
    assert q({'age': None}) is False


def test_matches_accepts_regex_flags():
    """matches() should respect the regex flags argument."""
    q = Query().name.matches(r'john', flags=re.IGNORECASE)
    assert q({'name': 'JOHN'}) is True
    assert q({'name': 'John'}) is True
    assert q({'name': 'Jane'}) is False


def test_matches_returns_false_for_missing_key():
    """matches() should return False when the key is missing (path resolution error)."""
    q = Query().name.matches(r'.*')
    assert q({}) is False

def test_search_finds_substring_anywhere():
    """search() should match if the regex is found anywhere in the string."""
    q = Query().name.search(r'John')
    assert q({'name': 'John Doe'}) is True
    assert q({'name': 'Mr. John'}) is True
    assert q({'name': 'Jane'}) is False


def test_search_returns_false_for_non_string():
    """search() should return False for non-string values."""
    q = Query().age.search(r'2')
    assert q({'age': 25}) is False


def test_search_accepts_regex_flags():
    """search() should respect the regex flags argument."""
    q = Query().name.search(r'john', flags=re.IGNORECASE)
    assert q({'name': 'MR. JOHN'}) is True
    assert q({'name': 'MR. JANE'}) is False

def test_test_method_with_function():
    """test() should run a user-defined predicate on the resolved field value."""
    def is_positive(value):
        return value > 0

    q = Query().age.test(is_positive)
    assert q({'age': 5}) is True
    assert q({'age': -1}) is False
    assert q({'age': 0}) is False


def test_test_method_with_extra_args():
    """test() should forward extra positional arguments to the user-defined function."""
    def is_greater_than(value, threshold):
        return value > threshold

    q = Query().age.test(is_greater_than, 10)
    assert q({'age': 15}) is True
    assert q({'age': 10}) is False
    assert q({'age': 5}) is False


def test_test_method_with_multiple_extra_args():
    """test() should forward all extra positional arguments to the user-defined function."""
    def in_range(value, lo, hi):
        return lo <= value <= hi

    q = Query().age.test(in_range, 0, 100)
    assert q({'age': 50}) is True
    assert q({'age': 150}) is False
    assert q({'age': -1}) is False


def test_test_method_returns_false_for_missing_key():
    """test() should return False when the key is missing (path error)."""
    q = Query().age.test(lambda v: True)
    assert q({}) is False


def test_test_method_returns_query_instance():
    """test() should return a QueryInstance."""
    result = Query().age.test(lambda v: True)
    assert isinstance(result, QueryInstance)

def test_any_with_query_instance():
    """any() with a query should match if at least one element satisfies the query."""
    q = Query().items.any(Query().value == 1)
    assert q({'items': [{'value': 1}, {'value': 2}]}) is True
    assert q({'items': [{'value': 2}, {'value': 3}]}) is False


def test_any_with_list():
    """any() with a list should match if any element of the document's list is in the given list."""
    q = Query().tags.any([1, 2, 3])
    assert q({'tags': [2, 4]}) is True
    assert q({'tags': [4, 5]}) is False


def test_any_returns_false_for_non_list_value():
    """any() should return False if the field value is not a list or tuple."""
    q = Query().tags.any([1, 2, 3])
    assert q({'tags': 'string'}) is False
    assert q({'tags': 2}) is False
    assert q({'tags': None}) is False


def test_any_returns_false_for_empty_list():
    """any() should return False when the document's list is empty."""
    q = Query().tags.any([1, 2, 3])
    assert q({'tags': []}) is False


def test_any_with_tuple_field():
    """any() should work with tuple values (tuples are sequences in tinydb)."""
    q = Query().tags.any([1, 2, 3])
    assert q({'tags': (2, 4)}) is True
    assert q({'tags': (4, 5)}) is False


def test_any_returns_query_instance():
    """any() should return a QueryInstance."""
    result = Query().items.any([1, 2, 3])
    assert isinstance(result, QueryInstance)

def test_all_with_query_instance():
    """all() with a query should match if every element in the list satisfies the query."""
    q = Query().items.all(Query().value == 1)
    assert q({'items': [{'value': 1}, {'value': 1}]}) is True
    assert q({'items': [{'value': 1}, {'value': 2}]}) is False

def test_one_of_matches_value_in_list():
    """one_of() should match if the field's value is contained in the provided items."""
    q = Query().name.one_of(['John', 'Jane'])
    assert q({'name': 'John'}) is True
    assert q({'name': 'Jane'}) is True
    assert q({'name': 'Bob'}) is False


def test_one_of_with_non_string_values():
    """one_of() should work for any hashable value type."""
    q = Query().age.one_of([1, 2, 3])
    assert q({'age': 2}) is True
    assert q({'age': 4}) is False


def test_one_of_returns_false_for_missing_key():
    """one_of() should return False when the key is missing (path error)."""
    q = Query().name.one_of(['John', 'Jane'])
    assert q({}) is False


def test_one_of_returns_query_instance():
    """one_of() should return a QueryInstance."""
    result = Query().name.one_of(['John'])
    assert isinstance(result, QueryInstance)

def test_fragment_matches_subdocument():
    """fragment() should match when the document contains all the fragment's key/value pairs."""
    q = Query().fragment({'name': 'John', 'age': 30})
    assert q({'name': 'John', 'age': 30, 'extra': 'data'}) is True


def test_fragment_does_not_match_partial_overlap():
    """fragment() should not match if any fragment key has a different value."""
    q = Query().fragment({'name': 'John', 'age': 30})
    assert q({'name': 'John', 'age': 31}) is False


def test_fragment_does_not_match_missing_key():
    """fragment() should not match if a fragment key is missing from the document."""
    q = Query().fragment({'name': 'John', 'age': 30})
    assert q({'name': 'John'}) is False


def test_fragment_works_on_empty_query_path():
    """fragment() should be usable on a Query with no path (allow_empty_path=True)."""
    q = Query().fragment({'name': 'John'})
    assert q({'name': 'John'}) is True
    assert q({'name': 'Jane'}) is False
    assert q({}) is False


def test_fragment_with_empty_fragment_is_vacuously_true():
    """fragment({}) should match any document (vacuously true)."""
    q = Query().fragment({})
    assert q({}) is True
    assert q({'any': 'value'}) is True


def test_fragment_returns_query_instance():
    """fragment() should return a QueryInstance."""
    result = Query().fragment({'name': 'John'})
    assert isinstance(result, QueryInstance)

def test_noop_always_returns_true():
    """noop() should produce a query that always evaluates to True."""
    q = Query().noop()
    assert q({}) is True
    assert q({'any': 'value'}) is True
    assert q({'nested': {'x': 1}}) is True


def test_noop_returns_query_instance():
    """noop() should return a QueryInstance, not a Query."""
    result = Query().noop()
    assert isinstance(result, QueryInstance)


def test_noop_is_cacheable():
    """noop() should be cacheable."""
    assert Query().noop().is_cacheable() is True

def test_map_transforms_value_in_path():
    """map() should add a callable to the path that transforms the value before the comparison."""
    # The lambda doubles the resolved value before the equality test
    q = Query().num.map(lambda x: x * 2) == 4
    assert q({'num': 2}) is True   # 2*2 == 4
    assert q({'num': 3}) is False  # 3*2 != 4


def test_map_appends_callable_to_path():
    """map() should append the callable as the last element of the path."""
    q = Query().items.map(lambda x: x)
    assert len(q._path) == 2
    assert q._path[0] == 'items'
    assert callable(q._path[1])


def test_map_makes_query_uncacheable():
    """map() should set the hash to None, making the query uncacheable."""
    q = Query().num.map(lambda x: x * 2)
    assert q.is_cacheable() is False


def test_map_does_not_mutate_parent():
    """map() should not mutate the original query's path or hash."""
    parent = Query().num
    child = parent.map(lambda x: x * 2)
    assert parent._path == ('num',)
    assert len(child._path) == 2
    # Parent should still be cacheable; child should not
    assert parent.is_cacheable() is True
    assert child.is_cacheable() is False


def test_map_chained_with_any():
    """map() should work when combined with any() - transformation precedes element test."""
    # After map, the list is reversed; any() checks if any element equals 3
    q = Query().items.map(lambda lst: list(reversed(lst))).any(lambda y: y == 1)
    assert q({'items': [3, 2, 1]}) is True
    assert q({'items': [4, 5, 6]}) is False

def test_and_operator_combines_queries():
    """The & operator should combine two queries with logical AND."""
    q1 = Query().name == 'John'
    q2 = Query().age == 30
    combined = q1 & q2

    assert combined({'name': 'John', 'age': 30}) is True
    assert combined({'name': 'John', 'age': 25}) is False
    assert combined({'name': 'Jane', 'age': 30}) is False
    assert combined({'name': 'Jane', 'age': 25}) is False


def test_and_operator_with_query_methods():
    """The & operator should work with method-based queries like exists()."""
    q = (Query().name.exists()) & (Query().age > 0)
    assert q({'name': 'John', 'age': 25}) is True
    assert q({'name': 'John', 'age': -1}) is False
    assert q({'age': 25}) is False

def test_or_operator_combines_queries():
    """The | operator should combine two queries with logical OR."""
    q1 = Query().name == 'John'
    q2 = Query().age == 30
    combined = q1 | q2

    assert combined({'name': 'John', 'age': 25}) is True
    assert combined({'name': 'Jane', 'age': 30}) is True
    assert combined({'name': 'John', 'age': 30}) is True
    assert combined({'name': 'Jane', 'age': 25}) is False

def test_where_is_shorthand_for_query_item_access():
    """where(key) should be equivalent to Query()[key] and produce the same path."""
    q = where('name')
    assert q._path == ('name',)


def test_where_supports_comparison_operators():
    """A where() query should support all comparison operators just like Query()."""
    q = where('name') == 'John'
    assert q({'name': 'John'}) is True
    assert q({'name': 'Jane'}) is False


def test_where_supports_query_methods():
    """A where() query should support method-based queries like exists() and matches()."""
    assert where('name').exists()({'name': 'John'}) is True
    assert where('name').exists()({}) is False
    assert where('name').matches(r'^\w+$')({'name': 'John'}) is True
    assert where('name').matches(r'^\w+$')({'name': 'John Doe'}) is False

def test_query_with_path_is_cacheable():
    """A Query with a path should be cacheable."""
    assert Query().name.is_cacheable() is True
    assert Query().user.name.is_cacheable() is True
