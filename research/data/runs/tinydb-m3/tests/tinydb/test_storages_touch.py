import os
import pytest
from tinydb.storages import touch

def test_touch_creates_file_when_missing(tmp_path):
    """A plain filename in an existing dir should be created by touch."""
    new_file = str(tmp_path / "new_file.txt")

    # Sanity check: file does not exist before calling touch
    assert not os.path.exists(new_file)

    touch(new_file, create_dirs=False)

    # After touch, the file should exist
    assert os.path.exists(new_file)
    assert os.path.isfile(new_file)


def test_touch_creates_empty_file(tmp_path):
    """A newly created file should have no content (open in append mode does not write)."""
    new_file = str(tmp_path / "empty.txt")

    touch(new_file, create_dirs=False)

    # The file exists and is empty
    assert os.path.getsize(new_file) == 0


def test_touch_preserves_existing_content(tmp_path):
    """If the file already exists, touch must not modify its contents (append mode)."""
    existing = tmp_path / "existing.txt"
    existing.write_text("hello world")
    path_str = str(existing)

    touch(path_str, create_dirs=False)

    # Content should be preserved untouched
    assert existing.read_text() == "hello world"


def test_touch_with_create_dirs_creates_deeply_nested_parents(tmp_path):
    """When create_dirs=True, all missing parent directories should be created recursively."""
    nested_file = str(tmp_path / "a" / "b" / "c" / "d" / "deep.txt")
    base_dir = os.path.dirname(nested_file)

    # Sanity check: parent path does not exist yet
    assert not os.path.exists(base_dir)

    touch(nested_file, create_dirs=True)

    # All parent dirs should now exist, and the file should be created
    assert os.path.isdir(base_dir)
    for parent in [tmp_path / "a", tmp_path / "a" / "b", tmp_path / "a" / "b" / "c"]:
        assert os.path.isdir(parent)
    assert os.path.isfile(nested_file)


def test_touch_with_create_dirs_noop_when_parent_exists(tmp_path):
    """When create_dirs=True and the parent already exists, touch should still succeed."""
    parent = tmp_path / "already_here"
    parent.mkdir()
    nested_file = str(parent / "child.txt")

    touch(nested_file, create_dirs=True)

    # Parent is untouched and child file is created
    assert os.path.isdir(parent)
    assert os.path.isfile(nested_file)


def test_touch_missing_parent_without_create_dirs_raises(tmp_path):
    """When create_dirs=False and the parent directory is missing, open() should raise FileNotFoundError."""
    nested_file = str(tmp_path / "missing_parent" / "child.txt")

    with pytest.raises(FileNotFoundError):
        touch(nested_file, create_dirs=False)

    # Neither the parent nor the file should have been created
    assert not os.path.exists(nested_file)
    assert not os.path.isdir(os.path.dirname(nested_file))

