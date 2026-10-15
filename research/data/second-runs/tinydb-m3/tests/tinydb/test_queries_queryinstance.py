import pytest
from tinydb.queries import QueryInstance

def test_call_invokes_test_function_with_value():
    """Verify __call__ passes the input value to the test function and returns its result."""
    received = {}

    def capture(v):
        received['value'] = v
        return v.get('a') == 1

    q = QueryInstance(capture, 'h')
    sample = {'a': 1, 'b': 'hello'}
    result = q(sample)
    assert received['value'] is sample
    assert result is True


def test_call_returns_true_when_test_function_returns_true():
    """Verify __call__ returns True when the underlying test function returns True."""
    q = QueryInstance(lambda v: v.get('a') == 1, 'h')
    assert q({'a': 1}) is True


def test_call_returns_false_when_test_function_returns_false():
    """Verify __call__ returns False when the underlying test function returns False."""
    q = QueryInstance(lambda v: v.get('a') == 1, 'h')
    assert q({'a': 2}) is False


def test_call_with_empty_mapping():
    """Verify __call__ works with an empty mapping (no attribute errors)."""
    q = QueryInstance(lambda v: bool(v), 'h')
    assert q({}) is False
    assert q({'x': 1}) is True


def test_is_cacheable_returns_true_when_hashval_is_not_none():
    """Verify is_cacheable returns True when hashval is provided (not None)."""
    q = QueryInstance(lambda v: True, 'some_hash')
    assert q.is_cacheable() is True


def test_is_cacheable_returns_false_when_hashval_is_none():
    """Verify is_cacheable returns False when hashval is None (uncacheable)."""
    q = QueryInstance(lambda v: True, None)
    assert q.is_cacheable() is False


def test_hash_returns_hash_of_hashval():
    """Verify __hash__ returns the hash of the stored hashval."""
    q = QueryInstance(lambda v: True, 'foo')
    assert hash(q) == hash('foo')


def test_hash_is_stable_for_same_instance():
    """Verify __hash__ returns the same value on repeated calls for the same instance."""
    q = QueryInstance(lambda v: True, ('a', 'b'))
    assert hash(q) == hash(q)


def test_hash_for_none_hashval_returns_hash_of_none():
    """Verify __hash__ returns hash(None) when hashval is None (still produces an int)."""
    q = QueryInstance(lambda v: True, None)
    assert hash(q) == hash(None)


def test_repr_includes_hashval():
    """Verify __repr__ formats the hashval into the 'QueryImpl{hashval}' string."""
    q = QueryInstance(lambda v: True, ('a', 'b'))
    assert repr(q) == "QueryImpl('a', 'b')"


def test_repr_with_none_hashval():
    """Verify __repr__ formats None hashval as 'QueryImplNone'."""
    q = QueryInstance(lambda v: True, None)
    assert repr(q) == 'QueryImplNone'


def test_equal_when_same_hashval():
    """Verify two QueryInstances with equal hashvals are equal, regardless of test function."""
    q1 = QueryInstance(lambda v: v.get('a') == 1, 'shared')
    q2 = QueryInstance(lambda v: v.get('b') == 2, 'shared')
    assert q1 == q2


def test_not_equal_when_different_hashval():
    """Verify two QueryInstances with different hashvals are not equal."""
    q1 = QueryInstance(lambda v: True, 'hash1')
    q2 = QueryInstance(lambda v: True, 'hash2')
    assert q1 != q2


def test_equal_when_both_hashval_are_none():
    """Verify two QueryInstances with None hashvals compare as equal (None == None)."""
    q1 = QueryInstance(lambda v: v.get('a') == 1, None)
    q2 = QueryInstance(lambda v: v.get('b') == 2, None)
    assert q1 == q2


def test_not_equal_to_string_with_same_content():
    """Verify a QueryInstance is not equal to a string even when their values match."""
    q = QueryInstance(lambda v: True, 'some_hash')
    assert (q == 'some_hash') is False


def test_not_equal_to_none():
    """Verify a QueryInstance is not equal to None (non-QueryInstance)."""
    q = QueryInstance(lambda v: True, 'h')
    assert (q == None) is False  # noqa: E711 - intentional non-QueryInstance check


def test_not_equal_to_arbitrary_object():
    """Verify a QueryInstance is not equal to an arbitrary object (non-QueryInstance)."""
    q = QueryInstance(lambda v: True, 'h')
    assert (q == object()) is False
    assert (q == 42) is False


def test_and_returns_a_new_query_instance():
    """Verify __and__ returns a new QueryInstance, not a non-QueryInstance type."""
    q1 = QueryInstance(lambda v: True, 'a')
    q2 = QueryInstance(lambda v: True, 'b')
    combined = q1 & q2
    assert isinstance(combined, QueryInstance)


def test_and_logically_combines_operands():
    """Verify __and__ produces a query that is True only when both operands are True."""
    q1 = QueryInstance(lambda v: v.get('a') == 1, 'a')
    q2 = QueryInstance(lambda v: v.get('b') == 2, 'b')

    combined = q1 & q2
    assert combined({'a': 1, 'b': 2}) is True
    assert combined({'a': 1, 'b': 3}) is False
    assert combined({'a': 0, 'b': 2}) is False
    assert combined({'a': 0, 'b': 3}) is False


def test_and_invocations_of_both_operands():
    """Verify the AND query actually invokes both underlying test functions."""
    called = {'q1': 0, 'q2': 0}

    def t1(v):
        called['q1'] += 1
        return v.get('a') == 1

    def t2(v):
        called['q2'] += 1
        return v.get('b') == 2

    combined = QueryInstance(t1, 'a') & QueryInstance(t2, 'b')
    combined({'a': 1, 'b': 2})

    assert called['q1'] == 1
    assert called['q2'] == 1


def test_and_with_both_cacheable_is_cacheable_and_has_combined_hash():
    """When both operands are cacheable, the AND result is cacheable with combined hash."""
    q1 = QueryInstance(lambda v: True, 'a')
    q2 = QueryInstance(lambda v: True, 'b')

    combined = q1 & q2
    assert combined.is_cacheable() is True
    assert hash(combined) == hash(('and', frozenset(['a', 'b'])))


def test_and_with_one_uncacheable_operand_is_not_cacheable():
    """When either operand has None hashval, the AND result is not cacheable."""
    q_cacheable = QueryInstance(lambda v: True, 'a')
    q_uncacheable = QueryInstance(lambda v: True, None)

    combined = q_cacheable & q_uncacheable
    assert combined.is_cacheable() is False
    # The combined query should still behave correctly even when uncacheable
    assert combined({'x': 1}) is True


def test_and_with_both_uncacheable_is_not_cacheable():
    """When both operands are uncacheable, the AND result is not cacheable."""
    q1 = QueryInstance(lambda v: True, None)
    q2 = QueryInstance(lambda v: True, None)

    combined = q1 & q2
    assert combined.is_cacheable() is False


def test_and_short_circuits_when_left_operand_is_false():
    """Verify AND short-circuits and does not invoke the right operand when the left is False."""
    left_called = {'count': 0}
    right_called = {'count': 0}

    def left(v):
        left_called['count'] += 1
        return False

    def right(v):
        right_called['count'] += 1
        return True

    combined = QueryInstance(left, 'a') & QueryInstance(right, 'b')
    result = combined({'x': 1})

    assert result is False
    assert left_called['count'] == 1
    assert right_called['count'] == 0


def test_or_returns_a_new_query_instance():
    """Verify __or__ returns a new QueryInstance, not a non-QueryInstance type."""
    q1 = QueryInstance(lambda v: True, 'a')
    q2 = QueryInstance(lambda v: False, 'b')
    combined = q1 | q2
    assert isinstance(combined, QueryInstance)


def test_or_logically_combines_operands():
    """Verify __or__ produces a query that is True when at least one operand is True."""
    q1 = QueryInstance(lambda v: v.get('a') == 1, 'a')
    q2 = QueryInstance(lambda v: v.get('b') == 2, 'b')

    combined = q1 | q2
    assert combined({'a': 1, 'b': 2}) is True
    assert combined({'a': 1, 'b': 3}) is True
    assert combined({'a': 0, 'b': 2}) is True
    assert combined({'a': 0, 'b': 3}) is False


def test_or_with_both_cacheable_is_cacheable_and_has_combined_hash():
    """When both operands are cacheable, the OR result is cacheable with combined hash."""
    q1 = QueryInstance(lambda v: True, 'a')
    q2 = QueryInstance(lambda v: True, 'b')

    combined = q1 | q2
    assert combined.is_cacheable() is True
    assert hash(combined) == hash(('or', frozenset(['a', 'b'])))


def test_or_with_one_uncacheable_operand_is_not_cacheable():
    """When either operand has None hashval, the OR result is not cacheable."""
    q_cacheable = QueryInstance(lambda v: True, 'a')
    q_uncacheable = QueryInstance(lambda v: True, None)

    combined = q_cacheable | q_uncacheable
    assert combined.is_cacheable() is False


def test_or_with_both_uncacheable_is_not_cacheable():
    """When both operands are uncacheable, the OR result is not cacheable."""
    q1 = QueryInstance(lambda v: True, None)
    q2 = QueryInstance(lambda v: True, None)

    combined = q1 | q2
    assert combined.is_cacheable() is False


def test_or_short_circuits_when_left_operand_is_true():
    """Verify OR short-circuits and does not invoke the right operand when the left is True."""
    left_called = {'count': 0}
    right_called = {'count': 0}

    def left(v):
        left_called['count'] += 1
        return True

    def right(v):
        right_called['count'] += 1
        return False

    combined = QueryInstance(left, 'a') | QueryInstance(right, 'b')
    result = combined({'x': 1})

    assert result is True
    assert left_called['count'] == 1
    assert right_called['count'] == 0


def test_invert_returns_a_new_query_instance():
    """Verify __invert__ returns a new QueryInstance, not a non-QueryInstance type."""
    q = QueryInstance(lambda v: True, 'a')
    inverted = ~q
    assert isinstance(inverted, QueryInstance)


def test_invert_negates_the_operand_result():
    """Verify __invert__ produces a query whose result is the negation of the operand's."""
    q = QueryInstance(lambda v: v.get('a') == 1, 'a')
    inverted = ~q

    assert inverted({'a': 1}) is False
    assert inverted({'a': 2}) is True


def test_invert_with_cacheable_operand_is_cacheable_with_not_hash():
    """Verify inverted query is cacheable and its hash wraps the original with a 'not' marker."""
    q = QueryInstance(lambda v: True, 'a')
    inverted = ~q

    assert inverted.is_cacheable() is True
    assert hash(inverted) == hash(('not', 'a'))


def test_invert_with_uncacheable_operand_is_not_cacheable():
    """Verify inverted query is not cacheable when the operand is not cacheable."""
    q = QueryInstance(lambda v: True, None)
    inverted = ~q

    assert inverted.is_cacheable() is False
    # Even when uncacheable, the inversion should still invert the logic
    assert inverted({'x': 1}) is False


def test_and_is_commutative_by_hash_and_equality():
    """Verify (a & b) == (b & a) since frozenset-based hash is order-insensitive."""
    q1 = QueryInstance(lambda v: True, 'x')
    q2 = QueryInstance(lambda v: True, 'y')

    assert hash(q1 & q2) == hash(q2 & q1)
    assert (q1 & q2) == (q2 & q1)


def test_or_is_commutative_by_hash_and_equality():
    """Verify (a | b) == (b | a) since frozenset-based hash is order-insensitive."""
    q1 = QueryInstance(lambda v: True, 'x')
    q2 = QueryInstance(lambda v: True, 'y')

    assert hash(q1 | q2) == hash(q2 & q1) or True  # placeholder; replaced below
    assert hash(q1 | q2) == hash(q2 | q1)
    assert (q1 | q2) == (q2 | q1)


def test_cacheable_query_usable_as_dict_key():
    """Verify cacheable queries can be used as dictionary keys (cache use case).

    Two QueryInstances with the same hashval are equal, so they look up the
    same entry in a dict, just like the TinyDB query cache relies on.
    """
    q_a1 = QueryInstance(lambda v: True, 'shared_hash')
    q_a2 = QueryInstance(lambda v: False, 'shared_hash')  # different body, same hash
    q_b = QueryInstance(lambda v: True, 'other_hash')

    cache = {q_a1: 'cached_for_a', q_b: 'cached_for_b'}

    assert cache[q_a2] == 'cached_for_a'
    assert cache[q_b] == 'cached_for_b'
    assert len(cache) == 2


def test_cacheable_query_with_complex_hashval_in_dict():
    """Verify queries with tuple hashval (typical for real Query methods) work in dicts."""
    q1 = QueryInstance(lambda v: True, ('foo', 'bar'))
    q2 = QueryInstance(lambda v: False, ('foo', 'baz'))

    cache = {q1: 'v1', q2: 'v2'}

    assert cache[QueryInstance(lambda v: True, ('foo', 'bar'))] == 'v1'
    assert cache[QueryInstance(lambda v: False, ('foo', 'baz'))] == 'v2'
