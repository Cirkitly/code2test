<h1 align="center">Code2Test: Intent-Driven Test Generation Agent</h1>

<p align="center">
  <strong>Hierarchical Test Generation</strong> • <strong>Multi-Language Support</strong> • <strong>Human-in-the-Loop Verification</strong>
# Code2Test

> **Status: v1.0.0** — see [CHANGELOG.md](./CHANGELOG.md) for what is and isn't in this release.

Code2Test is an intent-first test generation agent. It extracts behavioral intent from source components (static analysis + LLM), generates tests that verify that intent, runs them, and diagnoses any failures. The emphasis is on **understanding what code is supposed to do** before deciding how to test it.

This v1.0 release ships:

- A single `Config` schema (`code2test.config.Config`) and a single provider seam (`code2test.providers.get_provider`) — agents no longer embed `pydantic_ai.Agent(...)` construction; they go through `provider.predict(system, user, schema)`.
- A real `StubProvider` for offline deterministic runs and CI; a scaffolding `PydanticAIProvider` (raises `NotImplementedError` — real wiring lands in v1.1).
- A real three-phase pipeline (intent extraction → test generation → verifier+diagnosis) wired end-to-end on stub.
- 88 passing tests covering smoke, unit, integration, and the full pipeline.
- A separate `code2testbench/` package with a 5-repo vendored corpus and a four-number `AcceptanceReport` (`code2testbench.runner` CLI).

What's **not** in v1.0 (deferred to v1.1+):

- A real LLM-backed provider (`PydanticAIProvider.predict` raises `NotImplementedError`).
- ChromaDB / vector-DB-backed intent storage.
- The web UI (`code2test/src/fe/`) inherited from the CodeWiki fork.
- Multi-language adapter benchmarks beyond Python.
- Mutation testing.
- The 1M-LOC scaling claim.

Architecture invariants are enforced by automated tests:

- `code2test/core/generator.py` does not import `AcceptanceReport`.
- `code2test/agents/*.py` do not import `pydantic_ai` directly.
- `import code2test` does not eagerly pull `cli.main`.
- CLI subcommands load lazily through `LazyGroup`.

For the quantitative SLOs reported by the benchmark, see `code2testbench/SLO.md`.

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/cirkitly/code2test.git
cd code2test

# Install with the dev extras (the only mode that lets you run the
# test suite). The [dev] extras pull pytest, pytest-cov, pytest-asyncio,
# pygments, and the linting tools. Without [dev] the package is install-
# able but not testable.
pip install -e ".[dev]"

# Verify installation
python -m code2test --help
```

Note: on a clean machine `pip install -e .` (without `[dev]`) succeeds too, but won't include the test tools. Both forms are reproducible from `pyproject.toml` alone.

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

### 3. Reporting
Generate detailed reports after a test run.

```bash
code2test test --auto --report html .
```
This creates `reports/report.html` with a visual summary of the run.

## 🏗️ Architecture

Code2Test operates in five phases:

1.  **Foundation**: Parses the codebase to build a Dependency Graph.
2.  **Intent Extraction**: Uses static analysis + LLMs to infer *what* a component should do.
3.  **Test Generation**: Uses language-specific agents to write idiomatic test code (Pytest, Jest, JUnit).
4.  **Verification**: Executes the generated tests immediately.
5.  **Diagnosis & Repair**: If tests fail, a diagnosis agent analyzes the traceback to fix the test or flag the code.

## 🤝 Contributing

Contributions are welcome! Please check out the [implementation plan](docs/implementation_plan.md) to see what's next.

## 📄 License

MIT License
