"""Hidden ground-truth tests for corpus/repo2/listutils.chunk."""

from __future__ import annotations
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "code"))

import pytest
from listutils import chunk


def test_chunk_even():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_chunk_uneven():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_empty():
    assert chunk([], 3) == []


def test_chunk_size_one():
    assert chunk([1, 2], 1) == [[1], [2]]


def test_chunk_rejects_zero_size():
    with pytest.raises(ValueError):
        chunk([1, 2], 0)


def test_chunk_rejects_negative_size():
    with pytest.raises(ValueError):
        chunk([1, 2], -1)


def test_chunk_rejects_non_list():
    with pytest.raises(TypeError):
        chunk("abc", 2)  # type: ignore[arg-type]
