# Quickstart

This guide takes you from installation to a verified, generated test suite for your own Python project.

## 1. Install

Code2Test needs Python 3.12 or later.

```bash
git clone https://github.com/Cirkitly/code2test.git
cd code2test
pip install .
code2test --version
```

## 2. Choose a model

Set an API key and, optionally, the model. Any [pydantic-ai model string](https://ai.pydantic.dev/models/) works:

```bash
export ANTHROPIC_API_KEY=...
export CODE2TEST_MODEL=anthropic:claude-sonnet-5-5
```

For an OpenAI-compatible provider, set `OPENAI_BASE_URL` and use the `openai-chat:` prefix:

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.minimax.io/v1
export CODE2TEST_MODEL=openai-chat:MiniMax-M3.1-Flash-Preview
```

To check the installation without a key, use `CODE2TEST_MODEL=test`. It runs the pipeline with a placeholder model, and the tests it produces are discarded.

## 3. Generate tests

From the root of the project you want to test:

```bash
cd /path/to/your/project
code2test test --auto .
```

Code2Test infers an intent for each function and class, generates tests, runs them and repairs failures. It ends with a summary like this:

```text
Components                        13
Components with passing tests     13 (100%)
Tests generated                   302
Passed on first run               231 (76%)
Tests kept                        300
  of which xfail (possible bugs)    0
Tests dropped                     2
```

The tests are in `tests/`, one file per component. The same numbers are saved to `.code2test/metrics.json`.

To review intents and tests before they are saved, run `code2test test .` without `--auto`. For each component you can accept the intent, edit it, or skip the component; then you accept or skip its tests.

To test only part of a project, pass a file or directory, for example `code2test test --auto src/mypkg/utils.py`. Paths still resolve to the project root.

## 4. Check the result

```bash
code2test verify tests/
```

This runs the suite and exits with status 1 if any test fails. After you change the code, you can repair the generated tests:

```bash
code2test verify --diagnose tests/   # explain each failure
code2test verify --fix tests/        # repair generated tests that you have not edited
```

## 5. Review and correct intents

```bash
code2test intent show            # all intents
code2test intent show my_func    # one function or class
code2test intent edit my_func    # correct it; later runs reuse your version
```

## 6. Measure test quality

```bash
code2test benchmark .
```

This injects small bugs into the tested code one at a time and reports how many the generated tests catch. It also reports how often the diagnosis agent identifies the cause of a failure correctly. Your source files are restored after every injected bug.

## 7. Use it in CI

```bash
code2test test --auto --exit-code .
code2test verify tests/
```

See [`examples/ci`](../examples/ci) for GitHub Actions and GitLab CI configurations, and [architecture.md](architecture.md) for how the pipeline works.
