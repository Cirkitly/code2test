# Real-model run against `inflection` 0.5.1

Goal: run code2test end to end on a real open-source library with a real LLM
(`CODE2TEST_MODEL=openai:gpt-4o-mini`) and record what it produces.

**Status: blocked. The OpenAI API rejected the configured `OPENAI_API_KEY`, so no
tests were generated.** The attempt did expose a code2test bug, which is fixed
below. The evidence sections are still to be filled in once a working key is
available.

## Setup

- code2test: `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`. The
  existing suite passed (79 tests).
- Target: `inflection==0.5.1` sdist (`pip download --no-deps --no-binary :all:`),
  unpacked to a scratch directory outside the repo. The upstream
  `test_inflection.py` was moved out so the generated suite starts from nothing.
  `inflection/__init__.py` is 426 lines.
- Command, run in the target directory:

  ```
  CODE2TEST_MODEL=openai:gpt-4o-mini code2test test --auto --report all -v .
  ```

## What happened

Static analysis worked. It found **14 components** in `inflection/__init__.py` and
extracted 14 intents from docstrings and signatures (average confidence 96%; no
LLM needed for this step).

Every test-generation request to `POST https://api.openai.com/v1/responses` then
returned **HTTP 401 `invalid_api_key`**. A direct `GET /v1/models` with the same
key also returns 401 `invalid_api_key`, so the key is the cause, not code2test or
the network proxy. The key is set (125 characters), but its prefix doesn't look
like a standard OpenAI key, so it may belong to another provider.

## Bug found: an auth failure looked like a successful run

Before the fix, each of the 14 per-component LLM calls logged an error and
returned an empty result. The CLI then printed a normal summary and **exited 0**:

```
│ Total Components │ 14    │
│ Tests Generated  │ 0     │
│ Test Files       │ 0     │
│ Verified         │ 0     │
│ Avg Confidence   │ 96%   │
✓ Generated 0 tests in 0 files
✓ HTML report generated: tests/reports/report.html
✓ JSON report generated: tests/reports/report.json
```

The agents swallow per-component LLM errors so that one bad component doesn't
sink the whole run. A rejected key or an unknown model fails every call the same
way, though, so swallowing it hides a broken setup. In CI this would pass while
generating nothing.

**Fix** (`code2test/agents/errors.py`): `raise_if_fatal()` re-raises HTTP 401,
403 and 404 from the model provider as `ModelAccessError`. It runs first in every
place that falls back after an LLM error: test generation, integration-test
generation, test repair, intent inference and diagnosis (in the agents and in
`core/generator.py`). Other errors, such as 429s after retries, 5xx responses and
malformed output, still fall back per component as before.

After the fix, the same run fails fast with exit code 1 and doesn't write any
tests or reports:

```
✓ Found 14 components
✗ Generation failed: The model provider rejected the request (HTTP 401). Check
the API key and CODE2TEST_MODEL. Details: status_code: 401, model_name:
gpt-4o-mini, body: {'message': 'Incorrect API key provided: sk-… You can find
your API key at https://platform.openai.com/account/api-keys.', 'type':
'invalid_request_error', 'code': 'invalid_api_key', 'param': None}
```

Regression test: `tests/test_cli.py::test_rejected_api_key_fails_the_run`. It
fails on the old code (exit code 0) and passes with the fix. The full suite
passes (80 tests).

## Still to do

Rerun the command above with a valid OpenAI key, then `code2test verify tests/`,
and record:

- the number of test files and test cases generated
- how many were verified, repaired, kept as xfail (possible bugs) or dropped
- the `code2test verify` result and sample generated files
