from typing import Mapping
import pytest
from tinydb.queries import QueryLike, Query, QueryInstance, where

def test_query_like_is_importable_and_exposes_call_and_hash_members():
    # The protocol must be importable under the documented name
    assert QueryLike is not None

    # The documented structural contract consists of callability and a stable hash
    assert '__call__' in vars(QueryLike)
    assert '__hash__' in vars(QueryLike)

def test_query_instance_callable_returns_bool_for_matching_and_non_matching_mapping():
    query = where('name') == 'John'

    matching = query({'name': 'John', 'age': 22})
    non_matching = query({'name': 'Jane', 'age': 22})

    # The protocol promises a bool, not a truthy value
    assert isinstance(matching, bool)
    assert matching is True
    assert isinstance(non_matching, bool)
    assert non_matching is False

def test_query_like_explicitly_typed_query_instance_can_be_used_as_query():
    query: QueryLike = where('name') == 'John'

    # Requirement 1 through the protocol type: call with a Mapping, get a bool
    assert query({'name': 'John'}) is True

    # Requirement 2 through the protocol type: stable hash usable for caching
    assert isinstance(query.__hash__(), int)

def test_query_has_stable_hash_usable_for_query_caching():
    first = where('name') == 'John'
    second = where('name') == 'John'

    first_hash = hash(first)
    second_hash = hash(second)

    # A stable hash: repeated calls return the same value
    assert hash(first) == first_hash

    # Equivalent queries hash equally, which is what makes caching by hash work
    assert first_hash == second_hash
    assert isinstance(first_hash, int)

def test_different_queries_have_different_hashes():
    name_query = where('name') == 'John'
    age_query = where('age') == 22

    assert isinstance(hash(name_query), int)
    assert isinstance(hash(age_query), int)

    # Distinct queries must not collide, otherwise query caching would be wrong
    assert hash(name_query) != hash(age_query)

def test_query_can_be_used_as_mapping_cache_key():
    query = where('name') == 'John'
    equivalent = where('name') == 'John'

    # Using the query as a Mapping key exercises both __hash__ and __eq__
    cache: dict = {query: ['cached result']}

    assert cache[equivalent] == ['cached result']

def test_query_works_as_membership_element_of_cacheable_collection():
    query = where('name') == 'John'

    # Queries are hashable, so they can live in hash-based collections
    assert query in {query}
    assert where('name') == 'Jane' not in {query}

def test_non_cacheable_query_still_satisfies_call_and_hash_requirements():
    # A query instance opts out of caching by passing ``None`` as its hash value.
    # (``Query().test(...)`` cannot be used for this: ``Query._generate_test``
    # raises ``ValueError('Query has no path')`` for an empty query path.)
    query = QueryInstance(lambda value: value.get('active') is True, None)

    # Optional opt-out for caching: present and reported as non-cacheable
    assert query.is_cacheable() is False

    # ...but the two mandatory protocol requirements still hold
    assert query({'active': True}) is True
    assert query({'active': False}) is False
    assert isinstance(hash(query), int)

    # Two non-cacheable queries with the same (absent) hash value hash equally
    assert hash(query) == hash(
        QueryInstance(lambda value: value.get('active') is True, None)
    )


def test_custom_callable_hashable_class_satisfies_query_like_contract():
    class RemoteUserQuery:
        def __call__(self, value: Mapping) -> bool:
            return value.get('user') == 'john'

        def __hash__(self) -> int:
            return hash(('remote-user', 'john'))

    query: QueryLike = RemoteUserQuery()

    assert query({'user': 'john'}) is True
    assert query({'user': 'jane'}) is False
    assert isinstance(query.__hash__(), int)

def test_callable_query_not_using_mapping_get_raises_attribute_error():
    class RemoteUserQuery:
        def __call__(self, value: Mapping) -> bool:
            return value.get('user') == 'john'

        def __hash__(self) -> int:
            return hash(('remote-user', 'john'))

    query: QueryLike = RemoteUserQuery()

    # The protocol requires a Mapping argument; anything else is out of contract
    with pytest.raises(AttributeError):
        query('not-a-mapping')

def test_callable_query_returning_non_boolean_fails_is_checks():
    class TruthyQuery:
        def __call__(self, value: Mapping):
            # Returns a truthy list instead of a bool -> violates the protocol
            return [value.get('user')]

        def __hash__(self) -> int:
            return hash('truthy')

    query: QueryLike = TruthyQuery()

    result = query({'user': 'john'})

    # Truthy, yet not a bool, so it does not fulfil requirement 1
    assert result
    assert isinstance(result, bool) is False

def test_non_hashable_callable_class_does_not_satisfy_query_like_contract():
    class UnhashableQuery:
        # Callable but unhashable: __hash__ is set to None by defining __eq__
        __hash__ = None

        def __eq__(self, other):
            return isinstance(other, UnhashableQuery)

        def __call__(self, value: Mapping) -> bool:
            return value.get('user') == 'john'

    query = UnhashableQuery()

    assert query({'user': 'john'}) is True

    # Requirement 2 of the protocol is violated: no stable hash for caching
    with pytest.raises(TypeError):
        hash(query)

def test_lambda_query_is_hashable_but_identity_based():
    query: QueryLike = lambda value: value.get('user') == 'john'

    assert query({'user': 'john'}) is True
    assert isinstance(query.__hash__(), int)

    # Default object hashing is identity based, so two equivalent lambdas differ
    other = lambda value: value.get('user') == 'john'
    assert hash(other) != hash(query)
