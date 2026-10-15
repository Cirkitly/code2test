import builtins
import pytest
import tinydb.operations as operations_module
from tinydb import TinyDB
from tinydb.operations import delete, set
from tinydb.storages import MemoryStorage

def test_set_updates_existing_field_in_place():
    """Assigning to an existing field overwrites the old value in place."""
    doc = {'status': 'active', 'other': 1}

    result = set('status', 'archived')(doc)

    assert doc == {'status': 'archived', 'other': 1}
    assert result is None
