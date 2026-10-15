import json
import os
import warnings
import pytest
from tinydb.storages import JSONStorage

@pytest.fixture
def json_file(tmp_path):
    """Return a path to a fresh temporary JSON file inside a per-test temp dir."""
    return str(tmp_path / "db.json")

import json

from tinydb.storages import JSONStorage


def test_write_and_read_data_roundtrip(json_file):
    """Writing data and reading it back should return the same data."""
    storage = JSONStorage(json_file)
    data = {"users": {"1": {"name": "Alice"}, "2": {"name": "Bob"}}}
    storage.write(data)
    result = storage.read()
    assert result == data
    storage.close()


from tinydb.storages import JSONStorage


def test_read_returns_none_for_empty_file(json_file):
    """A freshly created (and therefore empty) file should yield None on read."""
    storage = JSONStorage(json_file)
    result = storage.read()
    assert result is None
    storage.close()


import json
import os

from tinydb.storages import JSONStorage


def test_write_truncates_existing_data_when_shorter(json_file):
    """Writing smaller data after larger data should truncate the file to the new size."""
    storage = JSONStorage(json_file)

    # Write a large payload first.
    large_data = {"key": "x" * 1000}
    storage.write(large_data)

    # Then write a much smaller payload.
    small_data = {"key": "small"}
    storage.write(small_data)

    # Read should now return only the small data, no leftover from the large payload.
    result = storage.read()
    assert result == small_data

    # The on-disk content should match exactly the new serialized payload
    # (i.e. no stale bytes left over from the previous write).
    with open(json_file, "r") as f:
        raw = f.read()
    assert raw == json.dumps(small_data)

    storage.close()


import pytest

from tinydb.storages import JSONStorage


def test_close_makes_handle_unusable(json_file):
    """After close(), the underlying file handle is closed and I/O raises ValueError."""
    storage = JSONStorage(json_file)
    storage.close()
    with pytest.raises(ValueError):
        storage.read()
    with pytest.raises(ValueError):
        storage.write({"key": "value"})


import os

from tinydb.storages import JSONStorage


def test_create_dirs_true_creates_parent_directories(tmp_path):
    """create_dirs=True should create missing parent directories for the storage file."""
    nested_path = str(tmp_path / "a" / "b" / "c" / "db.json")
    # Sanity check: the parent directory does not exist yet.
    assert not os.path.exists(os.path.dirname(nested_path))

    storage = JSONStorage(nested_path, create_dirs=True)

    # The file (and its parent directories) should now exist.
    assert os.path.exists(nested_path)

    storage.write({"foo": "bar"})
    assert storage.read() == {"foo": "bar"}
    storage.close()


import pytest

from tinydb.storages import JSONStorage


def test_create_dirs_false_raises_when_parent_missing(tmp_path):
    """create_dirs=False should not create parent directories and should raise OSError."""
    nested_path = str(tmp_path / "missing_parent" / "db.json")
    with pytest.raises(OSError):
        JSONStorage(nested_path, create_dirs=False)


import pytest

from tinydb.storages import JSONStorage


def test_write_raises_ioerror_in_read_only_mode(tmp_path):
    """Writing through a storage opened in 'r' mode should raise IOError."""
    file_path = str(tmp_path / "db.json")

    # First, create the file with some data using the default write-capable mode.
    setup = JSONStorage(file_path)
    setup.write({"initial": "data"})
    setup.close()

    # Reopen in read-only mode and attempt to write.
    storage = JSONStorage(file_path, access_mode="r")
    with pytest.raises(IOError):
        storage.write({"new": "data"})
    storage.close()


from tinydb.storages import JSONStorage


def test_read_only_mode_can_read_existing_data(tmp_path):
    """Read-only mode should still serve existing data via read()."""
    file_path = str(tmp_path / "db.json")
    data = {"users": {"1": {"name": "Alice"}}}

    # Persist data first using the default mode.
    setup = JSONStorage(file_path)
    setup.write(data)
    setup.close()

    # Open in 'r' mode and confirm we can read the data back.
    storage = JSONStorage(file_path, access_mode="r")
    assert storage.read() == data
    storage.close()


import warnings

from tinydb.storages import JSONStorage


def test_warning_issued_for_non_standard_access_mode(json_file):
    """A non-standard access mode should emit a UserWarning.

    Using 'w+' (which contains 'w') still triggers the warning because the
    mode is not one of 'r', 'rb', 'r+', or 'rb+'. 'w+' also allows both
    reading and writing, so we can verify the storage is still usable.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        storage = JSONStorage(json_file, access_mode="w+")

    user_warnings = [item for item in caught if issubclass(item.category, UserWarning)]
    assert len(user_warnings) >= 1

    # The storage should still be usable after the warning.
    storage.write({"key": "value"})
    assert storage.read() == {"key": "value"}
    storage.close()

import warnings

from tinydb.storages import JSONStorage


def test_no_warning_issued_for_standard_access_modes(tmp_path):
    """Standard access modes (r, rb, r+, rb+) should not trigger the data-loss warning."""
    file_path = str(tmp_path / "db.json")
    # 'r' and 'rb' do not create the file, so seed it first.
    with open(file_path, "w") as f:
        f.write("{}")

    for mode in ("r", "rb", "r+", "rb+"):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            storage = JSONStorage(file_path, access_mode=mode)

        # No UserWarning about data loss / access mode should be raised.
        suspicious = [
            item
            for item in caught
            if issubclass(item.category, UserWarning)
            and "access_mode" in str(item.message)
        ]
        assert suspicious == [], (
            f"Unexpected data-loss warning emitted for standard mode {mode!r}: "
            f"{[str(w.message) for w in suspicious]}"
        )
        storage.close()


from tinydb.storages import JSONStorage


def test_extra_kwargs_passed_to_json_dumps(json_file):
    """Constructor **kwargs should be forwarded to json.dumps when writing."""
    # Use sort_keys=True to enforce a deterministic key order in the file,
    # and indent=2 to make the multi-line formatting observable on disk.
    storage = JSONStorage(json_file, sort_keys=True, indent=2)
    storage.write({"b": 2, "a": 1})

    with open(json_file, "r") as f:
        raw = f.read()

    # sort_keys=True: 'a' must appear before 'b' in the raw file.
    assert raw.index('"a"') < raw.index('"b"')
    # indent=2: the serialization should be spread across multiple lines.
    assert "\n" in raw

    # The parsed result should still match what we wrote.
    assert storage.read() == {"b": 2, "a": 1}
    storage.close()

