import json
import os
import warnings
from pathlib import Path
import pytest
from tinydb.storages import JSONStorage

@pytest.fixture
def storage_path(tmp_path):
    """Path to a JSON database file inside a temporary directory."""
    return str(tmp_path / 'db.json')


@pytest.fixture
def storage(storage_path):
    """A ``JSONStorage`` opened in the default ``r+`` access mode, closed on teardown."""
    instance = JSONStorage(storage_path)
    yield instance
    instance.close()


@pytest.fixture
def existing_file(tmp_path):
    """Return a factory that creates a JSON file with given raw content at a fixed path."""
    path = str(tmp_path / 'existing.json')

    def _create(content):
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)
        return path

    return _create

def test_new_storage_reads_none_from_newly_created_file(storage_path):
    # The default access mode ('r+') creates the file on instantiation
    instance = JSONStorage(storage_path)
    try:
        assert instance.read() is None
    finally:
        instance.close()

def test_write_then_read_returns_written_data(storage):
    data = {'users': {'1': {'name': 'Alice', 'age': 30}}}

    storage.write(data)

    assert storage.read() == data

def test_write_persists_data_on_disk_as_json(storage, storage_path):
    data = {'users': {'1': {'name': 'Alice'}}}

    storage.write(data)
    storage.close()

    # The file on disk holds exactly the JSON serialization of the data
    assert Path(storage_path).read_text(encoding='utf-8') == json.dumps(data)

    # A different instance reading the same file sees the persisted data
    reopened = JSONStorage(storage_path, access_mode='r')
    try:
        assert reopened.read() == data
    finally:
        reopened.close()

def test_nested_data_survives_round_trip(storage):
    data = {
        'items': {
            '1': {
                'name': 'Ünïcödé',
                'count': 3,
                'active': True,
                'parent': None,
                'tags': ['a', 'b'],
                'meta': {'nested': {'deep': [1, 2, {'x': 'y'}]}},
            }
        }
    }

    storage.write(data)

    assert storage.read() == data

def test_read_returns_none_for_existing_but_empty_file(tmp_path):
    path = str(tmp_path / 'empty.json')
    with open(path, 'w'):
        pass

    instance = JSONStorage(path, access_mode='r')
    try:
        assert instance.read() is None
    finally:
        instance.close()

def test_file_is_created_on_init_in_writable_access_mode(tmp_path):
    path = str(tmp_path / 'created.json')
    assert not os.path.exists(path)

    instance = JSONStorage(path, access_mode='r+')
    try:
        assert os.path.exists(path)
    finally:
        instance.close()

def test_read_only_access_mode_does_not_create_missing_file(tmp_path):
    path = str(tmp_path / 'missing.json')

    with pytest.raises(FileNotFoundError):
        JSONStorage(path, access_mode='r')

    assert not os.path.exists(path)

def test_read_only_access_mode_returns_existing_data(existing_file):
    data = {'table': {'1': {'a': 1}}}
    path = existing_file(json.dumps(data))

    instance = JSONStorage(path, access_mode='r')
    try:
        assert instance.read() == data
    finally:
        instance.close()

def test_binary_read_only_access_mode_returns_existing_data(existing_file):
    data = {'table': {'1': {'a': 1}}}
    path = existing_file(json.dumps(data))

    instance = JSONStorage(path, access_mode='rb')
    try:
        assert instance.read() == data
    finally:
        instance.close()

def test_binary_plus_access_mode_supports_write_and_read(tmp_path):
    path = str(tmp_path / 'binary.json')
    data = {'table': {'1': {'a': 1}}}

    instance = JSONStorage(path, access_mode='rb+')
    try:
        # The handle is opened in binary mode, so writing the serialized
        # (text) database content raises a TypeError
        with pytest.raises(TypeError):
            instance.write(data)

        # Nothing was written, so the file is still empty and ``read``
        # reports an uninitialized database
        assert instance.read() is None
    finally:
        instance.close()

def test_write_in_read_only_access_mode_raises_ioerror_and_keeps_file_unchanged(existing_file):
    original = {'table': {'1': {'a': 1}}}
    path = existing_file(json.dumps(original))

    instance = JSONStorage(path, access_mode='r')
    try:
        with pytest.raises(IOError) as exc_info:
            instance.write({'table': {'2': {'b': 2}}})

        assert str(exc_info.value) == 'Cannot write to the database. Access mode is "r"'
        # The file content must not have been modified
        assert Path(path).read_text(encoding='utf-8') == json.dumps(original)
    finally:
        instance.close()

def test_write_starts_at_beginning_of_file(storage, storage_path):
    storage.write({'small': {'1': 1}})
    storage.read()  # leaves the cursor at the end of the file

    larger = {'larger': {'1': {'value': 'x' * 100}}}
    storage.write(larger)
    storage.close()

    assert Path(storage_path).read_text(encoding='utf-8') == json.dumps(larger)

def test_write_truncates_file_when_new_data_is_shorter(storage, storage_path):
    long_data = {'table': {'1': {'value': 'y' * 500}}}
    short_data = {'table': {'1': {'value': 'z'}}}

    storage.write(long_data)
    storage.write(short_data)
    storage.close()

    assert Path(storage_path).read_text(encoding='utf-8') == json.dumps(short_data)

def test_write_replaces_previously_stored_tables_completely(storage):
    storage.write({'a': {'1': {'x': 1}}, 'b': {'2': {'y': 2}}})

    storage.write({'a': {'1': {'x': 99}}})

    assert storage.read() == {'a': {'1': {'x': 99}}}

def test_repeated_read_calls_return_the_same_data(storage):
    data = {'table': {'1': {'a': 1}}}
    storage.write(data)

    assert storage.read() == data
    assert storage.read() == data
    assert storage.read() == data

@pytest.mark.parametrize('access_mode', ['w', 'a'])
def test_warns_for_access_modes_other_than_read_variants(tmp_path, access_mode):
    path = str(tmp_path / 'db.json')

    with pytest.warns(UserWarning, match='can cause data loss or corruption'):
        instance = JSONStorage(path, access_mode=access_mode)

    instance.close()

@pytest.mark.parametrize('access_mode', ['r+', 'rb+'])
def test_no_warning_for_documented_access_modes(tmp_path, access_mode):
    path = str(tmp_path / 'db.json')
    with open(path, 'w'):
        pass

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        instance = JSONStorage(path, access_mode=access_mode)

    instance.close()

    assert [w for w in caught if issubclass(w.category, UserWarning)] == []

def test_write_access_mode_truncates_existing_file(existing_file):
    path = existing_file(json.dumps({'old': {'data': 1}}))

    with pytest.warns(UserWarning):
        instance = JSONStorage(path, access_mode='w')

    try:
        assert instance.read() is None
    finally:
        instance.close()

def test_create_dirs_creates_missing_parent_directories(tmp_path):
    path = str(tmp_path / 'nested' / 'dir' / 'db.json')

    instance = JSONStorage(path, create_dirs=True)
    try:
        assert os.path.exists(path)
        assert instance.read() is None
    finally:
        instance.close()

def test_missing_parent_directory_without_create_dirs_raises_error(tmp_path):
    path = str(tmp_path / 'does_not_exist' / 'db.json')

    with pytest.raises(OSError):
        JSONStorage(path)

    assert not os.path.exists(path)

def test_extra_keyword_arguments_are_forwarded_to_json_dumps(storage_path):
    data = {'b': {'2': {'z': 1}}, 'a': {'1': {'y': 2}}}

    instance = JSONStorage(storage_path, sort_keys=True, indent=2)
    instance.write(data)
    instance.close()

    assert Path(storage_path).read_text(encoding='utf-8') == json.dumps(
        data, sort_keys=True, indent=2
    )

def test_encoding_is_used_for_non_ascii_data(tmp_path):
    path = str(tmp_path / 'utf8.json')
    data = {'table': {'1': {'name': 'Ünïcödé ✓'}}}

    instance = JSONStorage(path, encoding='utf-8')
    instance.write(data)
    instance.close()

    assert json.loads(Path(path).read_text(encoding='utf-8')) == data

    reopened = JSONStorage(path, access_mode='r', encoding='utf-8')
    try:
        assert reopened.read() == data
    finally:
        reopened.close()

def test_read_raises_json_decode_error_for_invalid_json(existing_file):
    path = existing_file('this is not json')

    instance = JSONStorage(path, access_mode='r')
    try:
        with pytest.raises(json.JSONDecodeError):
            instance.read()
    finally:
        instance.close()

def test_close_releases_the_file_but_data_stays_persisted(storage_path):
    data = {'table': {'1': {'a': 1}}}

    instance = JSONStorage(storage_path)
    instance.write(data)
    instance.close()

    with pytest.raises(ValueError):
        instance.read()

    reopened = JSONStorage(storage_path, access_mode='r')
    try:
        assert reopened.read() == data
    finally:
        reopened.close()
