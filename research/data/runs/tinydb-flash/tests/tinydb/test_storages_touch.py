import io
import json
import os
import warnings
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pytest
from tinydb.storages import touch, JSONStorage

def test_touch_creates_missing_file(tmp_path):
    """touch should create the file when it does not exist yet."""
    target = tmp_path / 'new_file.txt'
    assert not target.exists()

    touch(str(target), False)

    assert target.exists()
    assert target.is_file()

def test_touch_leaves_existing_file_untouched(tmp_path):
    """Opening in append mode without writing must not alter existing content."""
    target = tmp_path / 'existing.txt'
    target.write_text('original content', encoding='utf-8')

    touch(str(target), False)

    assert target.read_text(encoding='utf-8') == 'original content'

def test_touch_on_existing_file_is_idempotent(tmp_path):
    """Repeated touch calls neither raise nor destroy the file."""
    target = tmp_path / 'repeat.txt'
    touch(str(target), False)
    touch(str(target), False)
    touch(str(target), False)

    assert target.exists()
    assert target.read_text(encoding='utf-8') == ''

def test_touch_creates_new_empty_file(tmp_path):
    """touch creates the file but never writes to it, so it starts empty."""
    target = tmp_path / 'empty.txt'

    touch(str(target), False)

    assert target.read_text(encoding='utf-8') == ''
    assert target.stat().st_size == 0

def test_touch_creates_missing_parent_directories_when_requested(tmp_path):
    """create_dirs=True creates every missing parent directory of the path."""
    target = tmp_path / 'nested' / 'deeper' / 'data.txt'
    assert not target.parent.exists()

    touch(str(target), True)

    assert target.parent.is_dir()
    assert target.exists()
    assert target.is_file()

def test_touch_does_not_create_directories_when_disabled(tmp_path):
    """Without create_dirs the parent directory is left untouched and touch fails."""
    target = tmp_path / 'missing_dir' / 'data.txt'

    with pytest.raises(FileNotFoundError):
        touch(str(target), False)

    assert not target.parent.exists()
    assert not target.exists()

def test_touch_creates_file_in_existing_directory(tmp_path):
    """create_dirs=True must not fail when the parent directory is already present."""
    existing_dir = tmp_path / 'already_there'
    existing_dir.mkdir()
    target = existing_dir / 'file.txt'

    touch(str(target), True)

    assert existing_dir.is_dir()
    assert target.exists()
    assert target.read_text(encoding='utf-8') == ''

def test_touch_creates_directories_along_existing_path(tmp_path):
    """Only the absent directories are created; existing ones are reused."""
    (tmp_path / 'level1').mkdir()
    target = tmp_path / 'level1' / 'level2' / 'level3' / 'data.json'

    touch(str(target), True)

    assert (tmp_path / 'level1' / 'level2' / 'level3').is_dir()
    assert target.exists()

def test_touch_with_create_dirs_on_existing_file_and_missing_dirs_preserves_content(tmp_path):
    """The create_dirs branch must not interfere with an already existing file."""
    target = tmp_path / 'db.json'
    target.write_text('{"_default": {}}', encoding='utf-8')

    touch(str(target), True)

    assert target.read_text(encoding='utf-8') == '{"_default": {}}'

def test_touch_with_create_dirs_true_and_no_directory_component_raises(tmp_path, monkeypatch):
    """dirname('file.txt') is '', and os.path.exists('') is False -> os.makedirs('') raises."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        touch('file.txt', True)

    assert not (tmp_path / 'file.txt').exists()

def test_touch_with_create_dirs_false_and_no_directory_component_creates_file(tmp_path, monkeypatch):
    """Without the dirname branch, a relative bare filename is created in the cwd."""
    monkeypatch.chdir(tmp_path)

    touch('data.json', False)

    assert (tmp_path / 'data.json').exists()
    assert (tmp_path / 'data.json').read_text(encoding='utf-8') == ''

def test_touch_returns_none(tmp_path):
    """The function performs the side effect and yields None."""
    target = tmp_path / 'ret.txt'

    result = touch(str(target), False)

    assert result is None
    assert target.exists()

@pytest.mark.skipif(os.name == 'nt' or os.geteuid() == 0,
                    reason='Permission checks are unreliable on Windows or for root')
def test_touch_raises_on_unwritable_directory(tmp_path):
    """Without write permission on the parent, open() in append mode fails."""
    locked = tmp_path / 'locked'
    locked.mkdir()
    os.chmod(locked, 0o500)

    try:
        with pytest.raises(PermissionError):
            touch(str(locked / 'new.txt'), False)
    finally:
        os.chmod(locked, 0o700)

    assert not (locked / 'new.txt').exists()

def test_touch_raises_when_path_is_a_directory(tmp_path):
    """open(dir, 'a') is not permitted on POSIX and raises IsADirectoryError."""
    a_directory = tmp_path / 'a_directory'
    a_directory.mkdir()

    with pytest.raises(IsADirectoryError):
        touch(str(a_directory), False)

    assert a_directory.is_dir()

def test_touch_raises_isadirectoryerror_with_create_dirs_true_on_directory_path(tmp_path):
    """create_dirs=True still fails with IsADirectoryError when path names a directory."""
    a_directory = tmp_path / 'dir_target'
    a_directory.mkdir()

    with pytest.raises(IsADirectoryError):
        touch(str(a_directory), True)

    assert a_directory.is_dir()

def test_touch_missing_directories_with_create_dirs_true_creates_full_tree(tmp_path):
    """os.makedirs is applied to the whole dirname, creating every intermediate level."""
    target = tmp_path / 'a' / 'b' / 'c' / 'd' / 'e' / 'table.json'

    touch(str(target), True)

    for level in ('a', 'a/b', 'a/b/c', 'a/b/c/d', 'a/b/c/d/e'):
        assert (tmp_path / level).is_dir()
    assert target.is_file()

def test_touch_creates_file_suitable_for_json_storage(tmp_path):
    """touch's output is an existing, writable file that JSONStorage can open."""
    db_file = tmp_path / 'db' / 'db.json'

    touch(str(db_file), True)

    storage = JSONStorage(str(db_file))
    try:
        assert storage.read() is None
        storage.write({'_default': {}})
        storage.close()
    finally:
        if not storage._handle.closed:
            storage.close()

    assert db_file.exists()
    assert '_default' in json.loads(db_file.read_text(encoding='utf-8'))

def test_touch_does_not_truncate_existing_json_database_file(tmp_path):
    """touch on an existing JSON db file leaves its serialized contents intact."""
    db_file = tmp_path / 'db.json'
    db_file.write_text(json.dumps({'_default': {}}), encoding='utf-8')

    touch(str(db_file), True)

    assert json.loads(db_file.read_text(encoding='utf-8')) == {'_default': {}}

def test_touch_creates_readable_and_writable_file(tmp_path):
    """The created file behaves like a normal empty file for the caller."""
    target = tmp_path / 'usable.txt'

    touch(str(target), False)

    with open(target, 'r') as handle:
        assert handle.read() == ''

    with open(target, 'a') as handle:
        handle.write('hello')

    assert target.read_text(encoding='utf-8') == 'hello'
