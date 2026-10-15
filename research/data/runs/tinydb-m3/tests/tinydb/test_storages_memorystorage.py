import pytest
from tinydb.storages import MemoryStorage

def test_initial_state_returns_none():
    """A freshly constructed MemoryStorage has no data; read() returns None."""
    storage = MemoryStorage()

    assert storage.read() is None


def test_write_then_read_returns_written_data():
    """After write(), read() should return a value equal to the written dict."""
    storage = MemoryStorage()
    payload = {"users": {"u1": {"name": "Alice"}}, "items": {"i1": {"price": 9.99}}}

    storage.write(payload)

    result = storage.read()
    assert result == payload
    assert isinstance(result, dict)


def test_subsequent_write_overwrites_previous_data():
    """Calling write() again should replace the data previously stored in memory."""
    storage = MemoryStorage()
    storage.write({"first": 1, "shared": "old"})
    storage.write({"second": 2, "shared": "new"})

    result = storage.read()
    assert result == {"second": 2, "shared": "new"}
    assert "first" not in result


def test_writing_empty_dict_distinguishes_from_initial_state():
    """Writing {} should leave read() returning an empty dict, distinct from the initial None."""
    storage = MemoryStorage()
    storage.write({})

    result = storage.read()
    assert result == {}
    assert result is not None
    assert isinstance(result, dict)


def test_writing_complex_nested_data_round_trips_intact():
    """Deeply nested data structures must be preserved verbatim by write()/read()."""
    storage = MemoryStorage()
    nested = {
        "table_a": {
            "id1": {"meta": {"tags": ["a", "b"], "active": True}, "count": 0},
        },
        "table_b": {
            "id2": {"value": None, "label": "", "ratio": 1.5},
        },
    }

    storage.write(nested)

    assert storage.read() == nested


def test_overwriting_with_empty_dict_clears_previous_data():
    """Writing {} after a non-empty write should reset memory to {}, not leave prior data."""
    storage = MemoryStorage()
    storage.write({"keep": "me"})
    storage.write({})

    assert storage.read() == {}


def test_instances_have_independent_memory():
    """Two MemoryStorage instances must not share state; writes in one are invisible to the other."""
    storage_a = MemoryStorage()
    storage_b = MemoryStorage()

    storage_a.write({"only_in_a": True})

    assert storage_a.read() == {"only_in_a": True}
    assert storage_b.read() is None

    storage_b.write({"only_in_b": "yes"})

    assert storage_a.read() == {"only_in_a": True}
    assert storage_b.read() == {"only_in_b": "yes"}


def test_consecutive_reads_are_stable():
    """Multiple read() calls without an intervening write() must return the same value."""
    storage = MemoryStorage()
    storage.write({"stable": True})

    first = storage.read()
    second = storage.read()
    third = storage.read()

    assert first == second == third == {"stable": True}
