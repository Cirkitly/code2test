import re
import operator
import pytest
from tinydb.queries import Query
from tinydb.queries import where

@pytest.fixture
def users():
    """A tiny collection of documents that queries can be run against."""
    return [
        {'name': 'John Doe', 'age': 30, 'logged-in': True},
        {'name': 'Jane Doe', 'age': 25, 'logged-in': False},
        {'name': 'Bob', 'age': 30},
    ]

def test_orm_style_attribute_query_matches_documents():
    """The documented ORM style (``Query().field == value``) filters documents."""
    query = Query().name == 'John Doe'

    assert query({'name': 'John Doe'}) is True
    assert query({'name': 'Jane Doe'}) is False
    # A missing field can never match, it does not raise
    assert query({'other': 'John Doe'}) is False

def test_item_access_syntax_matches_documents():
    """``Query()['field']`` is an alternative to attribute access."""
    assert (Query()['logged-in'] == True)({'logged-in': True}) is True  # noqa: E712
    assert (Query()['logged-in'] == True)({'logged-in': False}) is False  # noqa: E712

def test_where_is_shorthand_for_query_item_access():
    """``where(key)`` behaves exactly like ``Query()[key]``."""
    assert (where('value') == True)({'value': True}) is True  # noqa: E712
    assert (where('value') == True)({'value': False}) is False  # noqa: E712
    assert (where('missing') == 1)({}) is False

def test_query_can_be_applied_to_multiple_documents(users):
    """A generated query can be used to filter a whole list of documents."""
    query = Query().age == 30

    matched = [doc for doc in users if query(doc)]

    assert matched == [
        {'name': 'John Doe', 'age': 30, 'logged-in': True},
        {'name': 'Bob', 'age': 30},
    ]

def test_inequality_query_matches_documents():
    """``!=`` builds the complementary query of ``==``."""
    query = Query().f1 != 42

    assert query({'f1': 43}) is True
    assert query({'f1': 42}) is False
    assert query({}) is False

@pytest.mark.parametrize(
    'op_name, operand, matching_doc, non_matching_doc',
    [
        ('lt', 3, {'f1': 2}, {'f1': 3}),
        ('le', 3, {'f1': 3}, {'f1': 4}),
        ('gt', 3, {'f1': 4}, {'f1': 3}),
        ('ge', 3, {'f1': 3}, {'f1': 2}),
    ],
)
def test_comparison_operators_build_queries(
    op_name, operand, matching_doc, non_matching_doc
):
    """All ordering operators generate queries for their respective test."""
    op = getattr(operator, op_name)
    query = op(Query().f1, operand)

    assert query(matching_doc) is True
    assert query(non_matching_doc) is False
    # A missing field never satisfies a comparison
    assert query({}) is False

def test_comparison_errors_from_the_test_function_propagate():
    """Only path resolution errors are swallowed, comparison errors are not."""
    with pytest.raises(TypeError):
        (Query().f1 < 1)({'f1': None})

def test_nested_query_paths_resolve_through_mappings():
    """Chained attribute access builds a nested query path."""
    query = Query().f1.f2 == 1

    assert query({'f1': {'f2': 1}}) is True
    assert query({'f1': {'f2': 2}}) is False
    # KeyError while resolving the path -> no match
    assert query({'f1': {'f3': 1}}) is False
    # TypeError while resolving the path (int is not subscriptable) -> no match
    assert query({'f1': 42}) is False

def test_equality_against_containers():
    """Values such as mappings and lists can be compared against as well."""
    assert (Query().f1 == {'a': 1})({'f1': {'a': 1}}) is True
    assert (Query().f1 == {'a': 1})({'f1': {'a': 2}}) is False
    assert (Query().f1 == [1, 2])({'f1': [1, 2]}) is True
    assert (Query().f1 == [1, 2])({'f1': [2, 1]}) is False

def test_exists_query():
    """``exists()`` only tests for the presence of a key, not for its value."""
    query = Query().f1.exists()

    assert query({'f1': None}) is True
    assert query({'f1': 0}) is True
    assert query({'f2': 1}) is False
    assert query({}) is False

def test_attribute_access_creates_independent_query_objects():
    """Every attribute access returns a new query object with its own path."""
    base = Query()
    first = base.f1
    second = base.f2

    assert (first == 1)({'f1': 1, 'f2': 2}) is True
    assert (second == 2)({'f1': 1, 'f2': 2}) is True
    # ``first`` was not modified by creating ``second``
    assert (first == 1)({'f2': 2}) is False

def test_matches_requires_whole_string_to_match():
    """``matches()`` anchors the regex at the beginning of the value."""
    query = Query().f1.matches(r'\w+')

    assert query({'f1': 'abc'}) is True
    assert query({'f1': 'abc123'}) is True
    # ``\w+`` also matches at the start of ``123abc`` (re.match is not a
    # full-string match, it only anchors at the beginning)
    assert query({'f1': '123abc'}) is True

    # A regex that does not match at the start of the value does not match
    anchored = Query().f1.matches(r'abc')
    assert anchored({'f1': '123abc'}) is False
    assert anchored({'f1': 'abc123'}) is True

    # Missing fields and non-string values never match
    assert query({}) is False
    assert query({'f1': 42}) is False

def test_matches_returns_false_for_non_string_values():
    """Non-string values simply do not match a regex based query."""
    query = Query().f1.matches(r'\w+')

    assert query({'f1': 42}) is False
    assert query({'f1': None}) is False
    assert query({'f1': ['abc']}) is False

def test_matches_supports_regex_flags():
    """Regex flags are forwarded to ``re.match``."""
    assert (Query().f1.matches('b', re.IGNORECASE))({'f1': 'B'}) is True
    assert (Query().f1.matches('b'))({'f1': 'B'}) is False

def test_search_matches_substrings():
    """``search()`` finds the regex anywhere inside the value."""
    query = Query().f1.search('b')

    assert query({'f1': 'abcb'}) is True
    # 'b' occurs at the end of the value, so this matches as well
    assert query({'f1': 'abc'}) is True
    # 'b' does not occur anywhere in the value
    assert query({'f1': 'xyz'}) is False
    assert query({'f1': 42}) is False
    assert query({}) is False

def test_search_supports_regex_flags():
    """Regex flags are forwarded to ``re.search``."""
    assert (Query().f1.search('B', re.IGNORECASE))({'f1': 'abc'}) is True
    assert (Query().f1.search('B'))({'f1': 'abc'}) is False

def test_test_runs_user_function_with_extra_arguments():
    """``test()`` calls the given function with the value and extra args."""
    query = Query().f1.test(lambda value, threshold: value > threshold, 3)

    assert query({'f1': 4}) is True
    assert query({'f1': 2}) is False
    assert query({}) is False

def test_any_with_a_list_condition():
    """``any()`` with a list checks for at least one common element."""
    query = Query().f1.any([1, 2, 3])

    assert query({'f1': [1, 2]}) is True
    assert query({'f1': [3, 4, 5]}) is True
    assert query({'f1': [4, 5]}) is False
    assert query({}) is False

def test_any_with_a_query_condition():
    """``any()`` with a query matches if at least one element matches."""
    query = Query().f1.any(Query().f2 == 1)

    assert query({'f1': [{'f2': 1}, {'f2': 0}]}) is True
    assert query({'f1': [{'f2': 0}]}) is False

def test_any_returns_false_for_non_sequence_values():
    """``any()`` requires the tested value to be a sequence."""
    query = Query().f1.any([1, 2, 3])

    assert query({'f1': 42}) is False
    assert query({'f1': None}) is False

def test_all_with_a_list_condition():
    """``all()`` with a list requires the list to be contained in the value."""
    query = Query().f1.all([1, 2, 3])

    assert query({'f1': [1, 2, 3]}) is True
    assert query({'f1': [1, 2, 3, 4, 5]}) is True
    assert query({'f1': [1, 2]}) is False
    assert query({}) is False

def test_all_with_a_query_condition():
    """``all()`` with a query matches only if every element matches."""
    query = Query().f1.all(Query().f2 == 1)

    assert query({'f1': [{'f2': 1}, {'f2': 1}]}) is True
    assert query({'f1': [{'f2': 1}, {'f2': 0}]}) is False

def test_all_returns_false_for_non_sequence_values():
    """``all()`` requires the tested value to be a sequence."""
    query = Query().f1.all([1, 2, 3])

    assert query({'f1': 42}) is False
    assert query({'f1': None}) is False

def test_one_of_matches_values_contained_in_the_given_items():
    """``one_of()`` checks whether the value is contained in the items."""
    query = Query().f1.one_of(['value 1', 'value 2'])

    assert query({'f1': 'value 1'}) is True
    assert query({'f1': 'value 2'}) is True
    assert query({'f1': 'value 3'}) is False
    assert query({}) is False

def test_one_of_supports_sets_and_mappings():
    """``one_of()`` also works with sets and lists of mappings."""
    set_query = Query().f1.one_of({'a', 'b'})
    assert set_query({'f1': 'a'}) is True
    assert set_query({'f1': 'c'}) is False

    mapping_query = Query().f1.one_of([{'a': 1}, {'b': 2}])
    assert mapping_query({'f1': {'a': 1}}) is True
    assert mapping_query({'f1': {'c': 3}}) is False

def test_fragment_matches_a_subset_of_the_document():
    """``fragment()`` matches documents that contain the given key/value pairs."""
    query = Query().fragment({'f1': 1})

    assert query({'f1': 1}) is True
    assert query({'f1': 1, 'f2': 2}) is True
    assert query({'f1': 2}) is False
    assert query({}) is False

def test_fragment_can_be_applied_to_a_nested_value():
    """A fragment query resolves its path first and then matches the fragment."""
    query = Query().nested.fragment({'a': 1})

    assert query({'nested': {'a': 1, 'b': 2}}) is True
    assert query({'nested': {'b': 2}}) is False
    assert query({'nested': []}) is False
    assert query({'other': {'a': 1}}) is False

def test_noop_matches_every_resolved_document():
    """``noop()`` always evaluates to ``True``, whatever the path is."""
    query = Query().noop()

    assert query({}) is True
    assert query({'f1': 1}) is True

    # ``noop()`` does not resolve the query path at all -- it is a plain
    # 'matches everything' query, which is handy as a base value when
    # composing queries dynamically
    assert (Query().f1.noop())({'f1': 1}) is True
    assert (Query().f1.noop())({'f2': 1}) is True

def test_noop_and_fragment_allow_an_empty_query_path():
    """``noop()`` and ``fragment()`` are usable without a query path."""
    assert Query().noop()({'f1': 1}) is True
    assert Query().fragment({'f1': 1})({'f1': 1, 'f2': 2}) is True

def test_map_adds_a_callable_to_the_query_path():
    """``map()`` adds an arbitrary function to the query path."""
    query = Query().values.map(lambda value: value['name'])

    assert (query == 'John')({'values': {'name': 'John'}}) is True
    assert (query == 'John')({'values': {'name': 'Jane'}}) is False
    # A KeyError inside the mapped function is handled like a missing field
    assert (query == 'John')({'values': {}}) is False

def test_map_queries_are_not_cacheable():
    """Mapped queries are not cacheable as callables may be mutable."""
    def resolve(value):
        return value

    assert (Query().f1 == 1).is_cacheable()
    assert not Query().f1.map(resolve).is_cacheable()
    assert not (Query().f1.map(resolve) == 1).is_cacheable()

def test_empty_query_raises_runtime_error_when_evaluated():
    """An empty ``Query()`` must not be evaluated."""
    with pytest.raises(RuntimeError, match='Empty query was evaluated'):
        Query()({})

@pytest.mark.parametrize(
    'build_query',
    [
        lambda q: q == 1,
        lambda q: q != 1,
        lambda q: q < 1,
        lambda q: q <= 1,
        lambda q: q > 1,
        lambda q: q >= 1,
        lambda q: q.exists(),
        lambda q: q.matches('a'),
        lambda q: q.search('a'),
        lambda q: q.test(lambda value: True),
        lambda q: q.any([1]),
        lambda q: q.all([1]),
        lambda q: q.one_of([1]),
    ],
    ids=[
        'eq', 'ne', 'lt', 'le', 'gt', 'ge', 'exists',
        'matches', 'search', 'test', 'any', 'all', 'one_of',
    ],
)
def test_query_tests_require_a_path(build_query):
    """Building a test on a path-less query raises a ``ValueError``."""
    with pytest.raises(ValueError, match='Query has no path'):
        build_query(Query())

def test_repr_shows_the_query_class_name():
    """``repr()`` of a query is its class name followed by parentheses."""
    assert repr(Query()) == 'Query()'

def test_subclass_attribute_access_preserves_the_subclass():
    """Subclasses of ``Query`` are preserved when building new queries."""
    class MyQuery(Query):
        pass

    query = MyQuery().field

    assert isinstance(query, MyQuery)
    assert repr(query) == 'MyQuery()'
    assert (query == 1)({'field': 1}) is True

def test_attribute_lookup_prefers_methods_over_field_queries():
    """Attribute access resolves ``Query`` methods, thus needing a path."""
    with pytest.raises(ValueError, match='Query has no path'):
        Query().test(lambda value: value == 1)

def test_getitem_creates_field_queries_even_for_method_names():
    """``[]`` always creates a field query, even for names of methods."""
    field_query = Query()['test']

    assert (field_query == 1)({'test': 1}) is True
    assert (field_query == 2)({'test': 1}) is False

    # 'matches' is a method name, but indexing still targets the field,
    # so the following regex test is run against the document field
    matches_query = Query()['matches']
    assert matches_query.matches('^a')({'matches': 'abc'}) is True
    assert matches_query.matches('^b')({'matches': 'abc'}) is False
    assert matches_query.matches('^a')({'other': 'abc'}) is False

def test_queries_with_the_same_path_share_the_same_hash():
    """Queries with an equal path are equal in terms of their hash."""
    assert hash(Query()) == hash(Query())
    assert hash(Query().f1) == hash(Query()['f1'])
    assert hash(Query().f1.f2) == hash(Query().f1.f2)
    assert hash(Query().f1) != hash(Query().f2)

def test_query_instances_for_equal_comparisons_hash_equally():
    """Generated queries are hashable, also for list/set right-hand sides."""
    assert hash(Query().f1 == 1) == hash(Query().f1 == 1)
    assert hash(Query().f1 == [1, 2]) == hash(Query().f1 == [1, 2])
    assert hash(Query().f1.one_of(['a', 'b'])) == hash(Query().f1.one_of(['a', 'b']))
    assert hash(Query().f1 == 1) != hash(Query().f1 == 2)
