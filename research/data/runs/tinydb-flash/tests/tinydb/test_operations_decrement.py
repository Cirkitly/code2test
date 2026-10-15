import pytest
from tinydb.operations import decrement

@pytest.fixture
def doc():
    """A simple document with a single integer field used by many tests."""
    return {'count': 5}

def test_decrement_returns_a_callable_transform():
    """``decrement(field)`` returns a callable that transforms a document."""
    transform = decrement('age')

    assert callable(transform)
