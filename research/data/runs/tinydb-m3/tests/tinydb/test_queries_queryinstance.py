import pytest
from tinydb.queries import QueryInstance

def test_call_returns_result_of_test_function():
    """Calling a QueryInstance returns the boolean result of its test function."""
    query = QueryInstance(lambda value: value.get('x') == 1, ('x', '==', 1))

    assert query({'x': 1}) is True
    assert query({'x': 2}) is False

def test_call_forwards_value_to_test_function():
    """The value passed to __call__ is forwarded verbatim to the test function."""
    captured = []

    def test_func(value):
        captured.append(value)
        return True

    query = QueryInstance(test_func, ('capture',))
    sentinel = {'marker': object()}

    result = query(sentinel)

    assert result is True
    assert captured == [sentinel]

def test_call_invokes_test_function_each_time():
    """Every call to __call__ re-invokes the underlying test function."""
    counter = [0]

    def test_func(value):
        counter[0] += 1
        return True

    query = QueryInstance(test_func, ('counter',))

    query({})
    query({})
    query({})

    assert counter[0] == 3

def test_is_cacheable_returns_true_when_hashval_provided():
    """A QueryInstance with a hashval is cacheable."""
    query = QueryInstance(lambda value: True, ('hash',))

    assert query.is_cacheable() is True

def test_is_cacheable_returns_false_when_hashval_is_none():
    """A QueryInstance without a hashval is not cacheable."""
    query = QueryInstance(lambda value: True, None)

    assert query.is_cacheable() is False

def test_hash_returns_hash_of_hashval():
    """__hash__ is hash(self._hash)."""
    hashval = ('field', 'op', 'value')
    query = QueryInstance(lambda value: True, hashval)

    assert hash(query) == hash(hashval)

def test_hash_distinguishes_queries_with_different_hashvals():
    """Different hashvals lead to different query hashes."""
    q1 = QueryInstance(lambda value: True, ('a',))
    q2 = QueryInstance(lambda value: True, ('b',))

    assert hash(q1) != hash(q2)

def test_repr_includes_hashval():
    """__repr__ embeds the hashval via standard str formatting."""
    query = QueryInstance(lambda value: True, ('alpha', 'beta'))

    assert repr(query) == "QueryImpl('alpha', 'beta')"

def test_repr_with_none_hashval():
    """__repr__ renders 'QueryImplNone' when hashval is None."""
    query = QueryInstance(lambda value: True, None)

    assert repr(query) == 'QueryImplNone'

def test_equality_when_hashvals_match():
    """Two QueryInstances with the same hashval are equal, even if test functions differ."""
    q1 = QueryInstance(lambda value: True, ('same',))
    q2 = QueryInstance(lambda value: False, ('same',))

    assert q1 == q2
    assert not (q1 != q2)

def test_inequality_when_hashvals_differ():
    """Two QueryInstances with different hashvals are not equal."""
    q1 = QueryInstance(lambda value: True, ('a',))
    q2 = QueryInstance(lambda value: True, ('b',))

    assert q1 != q2
    assert not (q1 == q2)

def test_equal_queries_have_equal_hashes():
    """Equal QueryInstances must have equal hashes (Python data model contract)."""
    q1 = QueryInstance(lambda value: True, ('same',))
    q2 = QueryInstance(lambda value: False, ('same',))

    assert q1 == q2
    assert hash(q1) == hash(q2)

def test_inequality_against_non_query_instance():
    """Comparing a QueryInstance with a non-QueryInstance returns False for equality."""
    q = QueryInstance(lambda value: True, ('x',))

    assert (q == 'string') is False
    assert (q == 42) is False
    assert (q == None) is False  # noqa: E711
    assert (q == ('x',)) is False
    assert (q == object()) is False

def test_and_evaluates_logical_conjunction_of_operands():
    """__and__ evaluates both operands and returns their logical AND."""
    q1 = QueryInstance(lambda v: v.get('a') == 1, ('a', '==', 1))
    q2 = QueryInstance(lambda v: v.get('b') == 2, ('b', '==', 2))
    combined = q1 & q2

    assert combined({'a': 1, 'b': 2}) is True
    assert combined({'a': 1, 'b': 99}) is False
    assert combined({'a': 99, 'b': 2}) is False
    assert combined({'a': 99, 'b': 99}) is False

def test_and_result_cacheable_when_both_operands_cacheable():
    """__and__ is cacheable iff both operands are cacheable."""
    q1 = QueryInstance(lambda v: True, ('a',))
    q2 = QueryInstance(lambda v: True, ('b',))

    assert (q1 & q2).is_cacheable() is True
    assert (q2 & q1).is_cacheable() is True

def test_and_result_not_cacheable_when_either_operand_not_cacheable():
    """__and__ is non-cacheable when at least one operand is non-cacheable."""
    cacheable = QueryInstance(lambda v: True, ('a',))
    not_cacheable = QueryInstance(lambda v: True, None)

    assert (cacheable & not_cacheable).is_cacheable() is False
    assert (not_cacheable & cacheable).is_cacheable() is False
    assert (not_cacheable & not_cacheable).is_cacheable() is False

def test_and_hash_is_commutative():
    """__and__ hashes the same regardless of operand order (uses frozenset)."""
    q1 = QueryInstance(lambda v: True, ('a',))
    q2 = QueryInstance(lambda v: True, ('b',))

    assert hash(q1 & q2) == hash(q2 & q1)

def test_or_evaluates_logical_disjunction_of_operands():
    """__or__ evaluates both operands and returns their logical OR."""
    q1 = QueryInstance(lambda v: v.get('a') == 1, ('a', '==', 1))
    q2 = QueryInstance(lambda v: v.get('b') == 2, ('b', '==', 2))
    combined = q1 | q2

    assert combined({'a': 1, 'b': 2}) is True
    assert combined({'a': 1, 'b': 99}) is True
    assert combined({'a': 99, 'b': 2}) is True
    assert combined({'a': 99, 'b': 99}) is False

def test_or_result_cacheable_when_both_operands_cacheable():
    """__or__ is cacheable iff both operands are cacheable."""
    q1 = QueryInstance(lambda v: True, ('a',))
    q2 = QueryInstance(lambda v: True, ('b',))

    assert (q1 | q2).is_cacheable() is True
    assert (q2 | q1).is_cacheable() is True

def test_or_result_not_cacheable_when_either_operand_not_cacheable():
    """__or__ is non-cacheable when at least one operand is non-cacheable."""
    cacheable = QueryInstance(lambda v: True, ('a',))
    not_cacheable = QueryInstance(lambda v: True, None)

    assert (cacheable | not_cacheable).is_cacheable() is False
    assert (not_cacheable | cacheable).is_cacheable() is False
    assert (not_cacheable | not_cacheable).is_cacheable() is False

def test_or_hash_is_commutative():
    """__or__ hashes the same regardless of operand order (uses frozenset)."""
    q1 = QueryInstance(lambda v: True, ('a',))
    q2 = QueryInstance(lambda v: True, ('b',))

    assert hash(q1 | q2) == hash(q2 | q1)

def test_invert_negates_test_result():
    """__invert__ returns a query that negates the original test function's result."""
    query = QueryInstance(lambda v: v.get('x') == 1, ('x', '==', 1))
    inverted = ~query

    assert inverted({'x': 1}) is False
    assert inverted({'x': 2}) is True

def test_invert_preserves_cacheability_when_original_cacheable():
    """__invert__ stays cacheable when applied to a cacheable query."""
    query = QueryInstance(lambda v: True, ('a',))

    assert (~query).is_cacheable() is True

def test_invert_not_cacheable_when_original_not_cacheable():
    """__invert__ produces a non-cacheable result for a non-cacheable original."""
    query = QueryInstance(lambda v: True, None)

    assert (~query).is_cacheable() is False

def test_double_invert_restores_logical_behavior():
    """A double invert produces a query with the same logical behaviour as the original."""
    query = QueryInstance(lambda v: v.get('x') == 1, ('x', '==', 1))
    double_inverted = ~~query

    assert double_inverted({'x': 1}) is True
    assert double_inverted({'x': 2}) is False

def test_double_invert_does_not_restore_equality():
    """A double-inverted query is logically equivalent but not equal (hash differs)."""
    query = QueryInstance(lambda v: True, ('a',))
    double_inverted = ~~query

    # Equality is hash-based, so wrapping twice changes the hashval
    # even though the test function is logically the same.
    assert query != double_inverted

def test_query_instance_can_be_used_as_dict_key():
    """Hashable QueryInstances can serve as dictionary keys for caching."""
    q1 = QueryInstance(lambda v: True, ('k1',))
    q2 = QueryInstance(lambda v: True, ('k2',))

    cache = {q1: 'result-1', q2: 'result-2'}

    assert cache[q1] == 'result-1'
    assert cache[q2] == 'result-2'
