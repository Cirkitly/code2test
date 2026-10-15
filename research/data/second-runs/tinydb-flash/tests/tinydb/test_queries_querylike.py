import pytest
from typing import Any, Callable, Mapping, Optional, Tuple, Protocol, get_type_hints
from tinydb.queries import Query, QueryInstance, QueryLike, where
from tinydb.utils import freeze

@pytest.fixture
def document():
    """A sample TinyDB document used to evaluate queries."""
    return {'name': 'John', 'age': 30, 'tags': ['a', 'b']}

@pytest.fixture
def predicate_query():
    """A user-defined object that structurally satisfies the QueryLike protocol."""
    return PredicateQuery(lambda value: value.get('flag') is True, ('custom',))

class PredicateQuery:
    """A user-defined object that structurally satisfies ``QueryLike``."""

    def __init__(self, test: Callable[[Mapping], bool], hashval: Optional[Tuple] = None):
        self._test = test
        self._hash = hashval

    def __call__(self, value: Mapping) -> bool:
        return self._test(value)

    def __hash__(self) -> int:
        return hash(self._hash)

    def is_cacheable(self) -> bool:
        return self._hash is not None


class UnhashablePredicate:
    """A callable that deliberately has no stable hash (defines ``__eq__``)."""

    def __call__(self, value: Mapping) -> bool:
        return bool(value)

    def __eq__(self, other: Any) -> bool:
        return self is other


def evaluate_query(query: QueryLike, value: Mapping) -> bool:
    """Evaluate any QueryLike against a Mapping."""
    return query(value)

def test_query_like_is_a_typing_protocol():
    """QueryLike must be a ``typing.Protocol`` class (it exists for static typing)."""
    assert isinstance(QueryLike, type)
    assert issubclass(QueryLike, Protocol)
    assert QueryLike.__name__ == 'QueryLike'

def test_query_like_declares_call_and_hash_members():
    """
    The protocol requires exactly two members: being callable and having a
    stable hash. ``is_cacheable`` is opt-in, so the protocol itself does not
    declare it.
    """
    assert callable(QueryLike.__call__)
    assert callable(QueryLike.__hash__)
    assert hasattr(QueryLike, 'is_cacheable') is False

def test_query_like_call_signature_accepts_mapping_returns_bool():
    """A query-like must accept a Mapping and return a bool."""
    hints = get_type_hints(QueryLike.__call__)
    assert hints['value'] is Mapping
    assert hints['return'] is bool

def test_query_like_hash_signature_returns_int():
    """The stable hash required by the protocol is an int."""
    hints = get_type_hints(QueryLike.__hash__)
    assert hints['return'] is int

def test_query_like_cannot_be_instantiated():
    """Protocols are not instantiable -- QueryLike is only a structural type."""
    with pytest.raises(TypeError):
        QueryLike()

def test_query_like_is_not_runtime_checkable():
    """
    The protocol is not decorated with ``@runtime_checkable``, so runtime
    checks must be rejected instead of silently returning False.
    """
    query = QueryInstance(lambda value: True, ('hashval',))

    with pytest.raises(TypeError):
        isinstance(query, QueryLike)

    with pytest.raises(TypeError):
        issubclass(QueryInstance, QueryLike)

def test_query_instance_satisfies_query_like_contract():
    """
    Happy path: a QueryInstance is the concrete implementation of QueryLike --
    it is callable, hashable and can report cacheability.
    """
    query = QueryInstance(lambda value: True, ('hashval',))

    assert callable(query.__call__)
    assert isinstance(hash(query), int)
    assert callable(query.is_cacheable)

def test_query_instance_is_called_with_mapping_and_returns_bool():
    """Calling a query-like passes the Mapping to the test function and returns a bool."""
    query = QueryInstance(lambda value: value['a'] == 1, ('t',))

    assert query({'a': 1}) is True
    assert query({'a': 2}) is False
    assert isinstance(query({'a': 1}), bool)

def test_query_instance_hash_is_stable_across_calls():
    """The hash must be stable, so repeated hashing yields the same int."""
    query = QueryInstance(lambda value: True, ('hashval',))

    first = hash(query)
    second = hash(query)

    assert isinstance(first, int)
    assert second == first

def test_query_instance_hash_depends_only_on_hash_value():
    """
    The hash is derived from the hash value only: two queries built with the
    same hash value hash equally, different hash values hash differently.
    """
    q1 = QueryInstance(lambda value: True, ('a', 1))
    q2 = QueryInstance(lambda value: False, ('a', 1))
    q3 = QueryInstance(lambda value: True, ('a', 2))

    assert hash(q1) == hash(q2)
    assert hash(q1) != hash(q3)

def test_distinct_queries_with_same_hash_are_not_equal():
    """
    Two distinct query objects that share a hash value are separate objects,
    but they compare equal and hash equally: QueryInstance defines equality
    (and thus hashing) purely in terms of its hash value.
    """
    q1 = QueryInstance(lambda value: True, ('a', 1))
    q2 = QueryInstance(lambda value: True, ('a', 1))

    assert q1 is not q2
    assert q1 == q2
    assert hash(q1) == hash(q2)

def test_query_with_unhashable_hash_value_raises_on_hash():
    """
    Error condition: an unhashable hash value violates the 'stable hash'
    requirement, so hashing the query fails.
    """
    query = QueryInstance(lambda value: True, ['unhashable'])

    with pytest.raises(TypeError):
        hash(query)

def test_query_with_hash_value_is_cacheable():
    """A query constructed with a hash value may be used for caching."""
    query = QueryInstance(lambda value: True, ('a', 1))

    assert query.is_cacheable() is True

def test_query_without_hash_value_is_not_cacheable_but_usable():
    """
    A query without a hash value marks itself as non-cacheable, but it must
    still be usable as a query.
    """
    query = QueryInstance(lambda value: True, None)

    assert query.is_cacheable() is False
    assert query({}) is True

def test_user_defined_callable_and_hashable_object_satisfies_query_like(predicate_query):
    """
    Any user-defined object with __call__, __hash__ and is_cacheable
    structurally satisfies QueryLike and can be evaluated like a TinyDB query.
    """
    assert callable(predicate_query.__call__)
    assert isinstance(hash(predicate_query), int)
    assert callable(predicate_query.is_cacheable)
    assert predicate_query({'flag': True}) is True
    assert predicate_query({'flag': False}) is False

def test_callable_without_stable_hash_is_not_a_valid_query():
    """
    Error condition: an object that defines __eq__ (and therefore loses
    __hash__) is callable but has no stable hash, so it is not a valid query.
    """
    predicate = UnhashablePredicate()

    assert UnhashablePredicate.__hash__ is None
    assert predicate({'a': 1}) is True

    with pytest.raises(TypeError):
        hash(predicate)

def test_plain_callable_lacks_cacheability_marker():
    """
    A plain function can be used as a test, but it carries no cacheability
    marker -- that is opt-in via is_cacheable().
    """
    def predicate(value):
        return True

    assert predicate({}) is True
    assert hasattr(predicate, 'is_cacheable') is False

def test_query_like_can_be_used_as_type_annotation():
    """
    QueryLike can annotate a parameter, which is exactly how TinyDB supports
    the query pattern in MyPy.
    """
    assert get_type_hints(evaluate_query)['query'] is QueryLike

    query = QueryInstance(lambda value: value['n'] > 2, ('n',))

    assert evaluate_query(query, {'n': 3}) is True
    assert evaluate_query(query, {'n': 1}) is False

def test_query_can_be_used_as_a_dict_key():
    """
    A stable, int hash makes a query usable as a dictionary key, which is the
    basis for query caching.
    """
    cache = {}
    query = Query().noop()

    cache[query] = 'cached'

    assert cache[query] == 'cached'
    assert list(cache.keys()) == [query]
    assert len(cache) == 1

def test_empty_query_raises_when_evaluated():
    """
    Error condition: an empty Query object is not a usable query -- calling it
    raises instead of returning a bogus boolean.
    """
    query = Query()

    assert isinstance(hash(query), int)

    with pytest.raises(RuntimeError):
        query({})

def test_frozen_documents_are_hashable_query_hash_values():
    """
    Hash values may embed frozen (immutable, hashable) data so that the
    query hash stays stable and computable.
    """
    frozen = freeze({'a': [1, 2]})

    assert isinstance(hash(frozen), int)
    assert hash(frozen) == hash(freeze({'a': [1, 2]}))

    query = QueryInstance(lambda value: True, (frozen,))
    other = QueryInstance(lambda value: False, (freeze({'a': [1, 2]}),))

    assert isinstance(hash(query), int)
    assert hash(query) == hash(other)

    with pytest.raises(TypeError):
        frozen['b'] = 3

def test_where_matches_builds_a_query_like():
    """
    The query builder produces real QueryLike objects: a matches query is a
    callable, hashable QueryInstance that matches values by regex.
    """
    query = where('value').matches('^ab')

    assert isinstance(query, QueryInstance)
    assert query.is_cacheable() is True
    assert isinstance(hash(query), int)
    assert query({'value': 'abc'}) is True
    assert query({'value': 'xyz'}) is False
    assert query({}) is False

def test_where_search_builds_a_query_like():
    """A search query is a callable, hashable QueryInstance."""
    query = where('value').search('bc')

    assert isinstance(query, QueryInstance)
    assert isinstance(hash(query), int)
    assert query({'value': 'abc'}) is True
    assert query({'value': 'xyz'}) is False
    assert query({}) is False

def test_where_one_of_builds_a_query_like():
    """An one_of query is a callable, hashable QueryInstance."""
    query = where('value').one_of([1, 2, 3])

    assert isinstance(query, QueryInstance)
    assert isinstance(hash(query), int)
    assert query({'value': 2}) is True
    assert query({'value': 5}) is False
    assert query({}) is False

def test_where_exists_builds_a_query_like():
    """An exists query is a callable, hashable QueryInstance."""
    query = where('missing').exists()

    assert isinstance(query, QueryInstance)
    assert isinstance(hash(query), int)
    assert query({}) is False
    assert query({'missing': None}) is True
    assert query({'other': 1}) is False

def test_where_test_builds_a_query_like():
    """A test query built from a predicate is a callable, hashable QueryInstance."""
    query = where('value').test(lambda value: value == 1)

    assert isinstance(query, QueryInstance)
    assert isinstance(hash(query), int)
    assert query({'value': 1}) is True
    assert query({'value': 2}) is False

def test_fragment_query_is_hashable_and_matches_sub_documents():
    """
    A fragment query embeds a frozen document in its hash value, so two
    equivalent fragment queries hash equally and can be compared for caching.
    """
    q1 = where('value').fragment({'a': 1})
    q2 = where('value').fragment({'a': 1})
    q3 = where('value').fragment({'a': 2})

    assert isinstance(hash(q1), int)
    assert hash(q1) == hash(q2)
    assert hash(q1) != hash(q3)
    assert q1({'value': {'a': 1}}) is True
    assert q1({'value': {'a': 2}}) is False
    assert q1({'value': {}}) is False

def test_noop_query_matches_every_document():
    """The simplest QueryLike: a hashable query that always matches."""
    query = Query().noop()

    assert isinstance(query, QueryInstance)
    assert isinstance(hash(query), int)
    assert hash(query) == hash(query)
    assert query({}) is True
    assert query({'a': 1}) is True

def test_matches_query_against_document_fixture(document):
    """A built query evaluates to True/False against a real document."""
    query = where('name').matches('J.*')

    assert query(document) is True
    assert query({'name': 'Alice'}) is False
    assert query({'other': 1}) is False

def test_search_query_against_document_fixture(document):
    """A built search query evaluates to True/False against a real document."""
    query = where('name').search('oh')

    assert query(document) is True
    assert query({'name': 'Alice'}) is False
    assert query({'other': 1}) is False
