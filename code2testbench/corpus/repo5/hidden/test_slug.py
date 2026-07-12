"""Hidden ground-truth tests for corpus/repo5/slug.slugify."""

from __future__ import annotations
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "code"))

import pytest
from slug import slugify


def test_basic_slugify():
    assert slugify("Hello World") == "hello-world"


def test_lowercases():
    assert slugify("HELLO WORLD") == "hello-world"


def test_consecutive_separators_collapse():
    assert slugify("foo---bar") == "foo-bar"


def test_strips_leading_trailing():
    assert slugify("---foo---") == "foo"


def test_empty_after_separators():
    assert slugify(" ") == ""


def test_already_slug():
    assert slugify("foo-bar-baz") == "foo-bar-baz"


def test_numbers_kept():
    assert slugify("Item 42") == "item-42"


def test_rejects_non_string():
    with pytest.raises(TypeError):
        slugify(None)  # type: ignore[arg-type]
