# Empirical Findings: generation_success_rate on MiniMax-M3

**Date:** 2026-07-13 (v1.1 instrumentation cycle)
**Status:** Architecture observable. Recorded run on the failure-mode
corpus shows three of four architectural invariants hold; the
fourth (`final > initial`) does not, and that finding is the next
engineering target.

## What we measured

After landing the v1.1 observability commits (provider `on_record`
callback + `GenerationRecorded` event + `generation_success_rate`
metric), we ran the live harness against the failure-mode corpus
with `--enable-rewrite --confidence 0.0 --model MiniMax-M3`.

Recorded run (commit `d4a5ba1`'s successor):

```json
{
  "schema_version": 2,
  "provider": "openai",
  "model": "MiniMax-M3",
  "confidence": 0.0,
  "initial_acceptance_rate": 1.0,
  "diagnosis_trigger_rate": 1.0,
  "rewrite_attempt_rate": 1.0,
  "rewrite_success_rate": 0.0,
  "final_acceptance_rate": 0.0,
  "generation_success_rate": 1.0,
  "net_improvement": -1.0,
  "_num_components": 1
}
```

Interpretation against `docs/v1.1_targets.md`:

| Assertion | Threshold | Recorded | Pass |
|-----------|-----------|----------|------|
| `diagnosis_trigger_rate == 1.0` | exact | 1.0 | ✓ |
| `rewrite_attempt_rate == 1.0` | exact | 1.0 | ✓ |
| `rewrite_success_rate >= 0.0` | floor | 0.0 | ✓ (boundary) |
| `final_acceptance_rate > initial_acceptance_rate` | floor | 0.0 < 1.0 | ✗ |
| `generation_success_rate > 0` | floor | 1.0 | ✓ |

Three of four architectural invariants hold. The fourth
(`final > initial`) does not. The bottleneck is no longer
"can the LLM produce tests" -- it can. The bottleneck is "do the
rewritten tests pass verification after the loop runs the full
suite."

## What the instrumentation revealed

Multiple runs on the same configuration produced different
shapes:

| Run | generation_success_rate | diagnosis_trigger_rate | observation |
|-----|------------------------|------------------------|-------------|
| A   | NaN                   | NaN                   | Phase 2 short-circuited; no LLM call |
| B   | 0.0                   | NaN                   | Truncated JSON response (EOF in array) |
| C   | 1.0                   | 1.0                   | Successful run, recorded in `latest_report_failure_modes.json` |

The empty-content failure (Run A) was the model's content
returning `""` -- the `on_record` callback captured this in
`raw_response`. Without the instrumentation we couldn't see this;
the test_agent's `try/except Exception` swallowed the underlying
error and the recorded report showed only "Generated 0 test
files" with no diagnostic.

The truncated-JSON failure (Run B) was visible as:

```
ERROR: Test generation failed: 1 validation error for TestGenerationResult
  Invalid JSON: EOF while parsing a list at line 20 column 5
  input_value='{\n  "tests": [\n    {\n...rt lacks a dot."\n    }'
```

The model started a multi-line test case description that got cut
off at "...lacks a dot." with no closing bracket. The recorder
captured the partial `parsed_response` and the validation error
in `validation_errors`.

## Why the rewrite loop is at 0/0

The recorded run (C) shows `rewrite_attempt_rate: 1.0` and
`rewrite_success_rate: 0.0`: the coordinator did its job --
attempted the rewrite exactly once per failing component, exactly
as the architecture guarantees. But the rewrite did not produce
a passing test on this corpus. The candidate test file came back
from the LLM, the candidate verifier ran it, the candidate's
tests all passed in isolation, but something about the
full-suite re-run after the rewrite evaluated them as failing.

Two hypotheses:

1. The candidate tests pass on the **candidate's** parsed input
   but fail when pytest re-imports them at the full-suite re-run.
   This is the transactional property we tested in isolation; if
   it's failing in production, the candidate-vs-production-path
   discrepancy is the bug.

2. The rewrite's verifier result was correct, but the candidate
   test_file's path collided with another component's test_file,
   causing pytest to import both as one suite and shadowing test
   names.

Both are debugging tasks, not prompt/schema changes. The
architecture works; the wiring needs iteration.

## What this means for v1.1.0

The four `v1.1_targets.md` assertions:

* generation_success_rate > 0  → 1.0 ✓
* diagnosis_trigger_rate == 1.0  → 1.0 ✓
* rewrite_attempt_rate == 1.0  → 1.0 ✓
* final_acceptance_rate > initial_acceptance_rate  → 0.0 < 1.0 ✗

The first three pass. The fourth does not. The architecture is
**measurable and falsifiable** as designed. v1.1.0 cannot ship
without the fourth assertion; the next session's task is to
diagnose the rewrite-failure mechanism with the new
instrumentation.

## What we should NOT do next

Per the discipline established earlier this session:

* Do not weaken the benchmark by switching to the v1.0 corpus.
* Do not modify the prompt or schema as an "implementation fix"
  without first understanding whether truncation is a model
  bug, a streaming bug, or a prompt bug.
* Do not tag v1.1.0 until a recorded run satisfies all four
  assertions.

## What we SHOULD do next

Three concrete investigations:

1. **Why does the rewrite's verifier pass in isolation but the
   full-suite re-run fail?** The transactional coordinator tests
   cover this in isolation. If it fails in production, look at
   `verifier.run_tests(candidate)` versus the full-suite re-run
   path in the generator.

2. **Why is the model non-deterministic in whether it returns a
   complete response?** Empty-string and truncated-JSON failures
   appear on some runs but not others. Track completion_tokens
   vs the openai SDK's max_tokens default; the truncation may be
   hitting that limit on some prompt lengths.

3. **Why is `final_acceptance_rate: 0.0`?** Hypothesis: the
   full-suite re-run at the end of phase 4 sees both the rewritten
   test_file and the corpus's other test_files (now also written
   by phase 3) and runs them together. The verifier might be
   running pytest against the wrong path or shadowing names.

Each is a single experiment. We run the harness, record the new
numbers, and decide based on data whether it moved.

## What's committed

* `code2test/providers/pydantic_ai_provider.py` -- on_record callback
* `code2test/events.py` -- GenerationRecorded event
* `code2test/agents/test_agent.py` -- bridges provider record to event
* `code2test/core/generator.py` -- passes run_id to test_agent
* `code2testbench/code2testbench/collector.py` -- generation counter
* `code2testbench/code2testbench/report.py` -- generation_success_rate

CI on v1.1 is green. The architecture is now observable; the
remaining work is upstream model behavior and rewrite-loop
diagnostics.
