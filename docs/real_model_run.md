# Real-model run against `inflection` 0.5.1

code2test was run end to end on a real open-source library with a real LLM, with
no fake or scripted model anywhere in the loop.

- **Model:** MiniMax `MiniMax-M3.1-Flash-Preview`, through MiniMax's
  OpenAI-compatible API (`OPENAI_BASE_URL=https://api.minimax.io/v1`,
  `CODE2TEST_MODEL=openai-chat:MiniMax-M3.1-Flash-Preview`).
- **Target:** the `inflection==0.5.1` sdist from PyPI: `inflection/__init__.py`,
  426 lines. Its own `test_inflection.py` was moved out first, so the generated
  suite started from nothing.
- **Command**, run in the target directory:

  ```bash
  OPENAI_BASE_URL=https://api.minimax.io/v1 \
  CODE2TEST_MODEL=openai-chat:MiniMax-M3.1-Flash-Preview \
  code2test test --auto --report all .
  code2test verify tests/
  ```

## Result (final run)

| | |
|---|---|
| Components analyzed | 13 functions (12 public, plus `_irregular`) |
| Test files written | 13 (one per function, all 13 covered) |
| Test functions written | 277 (2,245 lines) |
| Test cases, including parametrized | 620 |
| `code2test verify tests/` | **620 / 620 passed, exit 0** |
| Tests dropped by the repair loop | 1 (`pluralize('leaf') == 'leaves'`: `inflection` returns `'leafs'`) |
| Wall time | about 5 minutes |

### Do the tests catch bugs?

Bugs were injected into `inflection` one at a time, and the generated suite was
run against each:

| Injected bug | Generated tests failing |
|---|---|
| `humanize` no longer strips a trailing `_id` | 11 |
| `dasherize` uses `+` instead of `-` | 14 |
| `ordinal(13)` returns `"rd"` instead of `"th"` | 6 |
| `ordinal` drops `abs()`, so negative numbers break | 6 |

Every injected bug was caught. With the original code restored, all 620 pass again.

## What the real model exposed (all fixed, with regression tests)

The first real runs failed in ways the scripted tests never covered:

1. **A rejected API key looked like a successful run.** Every call returned 401,
   but the CLI exited 0 with "Generated 0 tests". Auth and unknown-model errors
   (401/403/404) now stop the run with a clear message.
2. **Nested functions were treated as components.** `caseinsensitive` is defined
   inside `_irregular()`, so it can never be imported. The analyzer now skips
   functions nested in functions.
3. **Unimportable files were kept as `xfail`.** An import error at module level
   isn't covered by `xfail` and broke the whole suite. Files that can't be
   collected are now never kept, and the diagnosis prompt treats errors raised by
   the test itself (ImportError, SyntaxError, NameError) as a wrong test, not a
   code bug.
4. **Test names didn't match.** The model's `name` field often differs from the
   function it actually defines, so failures were never matched to a test and
   failing files were kept as "unverified". Results are now matched against the
   functions each test defines, and any file still failing is removed.
5. **Escaped code.** The model sometimes returned code with literal `\n`
   sequences, so a whole file failed with a SyntaxError. Escaped test code and
   fixtures are now unescaped when that makes them compile. Fixtures are also
   shown to, and repaired by, the fix step.
6. **Tests broke each other across files.** Tests for `_irregular()` register new
   words in `inflection`'s global state, which broke `pluralize` tests in the
   combined run. After per-file verification, the whole generated suite is now
   run together, and tests that only fail there are dropped.
7. **Unreadable file names.** Tests for `pkg/__init__.py` were named
   `test___init___humanize.py`. They are now `tests/pkg/test_humanize.py`.

| Run | Files | Test cases | `verify` |
|---|---|---|---|
| 1 (before fixes 2–7) | 12 written, 3 failing | — | collection error, exit 1 |
| 2 (fixes 2, 3, 7) | 11 | 676 / 680 | 4 failures, exit 1 |
| 3 (all fixes) | 13 | 620 / 620 | **exit 0** |

## Sample of the generated tests

`tests/inflection/test_ordinal.py` (start of file):

```python
import pytest
from inflection import ordinal

def test_ordinal_returns_correct_suffix_for_documented_examples():
    """The documented examples must all produce the documented suffixes."""
    assert ordinal(1) == "st"
    assert ordinal(2) == "nd"
    assert ordinal(1002) == "nd"
    assert ordinal(1003) == "rd"
    assert ordinal(-11) == "th"
    assert ordinal(-1021) == "st"


def test_ordinal_returns_string_type():
    """The happy path must yield a string, so it can be concatenated to a number."""
    result = ordinal(1)
    assert isinstance(result, str)
    assert result

@pytest.mark.parametrize(
    "number",
    [1, 21, 31, 41, 51, 61, 71, 81, 91, 101, 201, 301, 1001, 123451],
)
def test_ordinal_returns_first_suffix_for_numbers_ending_in_one(number):
    """Numbers whose last digit is 1 (and last two digits are not 11) get 'st'."""
    assert ordinal(number) == "st"
```

`tests/inflection/test_humanize.py` (start of file):

```python
import pytest
from inflection import humanize

@pytest.fixture
def sample_words():
    """Representative (input, expected output) pairs for the happy path."""
    return [
        ("employee_salary", "Employee salary"),
        ("author_id", "Author"),
        ("the_employee_salary", "The employee salary"),
        ("employee", "Employee"),
        ("Employee", "Employee"),
        ("EMPLOYEE_SALARY", "Employee salary"),
        ("employee_2_salary", "Employee 2 salary"),
        ("employee-salary", "Employee-salary"),
    ]

def test_humanize_replaces_underscores_with_spaces():
    """The core intent: underscores in a word become spaces."""
    assert humanize("employee_salary") == "Employee salary"

def test_humanize_matches_documented_example_employee_salary():
    """The docstring example ``humanize('employee_salary')`` is honoured."""
    assert humanize("employee_salary") == "Employee salary"

def test_humanize_matches_documented_example_author_id():
    """The docstring example ``humanize('author_id')`` is honoured."""
    assert humanize("author_id") == "Author"

def test_humanize_strips_trailing_id_suffix_from_multi_word_string():
    """A trailing ``"_id"`` is removed even when other underscores exist."""
    assert humanize("the_employee_id") == "The employee"

def test_humanize_strips_only_one_trailing_id_suffix():
    """Only a single trailing ``"_id"`` is removed, not repeated occurrences."""
    # "record_id_id" -> "record_id" -> "Record id"
    assert humanize("record_id_id") == "Record id"

def test_humanize_keeps_id_when_it_is_not_an_underscore_suffix():
    """``"id"`` without a leading underscore is a normal word, not a suffix."""
```
