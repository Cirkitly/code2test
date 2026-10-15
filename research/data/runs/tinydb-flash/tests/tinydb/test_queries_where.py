import pytest
from tinydb import Query
from tinydb.queries import where

def test_where_returns_query_instance():
    """
    ``where`` is documented as a shorthand for ``Query()[key]``.

    The object returned must therefore be a ``Query`` instance, just like the
    one produced by writing ``Query()['key']`` by hand.
    """
    result = where('value')

    assert isinstance(result, Query)
    assert isinstance(Query()['value'], Query)

def test_where_result_is_callable():
    """
    The object returned by ``where`` is a callable query predicate. A bare key
    lookup is not evaluable on its own (it is an empty query until combined),
    but combined with a comparison it becomes a working predicate.
    """
    result = where('value')

    assert callable(result)
    assert (result == 1)({'value': 1}) is True
    assert (result == 2)({'value': 1}) is False

def test_where_is_equivalent_to_query_index_expression():
    """
    The whole point of ``where`` is to be a shorthand: for every key and every
    document, ``where(key)`` must behave identically to ``Query()[key]``.

    A bare key lookup is an empty query and cannot be evaluated directly, so
    equivalence is asserted through comparison combinations.
    """
    doc = {'name': 'John', 'age': 30}

    assert (where('name') == 'John')(doc) == (Query()['name'] == 'John')(doc)
    assert (where('age') == 30)(doc) == (Query()['age'] == 30)(doc)
    assert (where('age') > 18)(doc) == (Query()['age'] > 18)(doc)
    # A missing key resolves to None, so any equality comparison fails
    assert (where('missing') == 'John')(doc) is False
    assert (where('missing') == 'John')(doc) == (Query()['missing'] == 'John')(doc)

def test_where_resolves_nested_key_with_map():
    """
    ``Query()[key]`` supports ``.map()`` to walk into a subdocument, which is
    the idiomatic way of querying nested structures. ``where`` must keep that
    behaviour because it is only a shorthand.
    """
    query = where('name').map(lambda d: d['first'])

    assert (query == 'John')({'name': {'first': 'John'}}) is True
    assert (query == 'Jane')({'name': {'first': 'John'}}) is False

def test_where_can_be_composed_with_comparison_operators():
    """
    A ``where(key)`` result is normally combined with an operator (==, >, ...)
    to build a real condition. The shorthand must support that composition and
    the composed query must filter documents correctly.
    """
    condition = (where('age') > 18)

    assert condition({'age': 21}) is True
    assert condition({'age': 12}) is False
    assert condition({'other': 21}) is False

def test_where_with_empty_key_string():
    """
    ``where`` performs no validation of the key, so an empty string is simply
    forwarded to the mapping lookup. It must not raise and must behave the same
    as ``Query()['']``.
    """
    doc = {'': 'empty key value'}

    assert (where('') == 'empty key value')(doc) is True
    assert (where('') == 'empty key value')({'other': 1}) is False
    assert (where('') == 'empty key value')(doc) == (Query()[''] == 'empty key value')(doc)

def test_where_with_non_string_hashable_key():
    """
    The signature is annotated with ``str`` but no validation happens at
    runtime: any object is forwarded as a path element to ``Query()``. When the
    query is evaluated only ``str`` (and callable) path elements traverse the
    document, so a non-string key is ignored and the comparison is performed
    against the whole document. The result is identical to ``Query()[key]``.
    """
    doc = {1: 'one', ('a', 'b'): 'tuple key'}

    # Non-string keys are not used for a lookup: the document itself is compared
    assert (where(1) == 'one')(doc) is False
    assert (where(1) == 'one')(doc) == (Query()[1] == 'one')(doc)

    assert (where(('a', 'b')) == 'tuple key')(doc) is False
    assert (where(('a', 'b')) == 'tuple key')(doc) == (Query()[('a', 'b')] == 'tuple key')(doc)

    # An absent key behaves like any other non-string key: no lookup happens
    assert (where(99) == 'one')(doc) is False
    assert (where(99) == 'one')(doc) == (Query()[99] == 'one')(doc)

def test_where_with_missing_key_returns_none():
    """
    Resolving the path of an absent key fails and the resulting ``KeyError`` is
    caught by the query implementation. The condition therefore evaluates to
    ``False`` as a whole instead of comparing a ``None`` value: even ``!=``
    does not match a document that lacks the key. Present keys keep working
    normally.
    """
    doc = {'other': 'value'}

    # Missing key -> the entire condition is False, no value is compared
    assert (where('missing') == 'value')(doc) is False
    assert (where('missing') != 'value')(doc) is False
    assert (where('missing') == None)(doc) is False  # noqa: E711

    # Present key -> the comparison behaves normally
    assert (where('other') == 'value')(doc) is True
    assert (where('other') != 'value')(doc) is False

def test_where_falsy_and_truthy_values_in_boolean_context():
    """
    ``where`` produces a condition that matches a document when the stored value
    satisfies the comparison. Falsy stored values (0, '') therefore still match
    their own condition, while a document lacking the key does not.
    """
    doc = {'zero': 0, 'empty': '', 'filled': 'yes'}

    assert (where('filled') == 'yes')(doc) is True
    assert (where('filled') == 'no')(doc) is False

    # Falsy stored values still match when compared against themselves
    assert (where('zero') == 0)(doc) is True
    assert (where('empty') == '')(doc) is True

    # An absent key resolves to None and matches neither
    assert (where('absent') == 0)(doc) is False
    assert (where('absent') == '')(doc) is False

def test_where_returns_new_independent_query_each_call():
    """
    ``where`` builds a brand new ``Query()`` on every call. Two calls must
    return equal-but-distinct objects that do not share state.
    """
    first = where('value')
    second = where('value')

    assert first is not second
    assert first == second

def test_where_combined_with_logical_or_operator():
    """
    Shorthand queries compose: ``where(a) == 1 | where(b) == 2`` must match a
    document that satisfies either branch, exactly like the expanded form.
    """
    condition = (where('a') == 1) | (where('b') == 2)

    assert condition({'a': 1}) is True
    assert condition({'b': 2}) is True
    assert condition({'a': 1, 'b': 2}) is True
    assert condition({'a': 3, 'b': 4}) is False
