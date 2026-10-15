import os
import pytest
from tinydb.storages import touch, JSONStorage

@pytest.fixture
def db_path(tmp_path):
    """Path (as str) of a database file directly inside the temporary directory."""
    return str(tmp_path / 'db.json')

@pytest.fixture
def nested_db_path(tmp_path):
    """Path (as str) of a database file inside nested directories that do not exist yet."""
    return str(tmp_path / 'level1' / 'level2' / 'db.json')

@pytest.fixture
def existing_file(tmp_path):
    """An already existing file with content that must survive touch()."""
    path = tmp_path / 'existing.json'
    path.write_text('{"keep": {"me": true}}', encoding='utf-8')
    return str(path)

def test_touch_creates_file_in_existing_directory(db_path):
    """The primary use case: a missing file is created in an existing directory."""
    assert not os.path.exists(db_path)

    touch(db_path, create_dirs=False)

    assert os.path.exists(db_path)
    assert os.path.isfile(db_path)

def test_touch_creates_an_empty_file(db_path):
    """'a' mode only creates the file, it never writes data into it."""
    touch(db_path, create_dirs=False)

    assert os.path.getsize(db_path) == 0
    with open(db_path, 'r', encoding='utf-8') as handle:
        assert handle.read() == ''

def test_touch_returns_none(db_path):
    """The function has no return value, it only performs file system side effects."""
    result = touch(db_path, create_dirs=False)

    assert result is None
    assert os.path.isfile(db_path)

def test_touch_with_create_dirs_creates_all_missing_parent_directories(nested_db_path):
    """create_dirs=True creates every missing directory above the file."""
    base_dir = os.path.dirname(nested_db_path)
    assert not os.path.exists(base_dir)

    touch(nested_db_path, create_dirs=True)

    assert os.path.isdir(base_dir)
    assert os.path.isfile(nested_db_path)
    assert os.path.getsize(nested_db_path) == 0

def test_touch_with_create_dirs_true_is_noop_when_directories_already_exist(tmp_path):
    """An already existing directory must neither raise nor gain extra entries."""
    existing_dir = tmp_path / 'existing'
    existing_dir.mkdir()

    touch(str(existing_dir / 'db.json'), create_dirs=True)

    assert (existing_dir / 'db.json').is_file()
    assert sorted(entry.name for entry in existing_dir.iterdir()) == ['db.json']

def test_touch_preserves_contents_of_existing_file(existing_file):
    """touch() must not destroy data that is already stored in the file."""
    with open(existing_file, 'r', encoding='utf-8') as handle:
        before = handle.read()

    touch(existing_file, create_dirs=False)

    with open(existing_file, 'r', encoding='utf-8') as handle:
        assert handle.read() == before == '{"keep": {"me": true}}'

def test_touch_is_idempotent(existing_file):
    """Repeated calls neither raise nor append anything to the file."""
    touch(existing_file, create_dirs=True)
    touch(existing_file, create_dirs=True)
    touch(existing_file, create_dirs=False)

    with open(existing_file, 'r', encoding='utf-8') as handle:
        assert handle.read() == '{"keep": {"me": true}}'
    assert os.path.getsize(existing_file) == len('{"keep": {"me": true}}')

def test_touch_without_create_dirs_raises_when_parent_directory_is_missing(nested_db_path):
    """Without create_dirs the missing parent directory causes an OSError."""
    with pytest.raises(FileNotFoundError):
        touch(nested_db_path, create_dirs=False)

def test_touch_without_create_dirs_does_not_create_parent_directories(tmp_path):
    """After the failure nothing was written anywhere in the hierarchy."""
    nested = tmp_path / 'level1' / 'level2' / 'db.json'

    with pytest.raises(FileNotFoundError):
        touch(str(nested), create_dirs=False)

    assert not (tmp_path / 'level1').exists()
    assert list(tmp_path.iterdir()) == []

def test_touch_with_empty_path_raises_file_not_found_error():
    """An empty path is rejected by the operating system."""
    with pytest.raises(FileNotFoundError):
        touch('', create_dirs=False)

def test_touch_with_create_dirs_and_path_without_directory_component_raises_os_error(tmp_path, monkeypatch):
    """os.path.dirname('db.json') == '' cannot be created, so the call fails loudly."""
    monkeypatch.chdir(tmp_path)

    # FileNotFoundError (a subclass of OSError) is raised on POSIX systems
    with pytest.raises(OSError):
        touch('db.json', create_dirs=True)

    assert list(tmp_path.iterdir()) == []

def test_touch_raises_is_a_directory_error_when_path_is_a_directory(tmp_path):
    """A directory cannot be opened for appending."""
    directory = tmp_path / 'a_directory'
    directory.mkdir()

    with pytest.raises(IsADirectoryError):
        touch(str(directory), create_dirs=False)

    assert directory.is_dir()

def test_touch_accepts_path_like_objects(tmp_path):
    """A pathlib.Path is accepted just like a string path."""
    path = tmp_path / 'sub' / 'db.json'

    touch(path, create_dirs=True)

    assert path.is_file()
    assert path.read_text(encoding='utf-8') == ''

def test_touch_creates_readable_and_writable_file(db_path):
    """The created file must be usable for subsequent I/O."""
    touch(db_path, create_dirs=False)

    assert os.access(db_path, os.R_OK)
    assert os.access(db_path, os.W_OK)

    with open(db_path, 'w', encoding='utf-8') as handle:
        handle.write('{"a": {"b": 1}}')

    with open(db_path, 'r', encoding='utf-8') as handle:
        assert handle.read() == '{"a": {"b": 1}}'

def test_json_storage_can_use_file_created_by_touch(db_path):
    """The created file is directly usable as a JSONStorage backing file."""
    touch(db_path, create_dirs=False)
    assert os.path.isfile(db_path)

    storage = JSONStorage(db_path)
    # An empty file holds no data
    assert storage.read() is None
    storage.write({'default': {'value': 1}})
    storage.close()

    reopened = JSONStorage(db_path)
    assert reopened.read() == {'default': {'value': 1}}
    reopened.close()

def test_json_storage_with_create_dirs_after_touch_in_new_directory(nested_db_path):
    """touch() with create_dirs=True pre-creates the directory tree storages need."""
    touch(nested_db_path, create_dirs=True)
    assert os.path.isdir(os.path.dirname(nested_db_path))

    storage = JSONStorage(nested_db_path)
    assert storage.read() is None

    storage.write({'default': {'value': 42}})
    storage.close()

    reopened = JSONStorage(nested_db_path)
    assert reopened.read() == {'default': {'value': 42}}
    reopened.close()
