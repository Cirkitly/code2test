import pytest
from typing import Any, Callable, Dict, List, Mapping, Optional
from tinydb.queries import QueryInstance
from tinydb.utils import freeze

def test_call_evaluates_test_against_value():
    """A QueryInstance evaluates to the boolean result of its test function."""
    def test(value):
        return value['name'] == 'Alice'

    query = QueryInstance(test, ('name', '==', 'Alice'))

    assert query({'name': 'Alice'}) is True
    assert query({'name': 'Bob'}) is False

def test_call_passes_value_object_to_test():
    """The mapping passed to __call__ is handed to the test callable unchanged."""
    seen = []

    def test(value):
        seen.append(value)
        return True

    document = {'name': 'Alice', 'age': 42}
    query = QueryInstance(test, ('noop',))

    assert query(document) is True
    assert seen == [document]
    assert seen[0] is document

def test_is_cacheable_true_when_hashval_given():
    """A query instance built with a hash value can be used in a query cache."""
    query = QueryInstance(lambda value: True, ('exists', 'name'))

    assert query.is_cacheable() is True

def test_is_cacheable_false_when_hashval_is_none():
    """A query instance built without a hash value must not be cached."""
    query = QueryInstance(lambda value: True, None)

    assert query.is_cacheable() is False

def test_is_cacheable_false_for_empty_hashval_container():
    """Only ``None`` disables caching: an empty-but-present hashval stays cacheable."""
    query = QueryInstance(lambda value: True, ())

    assert query.is_cacheable() is True

def test_hash_is_stable_for_same_query():
    """The same query description always produces the same hash (cache key stability)."""
    hashval = ('and', frozenset([('name', '==', 'Alice'), ('age', '==', 42)]))
    q1 = QueryInstance(lambda value: True, hashval)
    q2 = QueryInstance(lambda value: False, hashval)

    assert hash(q1) == hash(q2)
    assert hash(q1) == hash(q1)

def test_instance_usable_as_dict_key():
    """A cacheable query instance can be used as a key in a query cache dict."""
    query = QueryInstance(lambda value: True, ('exists', 'name'))
    cache = {query: 'result'}

    assert cache[query] == 'result'
    assert len(cache) == 1

def test_equal_hashvals_compare_equal():
    """Two query instances describing the same query compare equal."""
    hashval = ('where', 'name')
    q1 = QueryInstance(lambda value: True, hashval)
    q2 = QueryInstance(lambda value: False, hashval)

    assert q1 == q2

def test_different_hashvals_compare_unequal():
    """Query instances describing different queries are not equal."""
    q1 = QueryInstance(lambda value: True, ('name', '==', 'Alice'))
    q2 = QueryInstance(lambda value: True, ('name', '==', 'Bob'))

    assert not (q1 == q2)
    assert q1 != q2

@pytest.mark.parametrize('other', ['not a query', 42, None, ('where', 'name'), frozenset()])
def test_eq_with_non_query_instance_returns_false(other):
    """Comparing a query with a non-QueryInstance returns False instead of raising."""
    query = QueryInstance(lambda value: True, ('where', 'name'))

    assert (query == other) is False
    assert (query != other) is True

def test_repr_contains_hash_value():
    """The repr of a query instance exposes the hash value describing the query."""
    hashval = ('name', '==', 'Alice')
    query = QueryInstance(lambda value: True, hashval)

    result = repr(query)

    assert isinstance(result, str)
    assert result.startswith('QueryImpl')
    assert str(hashval) in result

def test_repr_of_not_cacheable_query_shows_none():
    """A query instance without a hash value is rendered as ``QueryImplNone``."""
    query = QueryInstance(lambda value: True, None)

    assert repr(query) == 'QueryImplNone'

def test_and_matches_only_when_both_match():
    """Combining two queries with AND requires both to match."""
    is_alice = QueryInstance(lambda value: value['name'] == 'Alice', ('name', '==', 'Alice'))
    is_adult = QueryInstance(lambda value: value['age'] >= 18, ('age', '>=', 18))

    combined = is_alice & is_adult

    assert isinstance(combined, QueryInstance)
    assert combined({'name': 'Alice', 'age': 42}) is True
    assert combined({'name': 'Alice', 'age': 12}) is False
    assert combined({'name': 'Bob', 'age': 42}) is False

def test_or_matches_when_either_matches():
    """Combining two queries with OR matches if either query matches."""
    is_alice = QueryInstance(lambda value: value['name'] == 'Alice', ('name', '==', 'Alice'))
    is_adult = QueryInstance(lambda value: value['age'] >= 18, ('age', '>=', 18))

    combined = is_alice | is_adult

    assert isinstance(combined, QueryInstance)
    assert combined({'name': 'Alice', 'age': 42}) is True
    assert combined({'name': 'Alice', 'age': 12}) is True
    assert combined({'name': 'Bob', 'age': 42}) is True
    assert combined({'name': 'Bob', 'age': 12}) is False

def test_invert_inverts_result():
    """Inverting a query inverts its evaluation result."""
    is_alice = QueryInstance(lambda value: value['name'] == 'Alice', ('name', '==', 'Alice'))

    inverted = ~is_alice

    assert isinstance(inverted, QueryInstance)
    assert inverted({'name': 'Alice'}) is False
    assert inverted({'name': 'Bob'}) is True

def test_modifiers_do_not_mutate_operands():
    """Combining or inverting queries returns new objects and leaves operands unchanged."""
    left = QueryInstance(lambda value: True, ('left',))
    right = QueryInstance(lambda value: False, ('right',))

    combined_and = left & right
    combined_or = left | right
    inverted = ~left

    assert left({'x': 1}) is True
    assert right({'x': 1}) is False
    assert combined_and is not left and combined_and is not right
    assert combined_or is not left and combined_or is not right
    assert inverted is not left

def test_combination_of_two_cacheable_queries_is_cacheable():
    """Combining two cacheable queries yields a cacheable query with its own hash."""
    left = QueryInstance(lambda value: True, ('left',))
    right = QueryInstance(lambda value: False, ('right',))

    assert (left & right).is_cacheable() is True
    assert (left | right).is_cacheable() is True
    assert (~left).is_cacheable() is True

def test_combination_with_non_cacheable_query_is_not_cacheable():
    """A query that cannot be hashed poisons the cacheability of the combined query."""
    cacheable = QueryInstance(lambda value: True, ('cacheable',))
    uncacheable = QueryInstance(lambda value: True, None)

    assert (cacheable & uncacheable).is_cacheable() is False
    assert (uncacheable & cacheable).is_cacheable() is False
    assert (cacheable | uncacheable).is_cacheable() is False
    assert (uncacheable | cacheable).is_cacheable() is False

def test_inverted_non_cacheable_query_is_not_cacheable():
    """Inverting a non-cacheable query keeps it non-cacheable."""
    uncacheable = QueryInstance(lambda value: False, None)

    inverted = ~uncacheable

    assert inverted.is_cacheable() is False
    assert inverted({'anything': 1}) is True

def test_inversion_is_deterministic():
    """Double negation evaluates like the original and has a stable, nested hash."""
    query = QueryInstance(lambda value: value['x'] > 0, ('x', '>', 0))

    double_inverted = ~~query

    # The evaluation result is unchanged ...
    assert double_inverted({'x': 1}) is True
    assert double_inverted({'x': -1}) is False

    # ... but it is a new, cacheable instance whose hash description nests
    # the 'not' operation twice (it is not simplified back to the original)
    assert double_inverted is not query
    assert double_inverted.is_cacheable()
    assert double_inverted == ~~query
    assert hash(double_inverted) == hash(~~query)
    assert double_inverted != query

def test_and_is_commutative_for_equality():
    """AND is commutative: a & b and b & a describe the same query."""
    left = QueryInstance(lambda value: value['a'] == 1, ('a', '==', 1))
    right = QueryInstance(lambda value: value['b'] == 2, ('b', '==', 2))

    assert (left & right) == (right & left)
    assert hash(left & right) == hash(right & left)

def test_or_is_commutative_for_equality():
    """OR is commutative: a | b and b | a describe the same query."""
    left = QueryInstance(lambda value: value['a'] == 1, ('a', '==', 1))
    right = QueryInstance(lambda value: value['b'] == 2, ('b', '==', 2))

    assert (left | right) == (right | left)
    assert hash(left | right) == hash(right | left)

def test_and_and_or_combinations_differ():
    """A conjunction and a disjunction of the same operands are different queries."""
    left = QueryInstance(lambda value: value['a'] == 1, ('a', '==', 1))
    right = QueryInstance(lambda value: value['b'] == 2, ('b', '==', 2))

    assert (left & right) != (left | right)
    assert (~left) != left

def test_inverted_query_is_not_equal_to_query():
    """A negated query is a different query than the query it was built from."""
    query = QueryInstance(lambda value: value['x'] > 0, ('x', '>', 0))

    assert (~query) != query
    assert hash(~query) != hash(query)

def test_nested_combinations_evaluate_correctly():
    """Nested combinations (AND of OR, OR of AND, mixed negation) evaluate correctly."""
    is_alice = QueryInstance(lambda value: value['name'] == 'Alice', ('name', '==', 'Alice'))
    is_bob = QueryInstance(lambda value: value['name'] == 'Bob', ('name', '==', 'Bob'))
    is_adult = QueryInstance(lambda value: value['age'] >= 18, ('age', '>=', 18))
    is_senior = QueryInstance(lambda value: value['age'] >= 65, ('age', '>=', 65))

    query = (is_alice | is_bob) & (is_adult | is_senior)

    assert query({'name': 'Alice', 'age': 20}) is True
    assert query({'name': 'Alice', 'age': 10}) is False
    assert query({'name': 'Carol', 'age': 70}) is False
    assert query({'name': 'Bob', 'age': 70}) is True
    assert query.is_cacheable() is True

def test_combined_queries_have_stable_hashes_across_rebuilds():
    """Two independently built but identical queries hash the same (stable cache keys)."""
    def build():
        left = QueryInstance(lambda value: value['a'] == 1, ('a', '==', 1))
        right = QueryInstance(lambda value: value['b'] == 2, ('b', '==', 2))
        return (left & right) | (~right)

    first, second = build(), build()

    assert first == second
    assert hash(first) == hash(second)
    assert {first: 1}[second] == 1

def test_query_with_frozen_dict_hashval_is_hashable():
    """Queries built from document fragments use freeze() to stay hashable."""
    fragment = freeze({'name': 'Alice', 'age': 42})
    query = QueryInstance(lambda value: value == fragment, ('fragment', fragment))

    assert hash(query) == hash(QueryInstance(lambda value: False, ('fragment', fragment)))
    assert {query: 'matched'}[query] == 'matched'
    assert query({'name': 'Alice', 'age': 42}) is True
    assert query({'name': 'Bob', 'age': 42}) is False

def test_query_without_hashval_hashes_but_is_not_cacheable():
    """Non-cacheable queries still hash (to the hash of None) but must not be cached."""
    q1 = QueryInstance(lambda value: True, None)
    q2 = QueryInstance(lambda value: False, None)

    assert hash(q1) == hash(q2)
    assert q1 == q2
    assert q1.is_cacheable() is False

def test_call_does_not_catch_exceptions_from_test():
    """Exceptions raised inside the test callable are propagated to the caller."""
    def test(value):
        raise KeyError('missing')

    query = QueryInstance(test, ('raises',))

    with pytest.raises(KeyError):
        query({'name': 'Alice'})

def test_call_with_non_mapping_value_forwards_as_is():
    """The query itself does no validation; the test callable decides how to handle values."""
    def test(value):
        return value is None

    query = QueryInstance(test, ('is', None))

    assert query(None) is True
    assert query({'a': 1}) is False
    assert query([]) is False

def test_operands_are_evaluated_in_order_with_short_circuit():
    """AND/OR evaluate the right operand only when the left operand does not decide."""
    calls = []

    def make(name, result):
        def test(value):
            calls.append(name)
            return result
        return QueryInstance(test, (name,))

    # AND: a falsy left operand already decides -> right is not evaluated
    left_false = make('left_false', False)
    right = make('right', True)

    assert (left_false & right)({}) is False
    assert calls == ['left_false']

    # AND: a truthy left operand does not decide -> right is evaluated
    calls.clear()
    left_true = make('left_true', True)

    assert (left_true & right)({}) is True
    assert calls == ['left_true', 'right']

    # OR: a truthy left operand already decides -> right is not evaluated
    calls.clear()
    right_false = make('right_false', False)

    assert (left_true | right_false)({}) is True
    assert calls == ['left_true']

    # OR: a falsy left operand does not decide -> right is evaluated
    calls.clear()

    assert (left_false | right_false)({}) is False
    assert calls == ['left_false', 'right_false']
