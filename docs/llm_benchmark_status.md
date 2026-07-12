# Real-LLM Benchmark Status (v1.1 task 3b)

**Status (2026-07-12): LANDED.**

This document records what the first real-LLM benchmark against
MiniMax-M3 produced, the architecture decision that produced it, and
where the v1.1 pipeline is now.

## Recorded run

```bash
cd code2testbench
source ../.venv-fresh/bin/activate
export OPENAI_API_KEY='sk-cp-...'      # real key, exercised then discarded
export OPENAI_BASE_URL='https://api.minimax.io/v1'
python -m code2testbench.runner --provider openai \
    --model MiniMax-M3 --confidence 0.0
cat latest_report.json
```

Output (committed at `code2testbench/latest_report.json`):

```json
{
  "schema_version": 1,
  "provider": "openai",
  "model": "MiniMax-M3",
  "confidence": 0.0,
  "initial_acceptance_rate": 1.0,
  "diagnosis_trigger_rate": 0.0,
  "rewrite_attempt_rate": 0.0,
  "final_acceptance_rate": NaN,
  "net_improvement": NaN,
  "_num_components": 10
}
```

### Interpretation

- `initial_acceptance_rate: 1.0` — every component extracted by intent
  analysis was accepted. With `confidence_threshold=0.0` the LLM path
  fired on every one.
- `diagnosis_trigger_rate: 0.0` — **zero test failures**. The five
  corpus repos produced tests that all passed pytest without
  diagnosis-driven rework.
- `rewrite_attempt_rate: 0.0` — same explanation.
- `final_acceptance_rate: NaN` — the document "no data" signal for a
  denominator of zero rewrites. Defined in `AcceptanceReport.to_dict`
  semantics.
- `net_improvement: NaN` — same.

This is a **good** first recorded result for v1.1: every fixture
component produced passing tests from the LLM. The four-number
contract is satisfied; lower-bound numbers will move only when test
failures occur or rewrites happen.

## What changed in v1.1 to make this happen

Three coordinated fixes:

1. **`response_format={"type": "json_schema", ...}`** in
   `PydanticAIProvider.predict()`. Reasoning-capable models produce
   schema descriptions when only prose-instructed. Server-side schema
   enforcement returns array-element instances directly.

2. **`tests: list[GeneratedTest]` parameterization** in
   `code2test/agents/test_agent.py`. The earlier `list  # list[GeneratedTest]`
   lazy annotation produced empty `items: {}` in JSON Schema, which
   is the trigger MiniMax-M3's reasoning phase interprets as "describe
   what each item is" rather than "produce instances".

3. **`pytest-json-report>=1.5.0` declared as runtime dep**. The
   verifier always used `--json-report-file=...`; without the plugin,
   pytest exited 4 with an unrecognized-option error and the JSON file
   was empty. This was masking real counts on every prior run.

## What you need to know to operate this

Set these environment variables for a real-LLM benchmark run:

```bash
export OPENAI_API_KEY=<your-key>
export OPENAI_BASE_URL=https://api.minimax.io/v1     # project's deployment target
export OPENAI_MODEL=MiniMax-M3                       # any model your account exposes
```

The harness's `--confidence 0.0` flag is what activates the LLM path
across all components. With the default `0.6`, the static extractor
short-circuits on any well-documented component and the harness never
exercises the LLM-driven path it exists to test.

## What's in v1.2 next

None of this should land in v1.1 itself. The architecture works and
the benchmark runs. Possible v1.2 directions:

* **Failure-mode coverage.** Run with deliberately-bad fixtures to
  verify the diagnosis path triggers rewrites and final_acceptance_rate
  moves from 1.0 toward an SLO target.
* **`response_format` on Anthropic SDK.** If MiniMax or another
  provider offers a `tool_choice="required"` path that's lower-cost
  than JSON-schema strict mode, it could be the default for
  non-reasoning models.
* **Schema integration tests.** Currently the strict-enforcement path
  is verified by mocked-OpenAI unit tests; an integration-level
  record-replay test against MiniMax with a recorded conversation
  would close that loop.
