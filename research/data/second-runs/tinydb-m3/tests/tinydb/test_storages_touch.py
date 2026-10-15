import os
import pytest
from tinydb.storages import touch

def test_touch_creates_new_file(tmp_path):
    """Verify the primary happy path: touch creates a file that doesn't exist yet."""
    path = tmp_path / "new_file.txt"
    # Sanity check: confirm the file does not exist before calling touch.
    assert not path.exists()

    touch(str(path), create_dirs=False)

    # The file must exist after touch.
    assert path.exists()
    assert path.is_file()

def test_touch_creates_an_empty_file(tmp_path):
    """Verify that the created file is empty (touch only creates, never writes)."""
    path = tmp_path / "empty.txt"

    touch(str(path), create_dirs=False)

    # 'a' mode opens the file without truncating it; for a brand-new
    # file the resulting size must be zero.
    assert path.stat().st_size == 0

def test_touch_does_not_modify_existing_file_contents(tmp_path):
    """Verify that touch does not modify the contents of an existing file."""
    path = tmp_path / "existing.txt"
    original_content = "pre-existing contents that must be preserved"
    path.write_text(original_content)

    touch(str(path), create_dirs=False)

    # Because the file is opened in 'a' (append) mode, existing contents
    # must remain untouched.
    assert path.read_text() == original_content

def test_touch_creates_missing_parent_directories_when_create_dirs_true(tmp_path):
    """Verify that touch creates missing parent directories when create_dirs=True."""
    path = tmp_path / "nested" / "subdir" / "file.txt"
    # Confirm the parent directory does not exist before calling touch.
    assert not path.parent.exists()

    touch(str(path), create_dirs=True)

    # Both the parent directory and the file itself should now exist.
    assert path.exists()
    assert path.parent.exists()
    assert path.parent.is_dir()

def test_touch_with_create_dirs_true_is_safe_when_parent_exists(tmp_path):
    """Verify that touch does not error when create_dirs=True but the parent already exists."""
    path = tmp_path / "file.txt"
    # The parent (tmp_path) already exists; this call must succeed.
    touch(str(path), create_dirs=True)

    assert path.exists()
    assert path.is_file()

def test_touch_raises_filenotfound_when_create_dirs_false_and_parent_missing(tmp_path):
    """Verify that touch raises FileNotFoundError when the parent directory is missing and create_dirs=False."""
    path = tmp_path / "missing_parent" / "file.txt"
    # Confirm the parent directory really does not exist beforehand.
    assert not path.parent.exists()

    # Without create_dirs, no parent directory is created, so opening
    # the file in 'a' mode must raise FileNotFoundError.
    with pytest.raises(FileNotFoundError):
        touch(str(path), create_dirs=False)

def test_touch_creates_deeply_nested_missing_directories(tmp_path):
    """Verify that touch can create deeply nested missing parent directories when create_dirs=True."""
    path = tmp_path / "a" / "b" / "c" / "d" / "file.txt"
    # Confirm none of the intermediate directories exist yet.
    assert not path.parent.exists()

    touch(str(path), create_dirs=True)

    assert path.exists()
    assert path.parent.exists()
    assert path.parent.is_dir()
