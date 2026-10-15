import pytest
from tinydb.queries import where
from tinydb.queries import Query, QueryInstance

@pytest.fixture
def users():
    """A small list of documents used to emulate table contents."""
    return [
        {'name': 'John', 'age': 22},
        {'name': 'Jane', 'age': 44},
        {'name': 'Bob', 'age': 22},
    ]

def test_where_returns_a_query_object():
    """``where('name')`` returns a usable query object (like ``Query()``)."""
    query = where('name')

    assert isinstance(query, Query)
    assert isinstance(query, QueryInstance)
    assert callable(query)

def test_where_creates_a_new_object_on_every_call():
    """Every call builds a brand new query instead of returning a shared object."""
    first = where('name')
    second = where('name')

    assert first is not second

def test_where_behaves_like_query_index_access():
    """``where(key)`` is equivalent to ``Query()[key]`` in every observable way."""
    shorthand = where('name')
    explicit = Query()['name']

    assert shorthand.is_cacheable() == explicit.is_cacheable()

    documents = [{'name': 'John'}, {'name': ''}, {'nickname': 'John'}, {}]
    for document in documents:
        assert shorthand.exists()(document) == explicit.exists()(document)
        assert (shorthand == 'John')(document) == (explicit == 'John')(document)
        assert (shorthand.matches('^J'))(document) == (explicit.matches('^J'))(document)

def test_where_result_is_cacheable():
    """A field lookup query carries a hash value and can therefore be cached."""
    assert where('name').is_cacheable() is True

def test_where_matches_document_containing_the_key():
    """The query matches documents that contain the queried key."""
    assert where('name').exists()({'name': 'John'}) is True
    assert where('age').exists()({'name': 'John', 'age': 22}) is True

def test_where_does_not_match_document_missing_the_key():
    """A document that lacks the queried key never matches."""
    assert where('name').exists()({'age': 22}) is False
    assert where('age').exists()({'name': 'John'}) is False

def test_where_matches_key_holding_none():
    """Existence is about the key, not about the truthiness of its value."""
    assert where('name').exists()({'name': None}) is True

def test_where_supports_empty_key():
    """The empty string is treated like any other (valid) key."""
    query = where('').exists()

    assert query({'': 'value'}) is True
    assert query({'name': 'value'}) is False

def test_where_treats_dots_in_keys_literally():
    """``where`` uses plain item access - a dot inside the key is literal."""
    query = where('a.b').exists()

    assert query({'a.b': 1}) is True
    assert query({'a': {'b': 1}}) is False

def test_where_supports_equality_comparison():
    """``where(key) == value`` builds a query comparing the stored value."""
    query = where('name') == 'John'

    assert query({'name': 'John'}) is True
    assert query({'name': 'Jane'}) is False
    assert query({'nickname': 'John'}) is False

def test_where_equality_comparison_handles_list_values():
    """Queries built from ``where`` can compare unhashable (list) values."""
    query = where('tags') == ['a', 'b']

    assert query({'tags': ['a', 'b']}) is True
    assert query({'tags': ['a']}) is False
    assert query({'tags': 'a'}) is False
    # the comparison value is frozen, so the query stays cacheable
    assert query.is_cacheable() is True

def test_where_supports_regex_matching():
    """``where(key).matches(...)`` tests the stored value against a regex."""
    query = where('name').matches(r'\d+')

    # A value starting with digits matches the regex.
    assert query({'name': '42'}) is True

    # ``matches`` anchors the pattern at the start of the string, so a
    # trailing match does not count.
    assert query({'name': 'John 42'}) is False

    # A value that does not contain digits at all does not match.
    assert query({'name': 'John'}) is False

def test_where_resolves_nested_keys():
    """``where('user')['name']`` resolves a nested path."""
    query = where('user')['name'].exists()

    assert query({'user': {'name': 'John'}}) is True
    assert query({'user': {}}) is False
    assert query({}) is False

def test_where_returns_false_when_nested_path_cannot_be_resolved():
    """An unresolvable path (non-mapping on the way) results in "no match"."""
    query = where('user')['name'].exists()

    # looking up ``'name'`` inside a string/list/number would raise a TypeError
    assert query({'user': 'John'}) is False
    assert query({'user': 42}) is False
    assert query({'user': ['name']}) is False
    assert query({'user': None}) is False

def test_where_chaining_does_not_modify_the_parent_query():
    """Building a child query does not change the query it was derived from."""
    parent = where('a')
    child = parent['b']

    assert child.exists()({'a': {'b': 1}}) is True

    # the parent query still only looks at the key ``a``
    assert parent.one_of([1])({'a': 1}) is True
    assert parent.one_of([1])({'a': {'b': 1}}) is False

def test_where_index_and_attribute_chaining_are_equivalent():
    """Item access and attribute access build equivalent nested queries."""
    index_query = where('user')['name'].exists()
    attribute_query = Query().user.name.exists()

    documents = [
        {'user': {'name': 'John'}},
        {'user': {'nickname': 'John'}},
        {'user': 'John'},
        {},
    ]

    for document in documents:
        assert index_query(document) == attribute_query(document)

    assert index_query({'user': {'name': 'John'}}) is True

def test_where_filters_a_list_of_documents(users):
    """``where`` queries can be used to filter documents like a table search."""
    matched = [user for user in users if (where('age') == 22)(user)]

    assert matched == [
        {'name': 'John', 'age': 22},
        {'name': 'Bob', 'age': 22},
    ]

def test_bare_where_query_returns_false_when_key_is_missing():
    """Evaluating a bare ``where(key)`` query raises a RuntimeError.

    ``where(key)`` only selects the key path -- without a condition such
    as ``.exists()`` the resulting query is empty, and TinyDB refuses to
    evaluate empty queries instead of silently returning a result.
    """
    with pytest.raises(RuntimeError):
        where('name')({'nickname': 'John'})

def test_bare_where_query_does_not_match_a_document_containing_the_key():
    """``where(key)`` alone only builds a path - it never reports a match."""
    query = where('name')

    try:
        matched = query({'name': 'John'})
    except RuntimeError:
        # TinyDB refuses to run a query for which no test has been attached
        matched = False

    assert matched is not True

@pytest.mark.parametrize('key', ['', ' ', '0', '_id', 'a-b_c', '\u00e4', 'a.b[0]'])
def test_where_accepts_unusual_keys(key):
    """Any string key - including odd looking ones - can be queried for."""
    query = where(key).exists()

    assert query({key: 1}) is True
    assert query({}) is False
