import pytest
from typing import Mapping
from tinydb.queries import QueryLike, QueryInstance, Query, where

import pytest

from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_querylike_protocol_is_importable():
    """QueryLike is importable from tinydb.queries."""
    assert QueryLike is not None


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_querylike_protocol_declares_call_and_hash():
    """QueryLike protocol declares __call__ and __hash__ attributes."""
    # Protocols in Python expose the methods they declare
    assert hasattr(QueryLike, '__call__')
    assert hasattr(QueryLike, '__hash__')


from typing import Mapping

from tinydb.queries import QueryLike, QueryInstance, Query, where


def _truthy(v):
    return True


def _falsy(v):
    return False


def test_query_instance_callable_with_mapping_returns_true():
    """QueryInstance is callable on a Mapping and can return True."""
    qi = QueryInstance(_truthy, None)
    result = qi({'name': 'alice'})
    assert result is True


from tinydb.queries import QueryLike, QueryInstance, Query, where


def _predicate_match(value):
    return value.get('name') == 'alice'


def test_query_instance_callable_with_mapping_returns_false():
    """QueryInstance is callable on a Mapping and can return False."""
    qi = QueryInstance(_predicate_match, None)
    # Different value -> predicate returns False
    assert qi({'name': 'bob'}) is False


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_query_instance_always_returns_bool_type():
    """QueryInstance.__call__ result is always a bool instance."""
    qi = QueryInstance(lambda v: True, None)
    assert isinstance(qi({'k': 1}), bool)
    qi2 = QueryInstance(lambda v: False, None)
    assert isinstance(qi2({'k': 1}), bool)


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_query_instance_is_hashable():
    """A QueryInstance is hashable, returning an int from hash()."""
    qi = QueryInstance(lambda v: True, None)
    h = hash(qi)
    assert isinstance(h, int)


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_query_instance_hash_is_stable_across_calls():
    """The same QueryInstance hashes to the same int repeatedly."""
    qi = QueryInstance(lambda v: True, None)
    assert hash(qi) == hash(qi)
    assert hash(qi) == hash(qi)  # noqa: testing repetition


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_query_instances_share_hash_for_equal_hashvals():
    """QueryInstances with the same hashval produce the same hash."""
    hashval = ('name', '==', 'alice')

    def same_predicate(v):
        return v.get('name') == 'alice'

    qi1 = QueryInstance(same_predicate, hashval)
    qi2 = QueryInstance(same_predicate, hashval)
    assert hash(qi1) == hash(qi2)


def test_query_instance_is_cacheable_default_true():
    """A QueryInstance with a hashval is cacheable by default."""
    qi = QueryInstance(lambda v: True, ('key',))
    assert qi.is_cacheable() is True

def test_where_query_is_callable_with_mapping():
    """A Query built via where() is callable on a Mapping and returns a bool."""
    q = where('name') == 'alice'
    assert isinstance(q({'name': 'alice'}), bool)
    assert q({'name': 'alice'}) is True
    assert q({'name': 'bob'}) is False

from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_where_query_hash_is_stable():
    """A Query built via where() has a stable hash."""
    q = where('name')
    assert hash(q) == hash(q)
    assert isinstance(hash(q), int)


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_where_query_matching_and_non_matching():
    """Query distinguishes matching vs. non-matching Mappings."""
    q = where('name') == 'alice'
    assert q({'name': 'alice'}) is True
    assert q({'name': 'bob'}) is False


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_empty_mapping_query_returns_bool():
    """An empty Mapping is accepted and produces a bool."""
    qi = QueryInstance(lambda v: 'k' in v, None)
    result = qi({})
    assert isinstance(result, bool)
    assert result is False


def test_query_test_callback_works_as_querylike():
    """A callback-based QueryInstance satisfies the QueryLike protocol."""
    predicate = lambda v: v.get('x') == 1
    qi = QueryInstance(predicate, ('callback_query',))

    # Callable, returning bool
    assert callable(qi)
    assert qi({'x': 1}) is True
    assert qi({'x': 2}) is False
    # Hashable with a stable hash
    assert isinstance(hash(qi), int)
    assert hash(qi) == hash(qi)

from typing import Mapping

from tinydb.queries import QueryLike, QueryInstance, Query, where


class _FakeQuery:
    """A minimal stand-in implementing the QueryLike contract by hand."""

    def __call__(self, value: Mapping) -> bool:
        return 'k' in value

    def __hash__(self) -> int:
        return 123


def test_custom_class_implements_querylike_protocol():
    """A duck-typed class satisfies the QueryLike contract."""
    fq = _FakeQuery()
    # Callable contract
    assert fq({'k': 1}) is True
    assert fq({'other': 1}) is False
    # Hash contract
    assert isinstance(hash(fq), int)
    # Stable hash
    assert hash(fq) == hash(fq)


from typing import Mapping

from tinydb.queries import QueryLike, QueryInstance, Query, where


class _CustomHashQuery:
    """QueryLike whose hash depends on a stored target value."""

    def __init__(self, target):
        self._target = target

    def __call__(self, value: Mapping) -> bool:
        return value.get('key') == self._target

    def __hash__(self) -> int:
        return hash(self._target)


def test_custom_class_with_custom_hash_logic():
    """A QueryLike may encode state into its hash."""
    q1 = _CustomHashQuery('hello')
    q2 = _CustomHashQuery('hello')
    # Same state -> same hash
    assert hash(q1) == hash(q2)
    # Calling contract works
    assert q1({'key': 'hello'}) is True
    assert q1({'key': 'world'}) is False


from typing import Mapping

from tinydb.queries import QueryLike, QueryInstance, Query, where


class _RemoteLookupQuery:
    """A QueryLike simulating a remote lookup that should not be cached."""

    def __call__(self, value: Mapping) -> bool:
        # Pretend a remote lookup happened; the result is a bool either way
        return bool(value)

    def __hash__(self) -> int:
        return 999

    def is_cacheable(self) -> bool:
        return False


def test_non_cacheable_querylike_opt_out():
    """A QueryLike can mark itself non-cacheable via is_cacheable()."""
    q = _RemoteLookupQuery()
    # Opt out of caching
    assert q.is_cacheable() is False
    # Still satisfies the rest of the protocol
    assert isinstance(q({}), bool)
    assert isinstance(hash(q), int)


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_class_missing_call_fails_to_be_querylike():
    """A hashable but non-callable object fails the QueryLike contract."""

    class _HashOnly:
        def __hash__(self) -> int:
            return 7

    obj = _HashOnly()
    # Cannot be invoked with a Mapping; this fails the protocol contract
    with pytest.raises(TypeError):
        obj({'k': 1})


def test_unhashable_class_fails_to_be_querylike():
    """A callable but explicitly unhashable object fails the QueryLike contract."""

    class _Unhashable:
        __hash__ = None
        def __call__(self, value):
            return True

    obj = _Unhashable()
    # Callable works fine
    assert obj({'k': 1}) is True
    # But the object is explicitly unhashable: QueryLike requires a __hash__
    # that returns an int, so hash() must raise.
    with pytest.raises(TypeError):
        hash(obj)

from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_query_instance_call_does_not_raise_on_simple_predicate():
    """QueryInstance.__call__ completes without errors for well-behaved predicates."""
    qi = QueryInstance(lambda v: v.get('a') == 1, None)
    # No exception expected
    result = qi({'a': 1, 'b': 2})
    assert isinstance(result, bool)


from tinydb.queries import QueryLike, QueryInstance, Query, where


def test_query_instance_can_be_used_in_set_for_caching():
    """QueryInstances are usable in a set / as dict keys."""
    hashval = ('name', '==', 'alice')

    def pred(v):
        return v.get('name') == 'alice'

    qi1 = QueryInstance(pred, hashval)
    qi2 = QueryInstance(pred, hashval)

    cache = set()
    cache.add(qi1)
    cache.add(qi2)
    # Both instances should map to the same cache slot
    assert len(cache) == 1

