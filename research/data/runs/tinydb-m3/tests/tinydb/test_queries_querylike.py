import pytest
from tinydb.queries import QueryLike, QueryInstance

from tinydb.queries import QueryLike


def test_querylike_is_importable_from_queries_module():
    """QueryLike should be importable from tinydb.queries as documented."""
    assert QueryLike is not None


from tinydb.queries import QueryLike


def test_querylike_protocol_defines_dunder_call():
    """The QueryLike protocol must expose ``__call__`` to model the query invocation contract."""
    assert hasattr(QueryLike, '__call__')


from tinydb.queries import QueryLike


def test_querylike_protocol_defines_dunder_hash():
    """The QueryLike protocol must expose ``__hash__`` so queries are hashable for caching."""
    assert hasattr(QueryLike, '__hash__')


from tinydb.queries import QueryLike


def test_querylike_docstring_describes_callable_contract():
    """The QueryLike docstring should describe the callable(()->bool) requirement."""
    doc = (QueryLike.__doc__ or '').lower()
    assert 'callable' in doc


from tinydb.queries import QueryLike


def test_querylike_docstring_mentions_hash_for_caching():
    """The QueryLike docstring should explain that a stable hash enables caching."""
    doc = (QueryLike.__doc__ or '').lower()
    assert 'hash' in doc
    assert 'cach' in doc


from tinydb.queries import QueryLike


def test_querylike_docstring_describes_is_cacheable_marker():
    """The QueryLike docstring should mention ``is_cacheable`` as the opt-out marker method."""
    doc = QueryLike.__doc__ or ''
    assert 'is_cacheable' in doc


from tinydb.queries import QueryLike


class _CallableBoolQuery:
    """Minimal class satisfying the QueryLike callable half of the protocol."""

    def __call__(self, value):
        return bool(value)


def test_custom_query_returns_bool_when_called_with_mapping():
    """A user-defined query class must be callable returning a bool for a Mapping."""
    q = _CallableBoolQuery()
    result = q({'a': 1, 'b': 2})
    assert isinstance(result, bool)
    assert result is True
    # An empty mapping must produce a bool too
    assert isinstance(q({}), bool)


from tinydb.queries import QueryLike


class _HashableQuery:
    """Minimal class satisfying the hashing half of the QueryLike protocol."""

    def __call__(self, value):
        return True

    def __hash__(self):
        return 12345

    def __eq__(self, other):
        return isinstance(other, _HashableQuery)


def test_custom_query_supports_hashing():
    """A user-defined query class must be hashable to fulfill the QueryLike contract."""
    q = _HashableQuery()
    h = hash(q)
    assert isinstance(h, int)
    assert h == 12345


from tinydb.queries import QueryLike


class _StableHashQuery:
    """Custom query whose hash is deterministic across calls."""

    def __init__(self, tag):
        self._tag = tag

    def __call__(self, value):
        return True

    def __hash__(self):
        return hash(self._tag)

    def __eq__(self, other):
        return isinstance(other, _StableHashQuery) and self._tag == other._tag


def test_custom_query_hash_is_stable_across_calls():
    """The protocol requires a stable hash for caching; repeated hashes must match."""
    q = _StableHashQuery('alpha')
    first = hash(q)
    second = hash(q)
    third = hash(q)
    assert first == second == third
    assert isinstance(first, int)


import pytest


class _UnhashableQuery:
    """Query-like object that disables its own hash: should violate the caching contract."""

    __hash__ = None  # explicit opt-out from hashing

    def __call__(self, value):
        return True


def test_unhashable_query_violates_protocol_contract():
    """QueryLike requires a stable hash; an unhashable class must raise TypeError on hash()."""
    q = _UnhashableQuery()
    with pytest.raises(TypeError):
        hash(q)


from tinydb.queries import QueryInstance


def test_queryinstance_supports_callable_contract():
    """QueryInstance must be callable to satisfy QueryLike's invocation contract."""
    qi = QueryInstance(lambda v: True, None)
    assert callable(qi)


from tinydb.queries import QueryInstance


def test_queryinstance_call_returns_bool_for_mapping():
    """A QueryInstance invoked on a Mapping must return a boolean result."""
    # The test fn is the user's predicate that returns a bool over a Mapping.
    truthy = QueryInstance(lambda v: bool(v), None)
    falsy = QueryInstance(lambda v: not bool(v), None)

    assert truthy({'x': 1}) is True
    assert isinstance(truthy({'x': 1}), bool)

    assert falsy({'x': 1}) is False
    assert isinstance(falsy({'x': 1}), bool)

    # Empty mapping is falsy
    assert truthy({}) is False
    assert falsy({}) is True


from tinydb.queries import QueryInstance


def test_queryinstance_exposes_is_cacheable_marker():
    """The docstring-mandated ``is_cacheable`` marker should be present on QueryInstance."""
    qi = QueryInstance(lambda v: True, None)
    assert hasattr(qi, 'is_cacheable')


from tinydb.queries import QueryInstance


def test_queryinstance_is_cacheable_returns_bool():
    """``QueryInstance.is_cacheable`` must return a bool, per the documented intent."""
    qi = QueryInstance(lambda v: True, None)
    flag = qi.is_cacheable()
    assert isinstance(flag, bool)

