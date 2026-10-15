import pytest
from tinydb.queries import where
from tinydb.queries import Query
from tinydb.queries import QueryInstance

def test_where_returns_callable_query_instance():
    """where(key) returns a callable QueryInstance, matching Query()[key]."""
    result = where('name')
    # The actual return of Query()[key] is a QueryInstance
    assert isinstance(result, QueryInstance)
    # And QueryInstance is callable (has __call__)
    assert callable(result)

