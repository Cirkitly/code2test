import json
import os
import warnings
import pytest
from tinydb.storages import JSONStorage
from tinydb.storages import Storage

@pytest.fixture
def db_path(tmp_path):
    """Return the path (as string) of a JSON database file inside ``tmp_path``."""
    return str(tmp_path / 'db.json')

@pytest.fixture
def storage(db_path):
    """Return a ready to use ``JSONStorage`` for a fresh file in ``tmp_path``."""
    store = JSONStorage(db_path)
    yield store
    store.close()

def test_json_storage_is_a_storage_instance(db_path):
    """JSONStorage is a concrete implementation of the abstract Storage base class."""
    store = JSONStorage(db_path)

    assert isinstance(store, Storage)

    store.close()

def test_json_storage_creates_file_on_initialisation(db_path):
    """With the default access mode 'r+' the JSON file is created if missing."""
    assert not os.path.exists(db_path)

    store = JSONStorage(db_path)

    assert os.path.exists(db_path)
    assert os.path.getsize(db_path) == 0

    store.close()

def test_json_storage_read_returns_none_for_empty_file(storage):
    """An empty file is reported as ``None`` so TinyDB can initialise the database."""
    assert storage.read() is None

def test_json_storage_write_then_read_roundtrip(storage):
    """Data written via write() is returned unchanged by read()."""
    data = {
        'default': {
            '1': {'name': 'John', 'age': 42, 'active': True, 'tags': None},
            '2': {'name': 'Alice', 'scores': [1.5, 2.5]},
        }
    }

    storage.write(data)

    assert storage.read() == data

def test_json_storage_writes_valid_json_to_file(db_path):
    """The file content equals json.dumps() of the written data."""
    data = {'default': {'1': {'name': 'John'}}}

    store = JSONStorage(db_path)
    store.write(data)
    store.close()

    with open(db_path, encoding='utf-8') as handle:
        content = handle.read()

    assert content == json.dumps(data)
    assert json.loads(content) == data

def test_json_storage_persists_data_across_instances(db_path):
    """The JSON file is the persistent store: a new instance sees previously written data."""
    data = {'default': {'1': {'value': 'persisted'}}}

    first = JSONStorage(db_path)
    first.write(data)
    first.close()

    second = JSONStorage(db_path)
    assert second.read() == data
    second.close()

def test_json_storage_second_write_is_not_appended(db_path):
    """Writing twice replaces the previous content instead of appending it."""
    first_data = {'default': {'1': {'value': 'first'}}}
    second_data = {'default': {'2': {'value': 'second'}}}

    store = JSONStorage(db_path)
    store.write(first_data)
    store.write(second_data)
    store.close()

    with open(db_path, encoding='utf-8') as handle:
        content = handle.read()

    assert content == json.dumps(second_data)

def test_json_storage_truncates_file_when_data_gets_shorter(db_path):
    """A write() that produces less data removes the trailing bytes of the old content."""
    long_data = {'default': {str(i): {'value': 'x' * 50} for i in range(10)}}
    short_data = {'default': {}}

    store = JSONStorage(db_path)
    store.write(long_data)
    long_size = os.path.getsize(db_path)

    store.write(short_data)
    short_size = os.path.getsize(db_path)
    assert store.read() == short_data
    store.close()

    assert short_size == len(json.dumps(short_data))
    assert short_size < long_size

def test_json_storage_write_passes_kwargs_to_json_dumps(db_path):
    """Additional keyword arguments are forwarded to json.dumps when serialising."""
    data = {'b': {'2': {'name': 'Bob'}}, 'a': {'1': {'name': 'Alice'}}}

    store = JSONStorage(db_path, sort_keys=True, indent=2)
    store.write(data)
    store.close()

    with open(db_path, encoding='utf-8') as handle:
        content = handle.read()

    assert content == json.dumps(data, sort_keys=True, indent=2)
    assert '\n' in content
    assert content.index('"a"') < content.index('"b"')

def test_json_storage_roundtrips_non_ascii_data_with_default_encoding(db_path):
    """Non-ASCII values survive the roundtrip; json.dumps escapes them by default."""
    data = {'default': {'1': {'name': 'Ünïcödé ☃'}}}

    store = JSONStorage(db_path)
    store.write(data)
    assert store.read() == data
    store.close()

    # json.dumps() escapes non-ASCII characters unless ensure_ascii=False is used,
    # so the file on disk stays readable with plain ASCII.
    with open(db_path, encoding='ascii') as handle:
        assert json.load(handle) == data

def test_json_storage_writes_raw_utf8_bytes_when_ensure_ascii_disabled(db_path):
    """``encoding`` and ``ensure_ascii=False`` make the file contain real UTF-8 bytes."""
    data = {'default': {'1': {'name': 'Ünïcödé ☃'}}}

    store = JSONStorage(db_path, encoding='utf-8', ensure_ascii=False)
    store.write(data)
    store.close()

    with open(db_path, 'rb') as handle:
        raw = handle.read()

    assert raw == json.dumps(data, ensure_ascii=False).encode('utf-8')

    reopened = JSONStorage(db_path, encoding='utf-8')
    assert reopened.read() == data
    reopened.close()

def test_json_storage_read_returns_none_when_file_contains_json_null(db_path):
    """A non-empty file holding the JSON literal ``null`` also results in ``None``."""
    with open(db_path, 'w', encoding='utf-8') as handle:
        handle.write('null')

    store = JSONStorage(db_path)

    assert store.read() is None

    store.close()

def test_json_storage_read_returns_empty_dict_for_empty_json_object(storage):
    """Writing an empty database produces '{}' which reads back as {} (not None)."""
    storage.write({})

    result = storage.read()

    assert result == {}
    assert result is not None

def test_json_storage_read_returns_arbitrary_json_structures(db_path):
    """read() returns the decoded JSON value of the file, whatever its type."""
    with open(db_path, 'w', encoding='utf-8') as handle:
        json.dump([1, 2, {'three': 3}], handle)

    store = JSONStorage(db_path)

    assert store.read() == [1, 2, {'three': 3}]

    store.close()

def test_json_storage_read_raises_json_decode_error_for_invalid_json(db_path):
    """Content that is not valid JSON makes read() raise a JSONDecodeError."""
    with open(db_path, 'w', encoding='utf-8') as handle:
        handle.write('this is not json')

    store = JSONStorage(db_path)

    with pytest.raises(json.JSONDecodeError):
        store.read()

    store.close()

def test_json_storage_read_only_mode_does_not_create_missing_file(tmp_path):
    """With access_mode='r' no file is created and opening a missing file fails."""
    db_path = str(tmp_path / 'missing.json')

    with pytest.raises(FileNotFoundError):
        JSONStorage(db_path, access_mode='r')

    assert not os.path.exists(db_path)

def test_json_storage_read_only_mode_reads_existing_file(db_path):
    """A storage opened with access_mode='r' can read an already existing file."""
    data = {'default': {'1': {'name': 'John'}}}

    writer = JSONStorage(db_path)
    writer.write(data)
    writer.close()

    store = JSONStorage(db_path, access_mode='r')

    assert store.read() == data

    store.close()

def test_json_storage_write_raises_ioerror_in_read_only_mode(db_path):
    """Writing with access_mode='r' raises an IOError instead of failing silently."""
    with open(db_path, 'w', encoding='utf-8') as handle:
        handle.write('{}')

    store = JSONStorage(db_path, access_mode='r')

    with pytest.raises(IOError, match='Cannot write to the database'):
        store.write({'default': {'1': {'name': 'John'}}})

    store.close()

def test_json_storage_write_error_message_contains_access_mode(db_path):
    """The IOError raised for a read-only handle mentions the access mode in use."""
    with open(db_path, 'w', encoding='utf-8') as handle:
        handle.write('{}')

    store = JSONStorage(db_path, access_mode='r')

    with pytest.raises(IOError) as exc_info:
        store.write({'default': {}})

    assert 'Access mode is "r"' in str(exc_info.value)

    store.close()

def test_json_storage_read_only_write_error_leaves_file_unchanged(db_path):
    """A failed write() leaves the existing file content intact."""
    data = {'default': {'1': {'name': 'John'}}}
    with open(db_path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle)

    store = JSONStorage(db_path, access_mode='r')
    with pytest.raises(IOError):
        store.write({'default': {'2': {'name': 'Alice'}}})
    store.close()

    with open(db_path, encoding='utf-8') as handle:
        assert json.load(handle) == data

def test_json_storage_warns_for_write_access_mode(db_path):
    """An access mode other than r/rb/r+/rb+ triggers a UserWarning."""
    with pytest.warns(UserWarning, match='can cause data loss or corruption'):
        store = JSONStorage(db_path, access_mode='w')

    store.close()

def test_json_storage_warns_for_append_access_mode(tmp_path):
    """An append access mode also triggers the data-loss warning."""
    db_path = str(tmp_path / 'db.json')

    with pytest.warns(UserWarning, match='can cause data loss or corruption'):
        store = JSONStorage(db_path, access_mode='a')

    store.close()

def test_json_storage_write_access_mode_truncates_existing_file(db_path):
    """access_mode='w' empties an existing database file (and warns about it)."""
    with open(db_path, 'w', encoding='utf-8') as handle:
        json.dump({'default': {'1': {'name': 'John'}}}, handle)

    with pytest.warns(UserWarning):
        store = JSONStorage(db_path, access_mode='w')

    assert store.read() is None

    store.close()

def test_json_storage_does_not_warn_for_recommended_access_modes(db_path):
    """The recommended access modes 'r', 'r+' and 'rb'/'rb+' do not warn."""
    with open(db_path, 'w'):
        pass

    for mode in ('r', 'r+'):
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            store = JSONStorage(db_path, access_mode=mode)
            store.close()

        access_mode_warnings = [w for w in recorded if 'access_mode' in str(w.message)]
        assert access_mode_warnings == []

def test_json_storage_create_dirs_creates_missing_directories(tmp_path):
    """With create_dirs=True the parent directories of the database are created."""
    db_path = str(tmp_path / 'nested' / 'deeper' / 'db.json')

    store = JSONStorage(db_path, create_dirs=True)
    store.write({'default': {'1': {'name': 'John'}}})

    assert os.path.exists(db_path)
    assert store.read() == {'default': {'1': {'name': 'John'}}}

    store.close()

def test_json_storage_raises_without_create_dirs_when_directory_missing(tmp_path):
    """Without create_dirs a missing parent directory makes creation fail."""
    db_path = str(tmp_path / 'missing' / 'db.json')

    with pytest.raises(FileNotFoundError):
        JSONStorage(db_path)

def test_json_storage_r_plus_mode_supports_read_and_write(db_path):
    """An explicitly requested 'r+' access mode allows both writing and reading."""
    data = {'default': {'1': {'name': 'John'}}}

    store = JSONStorage(db_path, access_mode='r+')
    store.write(data)

    assert store.read() == data

    store.close()

def test_json_storage_binary_read_mode_reads_existing_file(db_path):
    """The access mode 'rb' can be used to read an existing database file."""
    data = {'default': {'1': {'name': 'John'}}}

    writer = JSONStorage(db_path)
    writer.write(data)
    writer.close()

    store = JSONStorage(db_path, access_mode='rb')

    assert store.read() == data

    store.close()

def test_json_storage_read_returns_fresh_data_on_every_call(storage):
    """read() re-reads the file, so the cursor position of a previous call is irrelevant."""
    data = {'default': {'1': {'name': 'John'}}}
    storage.write(data)

    first = storage.read()
    first['default']['1']['name'] = 'mutated'

    assert storage.read() == data

def test_json_storage_write_flushes_data_to_disk(db_path):
    """write() flushes and fsyncs the file, so its content is visible to other handles."""
    data = {'default': {'1': {'name': 'John'}}}

    store = JSONStorage(db_path)
    store.write(data)

    with open(db_path, encoding='utf-8') as handle:
        assert json.load(handle) == data

    store.close()

def test_json_storage_write_with_non_serializable_data_raises_type_error(db_path):
    """Data that json cannot serialise raises TypeError and leaves the file untouched."""
    data = {'default': {'1': {'name': 'John'}}}

    store = JSONStorage(db_path)
    store.write(data)

    with pytest.raises(TypeError):
        store.write({'default': {'1': {'value': object()}}})

    assert store.read() == data

    store.close()

def test_json_storage_close_closes_the_file_handle(storage):
    """After close() the underlying file handle is closed and cannot be used anymore."""
    storage.write({'default': {'1': {'name': 'John'}}})

    storage.close()

    with pytest.raises(ValueError, match='closed file'):
        storage.read()

def test_json_storage_write_after_close_raises_value_error(storage):
    """Writing to a closed storage fails with a ValueError."""
    storage.close()

    with pytest.raises(ValueError, match='closed file'):
        storage.write({'default': {}})

def test_json_storage_close_can_be_called_twice(storage):
    """close() is safe to call more than once."""
    storage.close()

    storage.close()
