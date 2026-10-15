import json
import warnings
import pytest
from tinydb.storages import JSONStorage

def test_read_empty_file_returns_none(tmp_path):
    """Reading from an empty JSON file should return None."""
    path = str(tmp_path / "test.json")
    storage = JSONStorage(path)
    try:
        result = storage.read()
        assert result is None
    finally:
        storage.close()

def test_write_and_read_roundtrip(tmp_path):
    """Writing data then reading it back should return the same data."""
    path = str(tmp_path / "test.json")
    data = {"table1": {"doc1": {"name": "John", "age": 30}}}
    storage = JSONStorage(path)
    try:
        storage.write(data)
        result = storage.read()
        assert result == data
    finally:
        storage.close()

def test_read_existing_data_from_file(tmp_path):
    """Reading existing JSON data from a file should return the parsed content."""
    path = str(tmp_path / "test.json")
    existing = {"existing": "data", "nested": {"key": [1, 2, 3]}}
    with open(path, "w") as f:
        json.dump(existing, f)

    storage = JSONStorage(path)
    try:
        result = storage.read()
        assert result == existing
    finally:
        storage.close()

def test_write_shorter_data_truncates_previous_content(tmp_path):
    """Writing shorter data should truncate leftover bytes from previous content."""
    path = str(tmp_path / "test.json")
    storage = JSONStorage(path)
    try:
        long_data = {"a": "this is a much longer string value"}
        short_data = {"b": 1}
        storage.write(long_data)
        storage.write(short_data)
        assert storage.read() == short_data
    finally:
        storage.close()

def test_invalid_access_mode_warns(tmp_path):
    """An access mode other than 'r', 'rb', 'r+', 'rb+' should trigger a UserWarning."""
    path = str(tmp_path / "test.json")
    with pytest.warns(UserWarning, match="data loss or corruption"):
        storage = JSONStorage(path, access_mode="w")
    storage.close()

def test_read_only_access_mode_cannot_write(tmp_path):
    """Writing to a storage opened in read-only mode should raise IOError."""
    path = str(tmp_path / "test.json")
    # Pre-populate the file using a default writeable storage
    storage_writer = JSONStorage(path)
    storage_writer.write({"initial": "data"})
    storage_writer.close()

    # Reopen in read-only mode
    storage = JSONStorage(path, access_mode="r")
    try:
        with pytest.raises(IOError):
            storage.write({"new": "data"})
    finally:
        storage.close()

def test_create_dirs_creates_parent_directories(tmp_path):
    """create_dirs=True should create missing parent directories."""
    path = str(tmp_path / "subdir" / "nested" / "test.json")
    storage = JSONStorage(path, create_dirs=True)
    try:
        # The file should exist and be empty, so read() returns None
        assert storage.read() is None
    finally:
        storage.close()

def test_default_access_mode_does_not_warn(tmp_path):
    """The default access mode 'r+' should not trigger a warning."""
    path = str(tmp_path / "test.json")
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        storage = JSONStorage(path)
    storage.close()
    assert len(recorded) == 0

def test_close_closes_file_handle(tmp_path):
    """close() should close the underlying file handle."""
    path = str(tmp_path / "test.json")
    storage = JSONStorage(path)
    storage.close()
    assert storage._handle.closed

def test_read_multiple_times(tmp_path):
    """Reading multiple times in succession should return the same data."""
    path = str(tmp_path / "test.json")
    data = {"key": "value", "list": [1, 2, 3]}
    storage = JSONStorage(path)
    try:
        storage.write(data)
        assert storage.read() == data
        assert storage.read() == data
    finally:
        storage.close()

def test_write_empty_dict(tmp_path):
    """Writing an empty dict should produce a file that reads back as empty dict."""
    path = str(tmp_path / "test.json")
    storage = JSONStorage(path)
    try:
        storage.write({})
        assert storage.read() == {}
    finally:
        storage.close()

def test_write_nested_data(tmp_path):
    """Writing nested data structures should round-trip correctly."""
    path = str(tmp_path / "test.json")
    data = {
        "users": {
            "1": {"name": "Alice", "age": 30},
            "2": {"name": "Bob", "age": 25},
        }
    }
    storage = JSONStorage(path)
    try:
        storage.write(data)
        assert storage.read() == data
    finally:
        storage.close()

def test_read_invalid_json_raises(tmp_path):
    """Reading a file with invalid JSON content should raise JSONDecodeError."""
    path = str(tmp_path / "test.json")
    with open(path, "w") as f:
        f.write("not valid json {{{")

    storage = JSONStorage(path)
    try:
        with pytest.raises(json.JSONDecodeError):
            storage.read()
    finally:
        storage.close()

def test_write_with_indent_kwarg(tmp_path):
    """Passing json.dumps kwargs to JSONStorage should affect the serialization format."""
    path = str(tmp_path / "test.json")
    storage = JSONStorage(path, indent=2)
    try:
        storage.write({"a": 1})
        with open(path, "r") as f:
            content = f.read()
        # With indent=2, the serialized JSON should contain newlines
        assert "\n" in content
    finally:
        storage.close()
