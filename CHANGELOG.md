# Changelog

All notable changes to Code2Test are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-15

First release: an alpha for Python projects.

### Added

- `code2test test` generates a pytest suite for existing Python code. For each top-level function and class it infers an intent from the docstring, type hints, naming and call sites, and asks the model when that inference is uncertain. It then generates tests, runs them, repairs failures from their pytest output (up to two rounds), and diagnoses tests that still fail as a wrong test, a code bug or a wrong intent. Suspected code bugs are kept as `xfail` tests that name the bug; everything else that fails is dropped, and a whole-suite run removes tests that only fail alongside others. The written suite therefore always passes.
  - Interactive by default: review, edit or skip each intent and set of tests. `--auto` runs without prompts, and `--exit-code` makes it usable in CI.
- `code2test verify` runs the generated suite; `--diagnose` explains failures and `--fix` repairs generated tests after the code changed, without touching tests you edited.
- `code2test benchmark` measures the suite: the share of injected bugs it catches (mutation score), and how often the diagnosis names the right cause of a failure whose cause is known.
- `code2test report coverage` and `code2test test --report html|json|all` report, per component, the behaviors its passing tests check, the injected bugs they catch and the diagnostic accuracy.
- `code2test intent show|edit|export` to review and correct intents. Edited intents are never overwritten by later runs.
- `code2test init` saves project defaults for `code2test test`: confidence threshold, output directory and exclude patterns.
- `code2test config set|show|validate` stores the API key and model; `validate` sends the model one test request.
- Works with any model pydantic-ai supports, including OpenAI-compatible endpoints through `OPENAI_BASE_URL`.

### Measured

On inflection 0.5.1 and TinyDB 4.8.2, with their own tests removed, using MiniMax `MiniMax-M3.1-Flash-Preview` and `MiniMax-M3`, two runs each:

| Measure | Result | Target |
| --- | --- | --- |
| Components with passing tests | 96–100% | 70% |
| Generated tests passing before any repair | 84–99% | 80% |
| Injected bugs caught | 59–84% | |
| Diagnosis correct on failures with a known cause | 97–100% | 75% |

One run kept a test as an expected failure that exposes a real defect in inflection 0.5.1: `singularize("campuses")` returns `"campuse"`. Details are in the README and in [`research/`](research/).

### Known limitations

- Python only; files in other languages are analyzed for the dependency graph but get no tests.
- Each run sends source code to the configured model provider and costs model calls.
- Evaluated on two small libraries with one provider's models; large codebases and other models are not yet measured.
- Not yet available: Markdown reports, and regenerating tests only for code that changed.

[0.1.0]: https://github.com/Cirkitly/code2test/releases/tag/v0.1.0
