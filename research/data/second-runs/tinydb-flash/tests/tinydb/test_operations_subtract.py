import pytest
from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_returns_a_callable_transform():
    """subtract(field, n) returns a callable used to transform a document."""
    transform = subtract('score', 3)

    assert callable(transform)

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_transform_returns_none():
    """The returned transform performs its work in place and returns None."""
    doc = {'score': 10}

    result = subtract('score', 3)(doc)

    assert result is None

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_reduces_numeric_field_by_n():
    """The value of the given field is reduced by exactly ``n``."""
    doc = {'score': 10}

    subtract('score', 3)(doc)

    assert doc == {'score': 7}

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_mutates_document_in_place():
    """The very same dict instance passed in is the one that is modified."""
    doc = {'score': 10}

    subtract('score', 3)(doc)

    assert doc['score'] == 7  # the original object was mutated, not a copy

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_with_zero_leaves_value_unchanged():
    """Subtracting 0 is a valid, value-preserving operation."""
    doc = {'score': 42}

    subtract('score', 0)(doc)

    assert doc == {'score': 42}

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_with_negative_n_increases_value():
    """A negative amount behaves like an addition (10 - (-5) == 15)."""
    doc = {'score': 10}

    subtract('score', -5)(doc)

    assert doc == {'score': 15}

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_supports_float_amounts():
    """Floats are supported for both the stored value and the amount."""
    doc = {'ratio': 1.5}

    subtract('ratio', 0.5)(doc)

    assert doc['ratio'] == pytest.approx(1.0)

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_leaves_other_fields_untouched():
    """Only the field named in the call is modified."""
    doc = {'name': 'Alice', 'score': 10, 'rank': 1}

    subtract('score', 3)(doc)

    assert doc == {'name': 'Alice', 'score': 7, 'rank': 1}

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_can_be_applied_repeatedly_accumulating():
    """Reusing the transform subtracts the amount each time it runs."""
    doc = {'score': 10}
    transform = subtract('score', 3)

    transform(doc)
    transform(doc)

    assert doc == {'score': 4}

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_raises_key_error_when_field_is_missing():
    """A missing field surfaces as a KeyError from the dict lookup."""
    doc = {'name': 'Alice'}

    with pytest.raises(KeyError):
        subtract('score', 3)(doc)

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_raises_type_error_for_non_numeric_field():
    """Subtracting from a non-numeric value raises TypeError and changes nothing."""
    doc = {'name': 'Alice'}

    with pytest.raises(TypeError):
        subtract('name', 3)(doc)

    assert doc == {'name': 'Alice'}

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_raises_type_error_for_non_numeric_amount():
    """Subtracting a non-numeric amount raises TypeError and changes nothing."""
    doc = {'score': 10}

    with pytest.raises(TypeError):
        subtract('score', 'three')(doc)

    assert doc == {'score': 10}

import pytest

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import subtract


def test_subtract_works_as_tinydb_update_operation():
    """The transform returned by subtract can drive a TinyDB update."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'Alice', 'score': 10})
    db.insert({'name': 'Bob', 'score': 3})

    db.update(subtract('score', 4), cond=lambda doc: doc['score'] > 5)

    scores = {doc['name']: doc['score'] for doc in db.all()}
    assert scores == {'Alice': 6, 'Bob': 3}
