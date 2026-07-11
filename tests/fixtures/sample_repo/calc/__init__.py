"""Code2Test fixture repo: sample_repo/calc.

Five functions with deliberately ambiguous intent. The ambiguity is the
point: success of intent extraction is measured against these ground-truth
behaviors by tests/fixtures/sample_repo/calc_hidden/test_ops.py.

If a future engine produces tests that consistently pass for these five, we
have a bug in either the test or the intent extraction; the purpose is to
exercise reasoning, not docstring regurgitation.

This is the M1C.1 fixture. The hidden test file in calc_hidden/ is the
ground truth and is the artifact the M1D benchmark corpus reproduces.
"""

from .ops import (
    normalize_path,
    merge_config,
    retry,
    load_plugins,
    calculate_discount,
)

__all__ = [
    "normalize_path",
    "merge_config",
    "retry",
    "load_plugins",
    "calculate_discount",
]
