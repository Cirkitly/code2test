# Real-LLM Benchmark Status (v1.1 task 3b)

## What was attempted

End-to-end harness run against the deployed MiniMax-compatible
endpoint on 2026-07-12:

```bash
OPENAI_BASE_URL=https://api.minimax.io/v1
OPENAI_MODEL=MiniMax-M3
OPENAI_API_KEY=sk-cp-...      # real key, exercised then discarded

python -m code2testbench.runner --provider openai --model MiniMax-M3
```

## What worked

- **Authentication**: HTTP 200 on `POST /v1/chat/completions` with
  Bearer auth (curl-probe and direct SDK call).
- **Models listing**: `MiniMax-M3`, `MiniMax-M2.7`, `MiniMax-M2.7-highspeed`,
  `MiniMax-M2.5`, ... returned via `GET /v1/models`.
- **Single-call predict()**: a one-shot `IntentAgent.infer_intent`
  call against `MiniMax-M3` returned a well-formed `IntentInferenceResult`
  with confidence 0.78 in ~5 seconds.
- **Harness wiring**: `code2testbench.runner` produced a valid
  `latest_report.json` with all six expected keys and a non-zero
  `_num_components`.

## What did not work

The harness recorded:

```json
{
  "initial_acceptance_rate": 1.0,
  "diagnosis_trigger_rate": NaN,
  "rewrite_attempt_rate": NaN,
  "final_acceptance_rate": NaN,
  "net_improvement": NaN
}
```

After ~83 seconds wall-clock. Five real components × ~17s each
(intent extract + test gen + verifier). All three phases ran
against the real endpoint.

`initial_acceptance_rate: 1.0` because the **static intent extractor
gives 0.99 confidence** on each component (they all have docstrings).
The LLM-path is only triggered when confidence is below threshold;
on this corpus, never — so the LLM-based intent extraction is
exercised only by direct probes, not through the harness.

The diagnosis-trigger and rewrite-attempt rates are `NaN` because
**the test-generation phase produces 0 test files** — the
`if test_file.test_cases` filter at the end of phase 2 drops every
file. This is the bug that needs more work, and the reason the recorded
benchmark is uninformative right now.

## Why the test-generation phase produces zero tests

`MiniMax-M3` is a **reasoning-capable model**. When given a schema
specifying ``tests: list[GeneratedTest]``, it returned:

```json
{
  "tests": [
    {
      "description": "Comprehensive test cases for chunk() function",
      "type": "object",
      "properties": { ... }
    }
  ]
}
```

The model produced a **schema description of the array elements** rather
than **instances of the array elements**. Or it produced a single dict
that has only one field — the field that maps to the schema's required
fields were not all filled. Either way, ``model_validate_json`` raised
``ValidationError`` (missing fields like ``name``, ``test_code``,
``tests_behavior``) or ``AttributeError("dict has no attribute name")``.

Attempted fixes (none resolved it during the v1.1 task-3b window):

- Strengthened ``PYTEST_GENERATION_PROMPT`` to say "produce OBJECT
  INSTANCES, not schema descriptions, not placeholders" and to give
  each field's shape explicitly. Did not reach a non-zero success rate.
- Bumped the openai SDK client ``timeout`` from 30s to 120s. Was on the
  edge of timing out during the longer reasoning phase for one
  component; 120s cleared it but did not produce test files.
- Prompted the model to avoid ``<think>...</think>`` blocks. The extractor
  handles them now (``PydanticAIProvider._extract_json`` strips these
  blocks first), but the model still emits them and they cost ~30s per
  call.

## What's next

This is a v1.1 task-3b **discovery**, not a v1.1 task-3b **completion**.
The wiring works; the *prompt × schema × reasoning-model* triple is
the next iteration. Two concrete follow-ups:

1. **Schema instancing**: switch `PydanticAIProvider.predict()` from
   "JSON schema in system prompt" to the openai SDK's
   ``response_format={"type": "json_schema", "json_schema": {...}}``
   parameter on `chat.completions.create`. The OpenAI API enforces the
   schema server-side for newer models; minimax's compatibility path
   should propagate this. Untried in v1.1.
2. **Lower the static-intractor confidence threshold** so the LLM
   path is actually exercised end-to-end on every component. With
   ``confidence_threshold=0.99``, the dynamic path never runs, so
   we never observe whether the dynamic path produces working tests.
   Setting it to ``0.0`` for testing forces every component through
   the LLM path and lets the harness measure test generation in
   isolation.

Once one or both are implemented, re-run and record the corrected
`latest_report.json`.

## What this commit does NOT include

- No recorded real-benchmark JSON in the tree — that's a future
  commit, separately, once the prompt/schema issue above is fixed.
- No changes to the architectural invariants.
- No changes to `v1.0.0`.
