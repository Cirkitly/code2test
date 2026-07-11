"""Ground-truth tests for sample_repo/calc.

This file is hidden from the engine during intent inference and test
generation. The benchmark corpus vendors it as ground truth. It MUST be
executable against sample_repo/calc/ops.py without any code2test machinery.

Reasoning difficulty: every test here reflects a *behavioral* decision the
generator must make from intent alone. A "simple coverage" generator that
just exercises the public surface would not produce these specific
assertions.
"""

from __future__ import annotations

import os
import sys

import pytest

# Make the fixture repo importable as `calc`.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_FIXTURE_PARENT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _FIXTURE_PARENT not in sys.path:
    sys.path.insert(0, _FIXTURE_PARENT)

from calc.ops import (  # noqa: E402
    normalize_path,
    merge_config,
    retry,
    load_plugins,
    calculate_discount,
)


# -------- normalize_path --------

def test_normalize_path_joins_and_normpath():
    assert normalize_path("foo/bar", "/base") == "/base/foo/bar"


def test_normalize_path_collapses_dotdot():
    # normpath collapses .. AFTER joining, not before.
    assert normalize_path("../up", "/base/dir") == "/base/up"


def test_normalize_path_absolute_is_normpathed():
    assert normalize_path("/a/b/../c") == "/a/c"


def test_normalize_path_rejects_non_string():
    with pytest.raises(TypeError):
        normalize_path(123, "/")  # type: ignore[arg-type]


def test_normalize_path_rejects_empty_path():
    with pytest.raises(ValueError):
        normalize_path("", "/base")


# -------- merge_config --------

def test_merge_config_shallow_overrides_win():
    base = {"a": 1, "b": 2}
    over = {"b": 99, "c": 3}
    out = merge_config(base, over)
    assert out == {"a": 1, "b": 99, "c": 3}


def test_merge_config_lists_replace_not_append():
    base = {"xs": [1, 2, 3]}
    over = {"xs": [9]}
    out = merge_config(base, over)
    assert out["xs"] == [9]


def test_merge_config_nested_is_verbatim():
    base = {"nested": {"x": 1, "y": 2}}
    over = {"nested": {"x": 9}}
    out = merge_config(base, over)
    # shallow — y is dropped, x is replaced, no deep merge
    assert out == {"nested": {"x": 9}}


def test_merge_config_rejects_non_dict():
    with pytest.raises(TypeError):
        merge_config("nope", {})  # type: ignore[arg-type]


# -------- retry --------

def test_retry_succeeds_first_try():
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return 42
    assert retry(fn, attempts=3) == 42
    assert calls["n"] == 1


def test_retry_eventually_succeeds():
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("not yet")
        return "ok"
    assert retry(fn, attempts=5, delay=0) == "ok"
    assert calls["n"] == 3


def test_retry_raises_last_error_after_exhausting_attempts():
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        raise ValueError(f"attempt {calls['n']}")
    with pytest.raises(ValueError, match=r"attempt 3"):
        retry(fn, attempts=3, delay=0)
    assert calls["n"] == 3


def test_retry_rejects_invalid_attempts():
    with pytest.raises(ValueError):
        retry(lambda: 1, attempts=0)


def test_retry_rejects_non_callable():
    with pytest.raises(TypeError):
        retry("not a function")  # type: ignore[arg-type]


# -------- load_plugins --------

def test_load_plugins_returns_empty_for_missing_dir(tmp_path):
    assert load_plugins(str(tmp_path / "no-such-dir")) == []


def test_load_plugins_loads_present_modules(tmp_path):
    (tmp_path / "alpha.py").write_text("VALUE = 1\n")
    (tmp_path / "beta.py").write_text("VALUE = 2\n")
    mods = load_plugins(str(tmp_path))
    assert len(mods) == 2
    values = sorted(m.VALUE for m in mods)
    assert values == [1, 2]


def test_load_plugins_skips_dunder_files(tmp_path):
    (tmp_path / "_skip_me.py").write_text("VALUE = 'no'\n")
    (tmp_path / "real.py").write_text("VALUE = 'yes'\n")
    mods = load_plugins(str(tmp_path))
    assert len(mods) == 1
    assert mods[0].VALUE == "yes"


def test_load_plugins_propagates_import_errors(tmp_path):
    (tmp_path / "broken.py").write_text("raise = SyntaxError(\"broken\")\n")
    with pytest.raises(ImportError):
        load_plugins(str(tmp_path))


def test_load_plugins_rejects_non_string():
    with pytest.raises(TypeError):
        load_plugins(123)  # type: ignore[arg-type]


# -------- calculate_discount --------

def test_calculate_discount_no_code_returns_price_unchanged():
    assert calculate_discount(100.0) == 100.0
    assert calculate_discount(100.0, "") == 100.0


def test_calculate_discount_student_is_ten_percent():
    assert calculate_discount(100.0, "STUDENT") == 90.0


def test_calculate_discount_blackfriday_is_thirty_percent():
    assert calculate_discount(200.0, "BLACKFRIDAY") == 140.0


def test_calculate_discount_unknown_code_raises():
    with pytest.raises(ValueError):
        calculate_discount(50.0, "NOPE")


def test_calculate_discount_negative_price_raises():
    with pytest.raises(ValueError):
        calculate_discount(-1.0)


def test_calculate_discount_rejects_non_numeric():
    with pytest.raises(TypeError):
        calculate_discount("100")  # type: ignore[arg-type]


def test_calculate_discount_rejects_bool():
    with pytest.raises(ValueError):
        calculate_discount(True)  # type: ignore[arg-type]


def test_calculate_discount_rounds_to_two_dp():
    # $33.33 with WELCOME 5% = $31.66 exact; pick a value that requires rounding
    # 11.11 * 0.95 = 10.5545 -> 10.55
    assert calculate_discount(11.11, "WELCOME") == 10.55
