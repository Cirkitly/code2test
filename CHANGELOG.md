# Changelog

All notable changes to code2test are documented here. Versions follow
[semver](https://semver.org/). The format is based on [Keep a Changelog](https://keepachangelog.com/).

## 1.1.0 (2026-07-12)

Strict scoping of v1.0's "wiring is real; first real-LLM benchmark lands
in v1.1" promise. v1.1 task 3a landed the provider wiring; v1.1 task
3b recorded the first real-LLM benchmark against MiniMax.

### Added

- `code2test.providers.schema_helpers` — converts pydantic schemas into
  the strict-compliant shape the openai SDK's `response_format`
  accepts. Walks every object level and sets `additionalProperties:
  false`; resolves `$ref` pointers to definitions so referenced
  schemas also satisfy strict mode.
- `PydanticAIProvider.predict()` now passes the schema via
  `response_format={"type": "json_schema", ...}` so reasoning-capable
  models (e.g. MiniMax-M3) emit array-element instances directly
  instead of schema descriptions.
- `GeneratorConfig` carries `provider/base_url/api_key` fields so the
  generator's lazily-built agent trio wires the configured Provider
  (previously: silently degraded to StubProvider).
- `code2testbench/runner.py` forwards provider credentials into the
  generator and reads `OPENAI_BASE_URL` (with `OPENAI_API_BASE` as
  fallback) so the harness can target any OpenAI-compatible endpoint.
- `pytest-json-report>=1.5.0` is now a runtime dependency. The
  verifier always used `--json-report-file=...`; without the plugin,
  every benchmark run produced only the failed-parse warning.

### Fixed

- `tests: list  # list[GeneratedTest]` → `tests: list[GeneratedTest]`.
  The lazy annotation produced empty `items: {}` in the JSON Schema
  output, which is the trigger for MiniMax-M3's reasoning phase
  to emit schema descriptions rather than instances.
- Confused baseline-threshold behavior in the harness: at the
  default `confidence_threshold=0.6`, the static intent extractor
  already returns 0.99 on every fixture component with docstrings,
  short-circuiting the LLM path that the harness is meant to test.
  We documented that `--confidence 0.0` is the right default for
  LLM-driven harness runs.

### Verified

- `pytest tests/                     -- 104 passed, 1 skipped`
- `pytest code2testbench/tests/      -- 21 passed`
- Direct probe against `MiniMax-M3` returned a valid
  `IntentInferenceResult` in ~5s.
- `python -m code2testbench.runner --provider openai --model MiniMax-M3
  --confidence 0.0` produced:
  ```
  initial_acceptance_rate:    1.0    (10/10 components accepted)
  diagnosis_trigger_rate:     0.0    (zero test failures)
  rewrite_attempt_rate:       0.0    (zero rewrites needed)
  final_acceptance_rate:      NaN    (denominator zero; safe-ratio NaN)
  ```
- The recorded `latest_report.json` was previously placeholder-NaN
  because the verifier never returned real counts (no
  pytest-json-report). After v1.1, it produces real numbers on every
  run against the configured endpoint.
- CI gates (5-step v1.0 ci.yml) — green.

### Architectural invariants preserved

- `code2test/core/generator.py` does not import `AcceptanceReport`.
- `code2test/agents/*.py` do not import `pydantic_ai` directly.
- `import code2test` does not eagerly pull `cli.main`.
- `cli/main.py` uses `LazyGroup`; per-command imports resolved on demand.

`v1.0.0` tag untouched at `1bfa4a5`.

## 1.0.0 (2026-07-12)

First release that we defended as honest. The architectural skeleton
is implemented end-to-end and validated by automated tests, but
quantitative claims about test quality were bounded — the recorded
benchmark reported placeholder-NaN rates because:

* No real LLM provider was wired (PydanticAIProvider raised
  `NotImplementedError`).
* `pytest-json-report` wasn't a declared dependency, so the
  verifier's JSON parse path always failed.

### Added (v1.0)

- `code2test.config.Config` — single pydantic schema; round-trips
  through JSON files.
- `code2test.providers` package — `Provider.predict()` seam.
  `StubProvider` (deterministic, offline). `PydanticAIProvider`
  scaffolding only.
- Three agents (`IntentAgent`, `TestAgent`, `DiagnosisAgent`) rewire
  through the seam. No agent constructs `pydantic_ai.Agent`.
- `code2test.events` — five event types; `null_sink()` default.
- CLI refactor for lazy per-command loading (`LazyGroup`).
- `tests/fixtures/sample_repo/calc/` — five ambiguous-intent functions
  + 27-test hidden ground truth.
- `code2testbench/` — separate package, vendored 5-repo corpus,
  `AcceptanceReport`, `EventCollector`, runner.

### Architectural invariants enforced by automated tests (in v1.0)

- `code2test/core/generator.py` does not reference `AcceptanceReport`.
- `code2test/agents/*.py` do not import `pydantic_ai` directly.
- `import code2test` does not pull `cli.main`.
- CLI subcommands load through `LazyGroup`.

(continued in v1.1.)
