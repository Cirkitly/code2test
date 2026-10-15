import pytest
from tinydb.queries import QueryInstance

@pytest.fixture
def cacheable_name_query():
    """A query instance that has a hashval and therefore is cacheable."""
    return QueryInstance(lambda doc: doc.get('name') == 'alice', ('name', 'alice'))

@pytest.fixture
def cacheable_age_query():
    """A second cacheable query instance with a different hashval."""
    return QueryInstance(lambda doc: doc.get('age') == 30, ('age', 30))

@pytest.fixture
def non_cacheable_query():
    """A query instance without a hashval, so it cannot be used in a cache."""
    return QueryInstance(lambda doc: True, None)

@pytest.fixture
def exploding_query():
    """A query whose test raises if it is ever evaluated."""
    def test(doc):
        raise AssertionError('this query must not be evaluated')

    return QueryInstance(test, ('exploding',))

def test_query_instance_evaluates_its_test_function_against_the_given_value():
    """Calling a query instance runs its test function on the passed document."""
    query = QueryInstance(lambda doc: doc.get('name') == 'alice', ('name', 'alice'))

    assert query({'name': 'alice'}) is True
    assert query({'name': 'bob'}) is False

def test_query_instance_passes_the_value_unchanged_to_the_test_function():
    """The exact object handed to __call__ is the object the test receives."""
    received = []

    def test(doc):
        received.append(doc)
        return True

    document = {'name': 'alice', 'nested': {'x': 1}}
    query = QueryInstance(test, ('record-call',))

    assert query(document) is True
    assert received == [document]
    assert received[0] is document

def test_query_instance_returns_the_raw_result_of_the_test_function():
    """__call__ returns whatever the test function returned, without coercion."""
    sentinel = object()
    query = QueryInstance(lambda doc: sentinel, ('sentinel',))

    assert query({}) is sentinel

def test_query_instance_propagates_exceptions_raised_by_the_test_function():
    """Errors raised inside a user supplied test function are not swallowed."""
    def test(doc):
        raise ValueError('boom')

    query = QueryInstance(test, ('boom',))

    with pytest.raises(ValueError, match='boom'):
        query({})

def test_query_instance_with_non_callable_test_raises_type_error_when_called():
    """Calling a query whose test is not callable is a programming error."""
    query = QueryInstance(None, ('none',))

    with pytest.raises(TypeError):
        query({})

def test_is_cacheable_is_true_when_a_hashval_is_given():
    """A query with a hashval can be used as a cache key."""
    query = QueryInstance(lambda doc: True, ('name', 'alice'))

    assert query.is_cacheable() is True

def test_is_cacheable_is_false_when_hashval_is_none():
    """A query without a hashval cannot be cached."""
    query = QueryInstance(lambda doc: True, None)

    assert query.is_cacheable() is False

def test_is_cacheable_is_true_even_for_falsy_hashvals():
    """Cacheability is decided by 'hashval is not None', not by truthiness."""
    assert QueryInstance(lambda doc: True, 0).is_cacheable() is True
    assert QueryInstance(lambda doc: True, ()).is_cacheable() is True

def test_hash_is_the_hash_of_the_hashval(cacheable_name_query):
    """The hash of a query is derived directly from its hashval."""
    assert hash(cacheable_name_query) == hash(('name', 'alice'))

def test_hash_is_stable_for_equal_hashvals(cacheable_name_query):
    """Two instances describing the same query hash the same way."""
    other = QueryInstance(lambda doc: False, ('name', 'alice'))

    assert hash(other) == hash(cacheable_name_query)

def test_hash_of_non_cacheable_query_is_the_hash_of_none(non_cacheable_query):
    """A query with hashval None still hashes, using hash(None)."""
    assert hash(non_cacheable_query) == hash(None)

def test_hash_raises_type_error_for_an_unhashable_hashval():
    """An unhashable hashval makes the query unusable as a dict key."""
    query = QueryInstance(lambda doc: True, ['unhashable'])

    with pytest.raises(TypeError):
        hash(query)

def test_query_instance_can_be_used_as_a_cache_key(cacheable_name_query):
    """An equivalent query finds the entry stored under an equal query."""
    equivalent = QueryInstance(lambda doc: False, ('name', 'alice'))
    cache = {cacheable_name_query: 'result'}

    assert cache[equivalent] == 'result'

def test_queries_with_different_hashvals_are_separate_cache_entries(cacheable_name_query, cacheable_age_query):
    """Different hashvals do not collide in a query cache."""
    cache = {cacheable_name_query: 'alice', cacheable_age_query: 'thirty'}

    assert len(cache) == 2
    assert cache[cacheable_name_query] == 'alice'
    assert cache[cacheable_age_query] == 'thirty'

def test_repr_shows_class_prefix_and_hashval(cacheable_name_query):
    """The repr is 'QueryImpl' followed by the hashval."""
    assert repr(cacheable_name_query) == 'QueryImpl{}'.format(('name', 'alice'))

def test_repr_of_non_cacheable_query_shows_none(non_cacheable_query):
    """A query without hashval renders as 'QueryImplNone'."""
    assert repr(non_cacheable_query) == 'QueryImplNone'

def test_equality_compares_hashvals_not_test_functions(cacheable_name_query):
    """Two instances are equal when their hashvals match, regardless of the test."""
    other = QueryInstance(lambda doc: False, ('name', 'alice'))

    assert (cacheable_name_query == other) is True
    assert (cacheable_name_query != other) is False

def test_queries_with_different_hashvals_are_not_equal(cacheable_name_query, cacheable_age_query):
    """Different hashvals mean different queries."""
    assert (cacheable_name_query == cacheable_age_query) is False
    assert (cacheable_name_query != cacheable_age_query) is True

def test_two_non_cacheable_queries_are_equal(non_cacheable_query):
    """Non-cacheable queries all share hashval None and therefore compare equal."""
    other = QueryInstance(lambda doc: False, None)

    assert (non_cacheable_query == other) is True

def test_equality_with_non_query_instance_is_always_false(cacheable_name_query):
    """Comparing against anything but a query instance yields False."""
    assert (cacheable_name_query == ('name', 'alice')) is False
    assert (cacheable_name_query == 'QueryImpl') is False
    assert (cacheable_name_query == None) is False  # noqa: E711

def test_equal_queries_have_equal_hashes(cacheable_name_query):
    """Equality and hashing stay consistent, as required for cache lookups."""
    other = QueryInstance(lambda doc: False, ('name', 'alice'))

    assert (cacheable_name_query == other) == (hash(cacheable_name_query) == hash(other))

def test_and_is_true_only_if_both_operands_match(cacheable_name_query, cacheable_age_query):
    """Logical AND requires both sub-queries to match the document."""
    combined = cacheable_name_query & cacheable_age_query

    assert combined({'name': 'alice', 'age': 30}) is True
    assert combined({'name': 'alice', 'age': 31}) is False
    assert combined({'name': 'bob', 'age': 30}) is False
    assert combined({'name': 'bob', 'age': 31}) is False

def test_and_returns_a_cacheable_query_instance(cacheable_name_query, cacheable_age_query):
    """Combining two cacheable queries yields another cacheable query instance."""
    combined = cacheable_name_query & cacheable_age_query

    assert isinstance(combined, QueryInstance)
    assert combined.is_cacheable() is True

def test_and_is_commutative_for_equality_and_hash(cacheable_name_query, cacheable_age_query):
    """'a & b' equals 'b & a' because the hashval uses a frozenset."""
    assert (cacheable_name_query & cacheable_age_query) == (cacheable_age_query & cacheable_name_query)
    assert hash(cacheable_name_query & cacheable_age_query) == hash(cacheable_age_query & cacheable_name_query)

def test_and_is_not_cacheable_if_any_operand_is_not_cacheable(cacheable_name_query, non_cacheable_query):
    """A single non-cacheable operand makes the whole conjunction non-cacheable."""
    assert (cacheable_name_query & non_cacheable_query).is_cacheable() is False
    assert (non_cacheable_query & cacheable_name_query).is_cacheable() is False

def test_and_short_circuits_when_the_left_operand_is_false(exploding_query):
    """The right operand is not evaluated when the left one already failed."""
    combined = QueryInstance(lambda doc: False, ('left',)) & exploding_query

    assert combined({}) is False

def test_and_does_not_modify_its_operands(cacheable_name_query, cacheable_age_query):
    """Combining creates a new query and leaves the operands untouched."""
    combined = cacheable_name_query & cacheable_age_query

    assert cacheable_name_query({'name': 'alice'}) is True
    assert cacheable_age_query({'age': 30}) is True
    assert cacheable_age_query({'age': 31}) is False
    assert combined({'name': 'alice'}) is False

def test_nested_and_is_cacheable_and_evaluates_every_part(cacheable_name_query, cacheable_age_query):
    """Chained conjunctions keep working and stay cacheable."""
    combined = (cacheable_name_query & cacheable_age_query) & cacheable_name_query

    assert combined.is_cacheable() is True
    assert combined({'name': 'alice', 'age': 30}) is True
    assert combined({'name': 'alice', 'age': 31}) is False

def test_and_raises_attribute_error_for_a_non_query_operand(cacheable_name_query):
    """Combining with a foreign object is a programming error."""
    with pytest.raises(AttributeError):
        cacheable_name_query & 'not a query'

def test_or_is_true_if_any_operand_matches(cacheable_name_query, cacheable_age_query):
    """Logical OR matches when at least one sub-query matches the document."""
    combined = cacheable_name_query | cacheable_age_query

    assert combined({'name': 'alice', 'age': 30}) is True
    assert combined({'name': 'alice', 'age': 31}) is True
    assert combined({'name': 'bob', 'age': 30}) is True
    assert combined({'name': 'bob', 'age': 31}) is False

def test_or_returns_a_cacheable_query_instance(cacheable_name_query, cacheable_age_query):
    """Combining two cacheable queries with OR yields a cacheable instance."""
    combined = cacheable_name_query | cacheable_age_query

    assert isinstance(combined, QueryInstance)
    assert combined.is_cacheable() is True

def test_or_is_commutative_for_equality_and_hash(cacheable_name_query, cacheable_age_query):
    """'a | b' equals 'b | a' because the hashval uses a frozenset."""
    assert (cacheable_name_query | cacheable_age_query) == (cacheable_age_query | cacheable_name_query)
    assert hash(cacheable_name_query | cacheable_age_query) == hash(cacheable_age_query | cacheable_name_query)

def test_or_is_not_cacheable_if_any_operand_is_not_cacheable(cacheable_name_query, cacheable_age_query, non_cacheable_query):
    """A single non-cacheable operand makes the whole disjunction non-cacheable."""
    assert (cacheable_name_query | non_cacheable_query).is_cacheable() is False
    assert (non_cacheable_query | cacheable_age_query).is_cacheable() is False

def test_or_short_circuits_when_the_left_operand_is_true(cacheable_name_query, exploding_query):
    """The right operand is not evaluated when the left one already matched."""
    combined = cacheable_name_query | exploding_query

    assert combined({'name': 'alice'}) is True

def test_or_raises_attribute_error_for_a_non_query_operand(cacheable_name_query):
    """Combining with a foreign object is a programming error."""
    with pytest.raises(AttributeError):
        cacheable_name_query | 42

def test_and_and_or_results_are_not_equal(cacheable_name_query, cacheable_age_query):
    """Conjunctions and disjunctions of the same operands are different queries."""
    assert (cacheable_name_query & cacheable_age_query) != (cacheable_name_query | cacheable_age_query)

def test_invert_negates_the_query_result(cacheable_name_query):
    """Logical NOT flips the outcome of the wrapped query."""
    inverted = ~cacheable_name_query

    assert inverted({'name': 'alice'}) is False
    assert inverted({'name': 'bob'}) is True
    assert inverted.is_cacheable() is True

def test_invert_wraps_the_hashval_in_a_not_tuple(cacheable_name_query):
    """The negated query is identified by ('not', hashval)."""
    assert (~cacheable_name_query) == QueryInstance(lambda doc: False, ('not', ('name', 'alice')))

def test_double_inversion_evaluates_like_the_original(cacheable_name_query):
    """Applying NOT twice restores the original evaluation behaviour."""
    double_inverted = ~~cacheable_name_query

    assert double_inverted({'name': 'alice'}) is True
    assert double_inverted({'name': 'bob'}) is False

def test_double_inversion_has_a_different_hashval_than_the_original(cacheable_name_query):
    """Negation changes the query identity even though behaviour is restored."""
    assert (~~cacheable_name_query) != cacheable_name_query

def test_invert_of_a_non_cacheable_query_stays_non_cacheable(non_cacheable_query):
    """Without a hashval there is nothing stable to wrap in a 'not' tuple."""
    inverted = ~non_cacheable_query

    assert inverted.is_cacheable() is False
    assert inverted({}) is False
    assert inverted == non_cacheable_query

def test_invert_does_not_modify_the_original_query(cacheable_name_query):
    """Negating returns a new instance and leaves the original operational."""
    inverted = ~cacheable_name_query

    assert cacheable_name_query({'name': 'alice'}) is True
    assert inverted({'name': 'alice'}) is False
    assert inverted is not cacheable_name_query
