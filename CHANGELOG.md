# Changelog

All notable changes to code2test are documented here. Versions follow
[semver](https://semver.org/). The format is based on [Keep a Changelog](https://keepachangelog.com/).

## 1.0.0 (2026-07-12)

First release that we will defend as honest. The architectural skeleton
is implemented end-to-end and validated by automated tests, but
quantitative claims about test quality are bounded — we report what the
stub provider produces, not aspirational SLO numbers.

### Added

* `code2test.config.Config` — single pydantic schema; round-trips
  through JSON files; replaces three previous Config classes.
* `code2test.providers` package — `Provider.predict(system, user,
  schema) -> schema_instance` seam. Two implementations: `StubProvider`
  (deterministic, offline) and `PydanticAIProvider` (scaffolding only
  in v1.0; raises `NotImplementedError` to surface the missing wiring
  loudly).
* Three agents (`IntentAgent`, `TestAgent`, `DiagnosisAgent`) rewire
  through the provider seam. No agent directly constructs
  `pydantic_ai.Agent(...)` in v1.0.
* `code2test.events` module — five event types (`IntentExtracted`,
  `TestsGenerated`, `VerificationCompleted`, `DiagnosisTriggered`,
  `RewriteAttempted`) plus a `null_sink()`. Generator emits events
  through an injected sink; production default is null.
* CLI refactor for lazy per-command loading (`code2test.cli.main.LazyGroup`).
  Subcommands load only when resolved; one broken subcommand no longer
  breaks the whole package.
* `tests/fixtures/sample_repo/calc/` — five ambiguous-intent Python
  functions with a 27-test ground-truth suite used by M1C.3.
* `tests/fixtures/sample_repo/calc_hidden/` — ground-truth test suite.
* `code2testbench/` — separate benchmark package. 5 vendored repos,
  `EventCollector` translates code2test events to a 4-number
  `AcceptanceReport`. `code2testbench.runner` is the CLI.

### Verified

* `python -m code2test --help` returns help text on Python 3.12+;
  every documented subcommand resolves through CliRunner.
* `pytest tests/` — 88 passing, 1 skipped, 0 failed across smoke,
  unit, integration.
* `pytest code2testbench/tests/` — 21 passing, 0 failed.
* `python -m code2testbench.runner --provider stub` writes
  `latest_report.json` with all four rates.

### Architecture invariants enforced by automated tests

* `code2test/core/generator.py` does not import or reference
  `AcceptanceReport` (verified by `inspect.getsource` test).
* `code2test/agents/*.py` do not import `pydantic_ai` directly
  (verified by `inspect.getsource` test).
* `code2test/__init__.py` is lazy — `import code2test` does not pull
  `cli.main` into `sys.modules`.
* `code2test/cli/main.py` uses `LazyGroup`; per-command imports are
  resolved on demand.

### Not in 1.0.0 (deferred)

* **ChromaDB / vector store for intents.** SQLite only.
* **Web UI (`code2test/src/fe`).** Legacy from the CodeWiki fork;
  not exercised by any v1.0 subcommand.
* **Multi-language adapters beyond Python.** Java/JavaScript adapters
  exist in code2test/adapters/ but v1.0 ships only the Python
  adapter path in the benchmark corpus.
* **Mutation testing / Code2TestBench mutation scoring.**
* **1M-LOC scaling claim.** Unverified; do not assert.
* **Real LLM provider.** `PydanticAIProvider` raises
  `NotImplementedError` in v1.0. Wiring land in v1.1.
* **CodeWiki legacy docs subsystem** (`code2test/src/`). Imports only
  via the legacy `code2test generate` command, which is out of v1.0
  scope. Not exercised by tests.

### Notes

* The four SLO numbers reported by code2testbench/SLO.md (40/20/15/55
  v1.0 floor; 60/40/35/75 stretch) are *lower* than the proposal's
  MVP targets (70/80/75). Reporting the lower number is honest;
  reporting the higher number before it has been measured would not be.
  Stretch targets are documented; they are what v1.1 aims for.
* StubProvider returns deterministic, content-derived values — useful
  for tests and CI, not a substitute for a real LLM. v1.0 ships with
  stub-only runs; real provider lands in v1.1.
