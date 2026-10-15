# Implementation Status

Code2Test grew out of CodeWiki, a repository documentation generator. Its dependency analyzer was kept and test generation was built on top; CodeWiki's documentation generator and web app have been removed. This page lists what v1 does, what exists in the code but is not used by the v1 pipeline, and what is planned. The original plan and its success criteria are in [proposal.md](proposal.md).

## Scope of v1

Python only. Test generation, verification and repair target pytest. Files in other languages are part of the dependency graph, but their components get no intents or tests, and `code2test test` says so when it skips them.

## Done

**Pipeline** (see [architecture.md](architecture.md))
- [x] Dependency analysis of the repository; top-level Python functions and classes become components
- [x] Static intent extraction with confidence scoring (docstrings, type hints, naming conventions, call sites, complexity)
- [x] LLM re-inference of intents below the confidence threshold
- [x] Intent storage in SQLite; edited intents are never overwritten
- [x] Test generation with the intent, import line, module imports, related API and source
- [x] Per-file execution with pytest, isolated from the user's working directory
- [x] Repair from pytest output, up to two rounds
- [x] Diagnosis of remaining failures as wrong test, code bug or wrong intent; suspected bugs kept as `xfail`
- [x] Whole-suite check that drops tests failing only alongside others
- [x] Reuse of already verified tests on re-runs in `--auto` mode
- [x] Provider errors 401, 403 and 404 stop the run

**Commands**
- [x] `test`, interactive and `--auto`, with `--exit-code` for CI and `--report html|json|all`
- [x] `verify`, with `--diagnose` and `--fix` (only for generated files not edited since)
- [x] `intent show|edit|export`
- [x] `benchmark`: mutation score and diagnosis accuracy on failures of known cause
- [x] `report summary`: intents by confidence
- [x] `report coverage` and the `--report` output: behavioral coverage (behaviors tested, mutants caught) and diagnostic accuracy per component
- [x] `init`: saves project defaults for `test` (confidence threshold, output directory, exclude patterns) in `.code2test/config.json`
- [x] `config set|show|validate`: API key and model; `validate` sends the model one test request

**Measurement and evaluation**
- [x] Run metrics in `.code2test/metrics.json`: acceptance rate, first-run pass rate, repairs, xfails, drops, reused and skipped components
- [x] Evaluation on inflection and TinyDB with two models; results in the [README](../README.md#results) and [research/](../research/)

**Project**
- [x] CI on every push and pull request: tests on Python 3.12 and 3.13, ruff lint and format check
- [x] CI examples for GitHub Actions and GitLab CI ([examples/ci](../examples/ci))
- [x] Release 0.1.0: [CHANGELOG](../CHANGELOG.md), PyPI publishing from GitHub releases (`.github/workflows/publish.yml`)

## In the code but not used by the v1 pipeline

- `code2test/adapters/` (pytest, Jest and JUnit adapters) and `code2test/core/templates.py`: the pipeline generates tests with the test agent and runs them with `core/verifier.py` instead.
- `code2test/core/intent_analyzers/` for JavaScript and Java: never reached, because `code2test test` passes only Python components to the pipeline.
- `TestAgent.generate_integration_tests`: not called by any command.

## Not done

- [ ] Markdown run reports
- [ ] Incremental generation for changed files only (re-runs reuse verified tests per component, whether or not the code changed)
- [ ] An experiment on code with known bugs, to test whether intent-first generation avoids locking bugs into the suite (see the paper's Discussion)

## Not planned

- **Intent Alignment Score** (proposal Section 7.1). The proposal defines it as the semantic similarity between a test's assertions and the intent text. That measures shared wording, not whether a test checks the intent: a test asserting a wrong value scores like one asserting the right value, and because most intents are docstring summaries, the score would mostly compare tests with docstrings. What it was meant to show is covered by `code2test report coverage`: the behaviors each component's passing tests check, shown next to its intent, the share of injected bugs those tests catch, and diagnostic accuracy. A model-judged alignment check, validated against hand-labelled tests, could replace it in future work.

## Post-v1

- [ ] Jest test generation and execution for JavaScript and TypeScript
- [ ] JUnit 5 test generation and execution for Java
