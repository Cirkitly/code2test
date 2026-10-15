<h1 align="center">Code2Test: Intent-Driven Test Generation Agent</h1>

<p align="center">
  <strong>Hierarchical Test Generation</strong> • <strong>Multi-Language Support</strong> • <strong>Human-in-the-Loop Verification</strong>
</p>

# Code2Test

Code2Test is an advanced AI agent that automatically generates, verifies, and maintains test suites for large-scale codebases. Unlike simple test generators that look at isolated functions, Code2Test understands the *intent* of your components, their role in the system architecture, and their dependencies.

It employs a hierarchical approach, extracting high-level intents from your codebase, generating corresponding tests, and running them in a verification loop to ensure correctness.

## 🚀 Key Features

*   **Intent-First Generation**: Extracts "intent" from docstrings, naming conventions, and dependencies to generate meaningful tests, not just coverage padding.
*   **Hierarchical Understanding**: Analyzes your dependency graph to understand how components interact, enabling integration test suggestions.
*   **Human-in-the-Loop**: Interactive CLI allows you to review inferred intents, edit generated tests, and guide the agent before committing.
*   **Self-Healing Verification**: If a generated test fails, the agent analyzes the error, determines if it's a test bug or a code bug, and attempts to fix the test automatically.
*   **Language Support**:
    *   🐍 **Python** (pytest) - *Test generation and verification*
    *   ☕ Java, 🟨 JavaScript/TypeScript, C/C++, C#, PHP - *Code analysis only* (dependency graph and documentation; test generation is planned)
*   **CI/CD Ready**: Includes `--auto` mode for headless execution in CI pipelines, with support for Github Actions and GitLab CI.
*   **Comprehensive Reporting**: Generates HTML and JSON reports detailing test coverage, verification status, and confidence levels.

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/cirkitly/code2test.git
cd code2test

# Install dependencies
pip install .

# Verify installation
code2test --help
```

## 🛠️ Usage

### 1. Interactive Test Generation
The default mode. The agent scans your code, presents inferred intents, and asks for confirmation before generating tests.

```bash
# Generate tests for the current directory
code2test test .

# Generate tests for a specific module
code2test test src/core/auth.py
```

### 2. CI/CD / Automated Mode
Run without user interaction. Useful for CI pipelines or nightly builds.

```bash
# Run in auto mode with a confidence threshold
code2test test --auto --confidence 0.8 --exit-code src/
```

*   `--auto`: Skip interactive prompts.
*   `--confidence 0.8`: Only generate tests for intents with >80% confidence.
*   `--exit-code`: Fail the build (exit 1) if any verification step fails.

### How generated tests are verified
Every generated test file is run with pytest before it is kept:

1.  Passing tests are written to `tests/<package>/test_<module>_<component>.py`.
2.  Failing tests are sent back to the model together with the real pytest failure output and repaired (up to 2 rounds).
3.  Tests that still fail are diagnosed. If the code under test looks buggy (it contradicts the inferred intent), the test is kept with `@pytest.mark.xfail(reason="code2test: possible bug - ...")` so the bug stays visible without breaking your suite. Otherwise the test is dropped.

The suite that lands in your repo therefore always passes.

### Re-checking tests later
```bash
code2test verify tests/            # run tests, exit 1 on any failure (CI friendly)
code2test verify --diagnose tests/ # explain each failure: wrong test, code bug or wrong intent
code2test verify --fix tests/      # repair failing generated tests after the code changed
```
`--fix` only touches files code2test generated and that you haven't edited since.

### Measuring test quality
Every `code2test test --auto` run ends with its metrics (also saved to `.code2test/metrics.json`): how many components got tests, how many generated tests passed before any repair, and how many were repaired, kept as `xfail` or dropped.

```bash
code2test benchmark .     # after code2test test
```
`benchmark` injects small bugs (mutants) into the tested code one at a time and reports the share the generated tests catch, and checks the diagnosis agent against failures whose cause is known. Your source is restored after every mutant. Results go to `.code2test/benchmark.json`.

### Reviewing intents
```bash
code2test intent show add          # by function/class name
code2test intent show calc.ops     # everything in a module
code2test intent edit add          # correct an intent; it is reused on the next run
```

### Choosing a model
Set `CODE2TEST_MODEL` to any [pydantic-ai model string](https://ai.pydantic.dev/models/) to override the configured model, e.g. `CODE2TEST_MODEL=openai:gpt-4o-mini` or `CODE2TEST_MODEL=anthropic:claude-sonnet-5-5`. `CODE2TEST_MODEL=test` runs the whole pipeline offline with a fake model (useful for checking your setup without an API key).

Any OpenAI-compatible provider works too: set `OPENAI_BASE_URL` and use the `openai-chat:` prefix. For example, MiniMax:

```bash
export OPENAI_API_KEY=...            # your MiniMax key
export OPENAI_BASE_URL=https://api.minimax.io/v1
export CODE2TEST_MODEL=openai-chat:MiniMax-M3.1-Flash-Preview
code2test test --auto .
```

See [docs/real_model_run.md](docs/real_model_run.md) for a full run against a real library.

### 3. Reporting
Generate detailed reports after a test run.

```bash
code2test test --auto --report html .
```
This creates `tests/reports/report.html` (under `--output-dir`) with a visual summary of the run.

## 🏗️ Architecture

Code2Test operates in five phases:

1.  **Foundation**: Parses the codebase to build a Dependency Graph.
2.  **Intent Extraction**: Uses static analysis + LLMs to infer *what* a component should do.
3.  **Test Generation**: Uses an LLM agent to write pytest tests, given the component's source, intent and exact import path.
4.  **Verification**: Executes the generated tests immediately.
5.  **Diagnosis & Repair**: Failing tests are repaired from their pytest output; tests that still fail are diagnosed and either kept as `xfail` (suspected code bug) or dropped.

## 🧪 Development

```bash
pip install -e ".[dev]"
pytest
```
The test suite runs the whole pipeline offline with scripted models, so no API key is needed.

## 🤝 Contributing

Contributions are welcome! Please check out the [implementation plan](docs/implementation_plan.md) to see what's next.

## 📄 License

MIT License
