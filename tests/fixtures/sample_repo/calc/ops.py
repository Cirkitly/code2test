"""Five functions with ambiguous intent.

The author documents behavior with one-line docstrings that say *what*, but
not *which* variant of *what*. A generator that produces passing tests for
this file must have reasoned about the variants in the docstrings below.

These five are deliberately hard at the intent layer. The cost of a wrong
intent here is a battery of fake-passing tests that don't actually constrain
behavior — exactly the failure mode code2test is supposed to prevent.

Hidden ground-truth tests live in tests/fixtures/sample_repo/calc_hidden/.
That file is what the benchmark corpus eventually vendors.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import time
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def normalize_path(path: str, base: str = "/") -> str:
    """Resolve a path against a base directory.

    Variants this could mean:
      - os.path.join, leaving '..' and '.' intact
      - os.path.normpath after join
      - pathlib.Path.resolve() which produces absolute paths
    Implementation choice: normpath after join. Does NOT canonicalize or
    follow symlinks (intentionally cheap).
    """
    if not isinstance(path, str):
        raise TypeError(f"path must be a string, got {type(path).__name__}")
    if not isinstance(base, str):
        raise TypeError(f"base must be a string, got {type(base).__name__}")
    if not base or not path:
        raise ValueError("path and base must be non-empty")
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(base, path))


def merge_config(defaults: dict, overrides: dict) -> dict:
    """Combine default and override configurations.

    Variants:
      - shallow merge (overrides win)
      - recursive merge (nested dicts merged)
      - keys collide: list vs scalar
    Implementation: shallow merge with overrides winning. Lists are NOT
    appended; the override list fully replaces the default list.

    Nested values are kept verbatim. The function does NOT deep-copy inputs.
    """
    if not isinstance(defaults, dict):
        raise TypeError("defaults must be a dict")
    if not isinstance(overrides, dict):
        raise TypeError("overrides must be a dict")
    out = dict(defaults)
    out.update(overrides)
    return out


def retry(callable_: Callable[[], T], attempts: int = 3, delay: float = 0.1) -> T:
    """Run a callable with retries on failure.

    Variants:
      - on what exception(s): all, specific, none
      - delay strategy: constant, exponential
      - max-delay cap
      - re-raise vs return sentinel
    Implementation: retries on any exception up to ``attempts`` times with a
    constant ``delay`` between attempts. Re-raises the last exception on
    final failure (does NOT swallow).
    """
    if not callable(callable_):
        raise TypeError("callable_ must be callable")
    if not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")
    if delay < 0:
        raise ValueError("delay must be non-negative")

    last_err: Exception | None = None
    for i in range(attempts):
        try:
            return callable_()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if i < attempts - 1:
                time.sleep(delay)
    assert last_err is not None
    raise last_err


def load_plugins(directory: str) -> list:
    """Discover and import plugin modules from a directory.

    Variants:
      - naming convention: plugins must be named like `plugin_*.py`
      - failure mode: raise if a plugin is broken, or skip with warning
    Implementation: discovers `*.py` files (NOT just `plugin_*`). Imports
    each. Re-raises the first import error encountered.
    """
    if not isinstance(directory, str):
        raise TypeError("directory must be a string")

    p = Path(directory)
    if not p.is_dir():
        return []
    loaded = []
    for entry in sorted(p.glob("*.py")):
        if entry.name.startswith("_"):
            continue
        # module name derived from filename relative to a synthetic root.
        # We use a fixed prefix 'sample_plugins' to keep things simple.
        mod_name = f"sample_plugins.{entry.stem}"
        # Stale stubs in a real engine would resolve through pkgutil; here we
        # surface the import error faithfully.
        spec = importlib.util.spec_from_file_location(mod_name, entry)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load plugin {entry}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            raise ImportError(f"failed to import plugin {entry}: {exc}") from exc
        loaded.append(module)
    return loaded


_DISCOUNT_CODES = {
    "STUDENT": 0.10,    # 10% off
    "WELCOME": 0.05,    # 5% off
    "BLACKFRIDAY": 0.30,  # 30% off
}


def calculate_discount(price: float, code: str = "") -> float:
    """Apply a discount code to a price.

    Variants:
      - unknown codes raise vs are silently ignored
      - negative prices raise vs return price unchanged
      - apply at most one code or stack
      - rounding
    Implementation: unknown codes are an error (ValueError). Negative input
    also raises. One code at a time; no stacking. Rounded to 2dp.
    """
    if not isinstance(price, (int, float)):
        raise TypeError("price must be numeric")
    if isinstance(price, bool) or price < 0:
        raise ValueError(f"price must be a non-negative number, got {price!r}")
    if code:
        if code not in _DISCOUNT_CODES:
            raise ValueError(f"unknown discount code: {code!r}")
        rate = _DISCOUNT_CODES[code]
    else:
        rate = 0.0
    discounted = price * (1.0 - rate)
    return round(discounted, 2)
