# Code2Test

[![CI](https://github.com/Cirkitly/code2test/actions/workflows/ci.yml/badge.svg)](https://github.com/Cirkitly/code2test/actions/workflows/ci.yml)

Code2Test generates pytest test suites for existing Python code using a large language model (LLM). Before it writes any test, it infers and records what each function and class is meant to do. It then runs every generated test, repairs failing tests from their pytest output, and writes only tests that pass. The one exception is a test that points at a likely bug, which is kept and marked as an expected failure.

On two open-source libraries whose own tests were removed, Code2Test produced passing tests for 96% to 100% of functions and classes, and the suites caught 59% to 78% of injected bugs ([results](#results)). A paper describing the tool and these results is in [`research/`](research/).

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Choosing a model](#choosing-a-model)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Commands](#commands)
- [Files Code2Test writes](#files-code2test-writes)
- [Results](#results)
- [Limitations](#limitations)
- [Development](#development)
- [License](#license)

## Requirements

- Python 3.12 or later
- An API key for an LLM provider supported by [pydantic-ai](https://ai.pydantic.dev/models/), or any OpenAI-compatible endpoint
- The code under test must be importable from the repository root or from `src/`

## Installation

```bash
pip install code2test
code2test --version
```

To install a release straight from GitHub instead, use `pip install git+https://github.com/Cirkitly/code2test@v0.1.0`. To work on Code2Test itself, see [Development](#development). Changes in each release are listed in [CHANGELOG.md](CHANGELOG.md).

## Choosing a model

Code2Test picks the model in this order:

1. The `CODE2TEST_MODEL` environment variable, which takes any pydantic-ai model string.
2. The main model saved with `code2test config set --main-model ...`.
3. Azure OpenAI, when `AZURE_OPENAI_DEPLOYMENT` and `AZURE_OPENAI_ENDPOINT` are set.
4. Gemini, when the API key saved with `code2test config set --api-key` is a Google key.
5. `openai:gpt-4o-mini` otherwise.

Each provider reads its usual key variable, for example `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. A key saved with `code2test config set --api-key` is stored in the system keychain and exported as `OPENAI_API_KEY` (and as the Google key variables) when Code2Test runs, replacing any value already in the environment.

```bash
export ANTHROPIC_API_KEY=...
export CODE2TEST_MODEL=anthropic:claude-sonnet-5-5
```

Any OpenAI-compatible provider works through `OPENAI_BASE_URL` and the `openai-chat:` prefix. For example, MiniMax:

```bash
export OPENAI_API_KEY=...                         # the provider's key
export OPENAI_BASE_URL=https://api.minimax.io/v1
export CODE2TEST_MODEL=openai-chat:MiniMax-M3.1-Flash-Preview
```

`CODE2TEST_MODEL=test` runs the whole pipeline offline with a placeholder model. Use it to check your setup without an API key; it does not produce useful tests.

## Quick start

Run these from the root of the project you want to test:

```bash
code2test test --auto .     # generate, run and repair tests
code2test verify tests/     # run the generated suite; exits 1 on any failure
code2test benchmark .       # measure how many injected bugs the tests catch
```

Without `--auto`, `code2test test` runs interactively. It shows each inferred intent and the generated tests, and asks before saving.

## How it works

1. **Analyze.** Code2Test builds a dependency graph of the repository. Each top-level Python function and class becomes a component. Functions nested inside other functions are skipped, because tests cannot import them.
2. **Infer intent.** Each component gets a one-sentence intent and a confidence score.
   - The score comes from static signals: the docstring, type hints, naming conventions and call sites.
   - If the score is below the threshold (`--confidence`, default 0.6), the LLM re-infers the intent and the more confident version is kept.
   - Intents are stored and can be edited. An edited intent is never overwritten by a later run.
3. **Generate.** The model receives the intent and the component's source. It also receives the exact import line for the component and the public API of the related project modules (signatures only). It returns test functions, imports and fixtures, which are written as one file per component.
4. **Run.** Each file runs under pytest, and failures are attributed to individual tests.
5. **Repair.** Failing tests go back to the model with their real pytest output, for up to two rounds.
6. **Diagnose.** Tests that still fail are classified as a wrong test, a code bug or a wrong intent.
   - A suspected code bug is kept with `@pytest.mark.xfail(reason="code2test: possible bug - ...")`.
   - Everything else is dropped.
7. **Check the whole suite.** All generated files run together, and tests that fail only alongside others are dropped. Such tests usually share module-level state.

The suite Code2Test writes therefore always passes: every test either passes or is an explicit expected failure.

## Commands

| Command | Purpose |
| --- | --- |
| `code2test test [PATH]` | Generate tests for a repository, directory or file |
| `code2test verify [PATH]` | Run tests; optionally diagnose or repair failures |
| `code2test benchmark [PATH]` | Measure mutation score and diagnosis accuracy of the generated tests |
| `code2test intent show\|edit\|export [NAME]` | Review or correct inferred intents |
| `code2test report summary\|coverage` | Summarize stored intents, or report behavioral coverage and diagnostic accuracy |
| `code2test init` | Save project defaults for `code2test test` (confidence threshold, output directory, exclude patterns) in `.code2test/config.json` |
| `code2test config set\|show\|validate` | Store the API key and model (`--api-key`, `--main-model`); `validate` sends the model one test request |
| `code2test version` | Show the installed version |

### `code2test test`

| Option | Default | Meaning |
| --- | --- | --- |
| `--auto` | off | Run without prompts |
| `--confidence FLOAT` | 0.6 | Intent confidence needed to generate tests in `--auto` mode |
| `--output-dir PATH` | `tests` | Where generated tests are written, relative to the project root |
| `--include GLOB` | | Analyze only matching files |
| `--exclude GLOB` | | Leave matching files out of the analysis; repeatable, and added to the built-in exclusions |
| `--dry-run` | off | Generate tests (this calls the model) without writing or running test files |
| `--exit-code` | off | Exit 1 if any written file failed verification (for CI) |
| `--report html\|json\|all` | none | Write a run report to `<output-dir>/reports/` |

Defaults for `--confidence`, `--output-dir` and extra exclude patterns can be saved per project with `code2test init`, for example `code2test init --confidence 0.7 --exclude "*migrations*"`. They are stored in `.code2test/config.json`; options given on the command line take precedence. The output directory and the usual test, cache and virtual-environment folders are never analyzed.

`PATH` can be the repository, a subdirectory or a single file. Imports, the `tests/` directory and `.code2test/` always resolve to the project root, which is the nearest directory containing `.git`, `pyproject.toml`, `setup.py`, `setup.cfg` or `.code2test`.

### `code2test verify`

```bash
code2test verify tests/              # run the suite, exit 1 on any failure
code2test verify --diagnose tests/   # explain each failure
code2test verify --fix tests/        # repair generated tests after the code changed
```

`--fix` only changes files that Code2Test generated and that have not been edited since.

### `code2test intent`

```bash
code2test intent show add            # by function or class name
code2test intent show calc.ops       # everything in a module
code2test intent edit add            # correct an intent; later runs reuse it
code2test intent export --format json
```

### `code2test benchmark`

Run this after `code2test test`. It injects small bugs into the tested code one at a time and reports the share the generated tests catch. Each bug is a single-site mutant, such as a flipped comparison or a changed constant. The source file is restored after every mutant.

The benchmark also scores the diagnosis agent on failures whose cause is known. Failures caused by mutated code should be diagnosed as code bugs. Passing tests given a deliberately wrong expected value should be diagnosed as wrong tests.

| Option | Default | Meaning |
| --- | --- | --- |
| `--mutants N` | 50 | Maximum number of mutants to run |
| `--diagnoses N` | 10 | Diagnosis cases per expected cause; 0 skips the LLM step |
| `--timeout SECONDS` | 120 | pytest timeout per run |

### `code2test report coverage`

Reports test quality per component:

- **Behaviors tested.** The distinct behaviors that the component's passing tests check, as stated for each generated test, next to its inferred intent.
- **Mutants killed.** The share of injected bugs in the component that the generated suite catches.
- **Diagnostic accuracy.** How often the diagnosis agent named the right cause of a failure with a known cause.

The last two come from the most recent `code2test benchmark` run; the report says when that run predates the current tests. `--format html` or `json` writes the report to `tests/reports/`; `code2test test --report` includes the same section.

### Continuous integration

`code2test test --auto --exit-code` and `code2test verify` both exit non-zero on failure. Examples for GitHub Actions and GitLab CI are in [`examples/ci`](examples/ci).

## Files Code2Test writes

| Path | Contents |
| --- | --- |
| `tests/<package>/test_<module>_<component>.py` | Generated tests, one file per component (`test_<component>.py` for a package's `__init__.py`) |
| `.code2test/code2test.db` | Inferred intents and the registry of generated tests (SQLite) |
| `.code2test/metrics.json` | Metrics of the last `test --auto` run |
| `.code2test/benchmark.json` | Results of the last `benchmark` run, including uncaught mutants |
| `.code2test/dependency_graphs/` | The analyzed dependency graph |
| `.code2test/config.json` | Project defaults written by `code2test init` and read by `code2test test` |
| `tests/reports/report.html`, `report.json` | Run reports, when `--report` is used |
| `tests/reports/coverage.html`, `coverage.json` | Coverage reports from `code2test report coverage --format html\|json` |

## Results

Measured on two open-source libraries after removing each library's own tests, with two MiniMax models: `MiniMax-M3.1-Flash-Preview` (Flash) and `MiniMax-M3` (M3). The table shows the first run of each configuration.

| Measure | inflection, Flash | inflection, M3 | TinyDB, Flash | TinyDB, M3 | Target |
| --- | --- | --- | --- | --- | --- |
| Components with passing tests | 100% (13 of 13) | 100% (13 of 13) | 96% (25 of 26) | 96% (25 of 26) | 70% |
| Generated tests passing before any repair | 96% (196 of 205) | 85% (147 of 172) | 87% (411 of 471) | 99% (294 of 297) | 80% |
| Test cases in the written suite | 408, all passing | 326, all passing | 531, all passing but 1 skipped | 432, all passing | |
| Injected bugs caught (mutation score) | 59% (47 of 80) | 73% (58 of 80) | 78% (62 of 80) | 76% (61 of 80) | |
| Diagnosis accuracy on failures with a known cause | 97% (29 of 30) | 100% (30 of 30) | 100% (30 of 30) | 100% (30 of 30) | 75% |
| Time to generate, run and repair | 193 s | 407 s | 314 s | 815 s | |

inflection 0.5.1 has 426 lines and 13 components; TinyDB 4.8.2 has 2,170 lines and 26 components. The targets come from the project proposal ([docs/proposal.md](docs/proposal.md)), and every run met all three.

The mutation scores show where the generated suites are weak:

- In inflection, half of the sampled mutants fall in `_irregular`, which builds the rules for irregular words such as *person*/*people*. The Flash run wrote a single test for it that checks only how many rules are added, and caught 9 of its 40 mutants. Outside `_irregular`, the suites caught 38 of 40 (Flash) and 40 of 40 (M3).
- In TinyDB, most surviving mutants change string literals, such as error messages and the names `Query` uses as hash keys, which tests rarely observe.

A second run of each configuration gave similar results, and one of them kept a test as an expected failure that exposes a real defect in inflection: `singularize("campuses")` returns `"campuse"`.

On these well-documented libraries, nearly every inferred intent came from the docstring. The paper ([`research/paper/main.pdf`](research/paper/main.pdf)) describes the setup, analyzes these results and compares Code2Test with related tools. The generated suites, intents and raw results are in [`research/data/`](research/data/).

## Limitations

- **Python only.** Files in other languages are part of the dependency graph but get no tests; the tool says so when it skips them.
- **Behavior is inferred, not specified.** Expected values come from the inferred intent and the source. Review generated tests before relying on them, as you would review a colleague's.
- **Each run calls the model.** A run sends source code to the configured provider and costs API usage: one or more calls per component, plus repairs.
- **Results come from two libraries and two models of one provider, two runs each.** Larger codebases, code with external services, other models and a proper estimate of run-to-run variance are not yet measured.

## Development

```bash
git clone https://github.com/Cirkitly/code2test.git
cd code2test
pip install -e ".[dev]"
pytest
ruff check code2test tests research/scripts      # lint
ruff format code2test tests research/scripts     # format
```

The tests in `tests/` drive the whole pipeline offline with scripted models, so no API key is needed. CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs them on Python 3.12 and 3.13, and checks lint and formatting, on every push and pull request.

When changing the pipeline:

- Add or update a test in `tests/` for every behavior change. `tests/test_pipeline.py` shows how to script model responses.
- To check a change against a real model, run `code2test test --auto`, `code2test verify` and `code2test benchmark` on a small library with its own tests removed, as [`research/scripts/run_experiments.sh`](research/scripts/run_experiments.sh) does.
- Keep [docs/architecture.md](docs/architecture.md) in step with the code it describes.

Further documentation:

- [docs/architecture.md](docs/architecture.md): modules and data flow
- [docs/quickstart.md](docs/quickstart.md): a step-by-step first run
- [docs/task.md](docs/task.md): implementation status
- [docs/proposal.md](docs/proposal.md): the original project proposal and its success criteria
- [docs/real_model_run.md](docs/real_model_run.md): the first real-model runs and the failures they exposed
- [research/](research/): the paper, experiment scripts and raw results

## License

MIT; see [LICENSE](LICENSE). The dependency analyzer is derived from [CodeWiki](https://github.com/FSoft-AI4Code/CodeWiki) (MIT, copyright 2025 FSoft-AI4Code), whose notice is kept in the LICENSE file.
