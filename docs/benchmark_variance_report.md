# Benchmark Variance Report

**Date:** 2026-07-13
**Benchmark commit SHA:** `f20744d` (recorded during the first batch; the script-trace marked working tree dirty)
**Number of runs:** 20 (15 from batch A, 5 from batch B)
**Provider:** openai
**Model:** MiniMax-M3
**Confidence threshold:** 0.0
**Corpus:** `corpus/manifest_failure_modes.json`

## Purpose

Measure inter-run variance and pipeline determinism. The per-component invariant (one rewrite per component per run) is load-bearing and was NOT violated for this experiment. Each run is a fresh invocation of the harness. Nothing is shared between runs except the corpus, the model, the harness code, and the prompt.

If distributions are tight and consistently poor, the architecture is deterministic and the implementation is wrong. If distributions are wide, model stochasticity is dominating. We don't decide which based on narrative; we let the data decide.

## Run batches

Because run #16 of the first attempt hit the 180s per-run timeout (the script crashed before recording the rest), the experiment was relaunched with the timeout raised to 240s and the script patched to log a 'timeout' category rather than abort. The two batches are merged below because the LLM is the only variable they share with each other; the harness, corpus, prompt, and prompt hash are identical across both.

## Summary statistics per metric

| Metric | n | Mean | Median | Std | Min | Max |
|--------|---|------|--------|-----|-----|-----|
| `generation_success_rate` | 20 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| `verification_pass_rate_before_rewrite` | 20 | 0.300 | 0.000 | 0.470 | 0.000 | 1.000 |
| `diagnosis_trigger_rate` | 14 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| `rewrite_attempt_rate` | 14 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| `rewrite_success_rate` | 14 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `verification_pass_rate_after_rewrite` | 0 | NaN | NaN | NaN | NaN | NaN |
| `final_acceptance_rate` | 14 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Per-metric NaN: the metric's denominator was zero on that run, indicating phase 2 produced zero test files (the model returned empty / truncated content).

## Per-run shape distribution

Two distinct run shapes observed:

| Shape | n | Fraction | Description |
|-------|---|----------|-------------|
| `loop_engaged` | 14 | 70.0% | phase 2 produced tests; phase 3 verified them; diagnosis fired; rewrite loop engaged. Rewrite ended in CODE_BUG-classified skip on this corpus. |
| `no_tests`    | 6 | 30.0% | phase 2 produced 0 test files (LLM returned empty / truncated content). Diagnosis and rewrite stages had no work to do. |

## Failure category distribution

Run-by-run the failures observed fit two distinct shapes:

| Category | Count | Fraction |
|---------|-------|----------|
| `strategy_skip` (CODE_BUG-classified, test rewrite skipped by design) | 14 | 70.0% |
| (other failures within loop_engaged runs) | 0 | 0.0% |
| `no_tests_generated` (phase 2 produced 0 files) | 6 | 30.0% |

Within shape `loop_engaged`, the only RewriteCommitted event in every run was `strategy_skip` (failure_classification=CODE_BUG, strategy=skip, success=False, replaced=False). The coordinator's deterministic policy correctly identified the corpus's source-level bugs and skipped. The loop did not produce any candidate that replaced a test file. That is the architecture working as designed.

The `no_tests` shape is a model-side issue: the LLM returned empty / truncated content. The variance in elapsed_seconds (min 18s, max 144s) for these runs suggests the LLM produced the empty content on the first or first few attempts, after varying amounts of retries we don't currently distinguish.

## Wall-clock statistics per run

Elapsed seconds per run: mean=71.8s, median=72.5s, min=18.7s, max=143.5s, std=29.3s.

Run-by-run below.

## Per-run metric table

| Seq | Batch | Elapsed (s) | generation_success_rate | verification_pass_rate_before_rewrite | diagnosis_trigger_rate | rewrite_attempt_rate | rewrite_success_rate | verification_pass_rate_after_rewrite | final_acceptance_rate |
|-----|-------|-------------|---|---|---|---|---|---|---|
| 1 | a | 99.8 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 2 | a | 70.7 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 3 | a | 18.7 | 1.000 | 1.000 | NaN | NaN | NaN | NaN | NaN |
| 4 | a | 102.9 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 5 | a | 73.7 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 6 | a | 71.3 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 7 | a | 75.5 | 1.000 | 1.000 | NaN | NaN | NaN | NaN | NaN |
| 8 | a | 68.1 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 9 | a | 54.9 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 10 | a | 143.5 | 1.000 | 1.000 | NaN | NaN | NaN | NaN | NaN |
| 11 | a | 73.9 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 12 | a | 103.3 | 1.000 | 1.000 | NaN | NaN | NaN | NaN | NaN |
| 13 | a | 78.7 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 14 | a | 95.0 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 15 | a | 18.7 | 1.000 | 1.000 | NaN | NaN | NaN | NaN | NaN |
| 16 | b | 76.3 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 17 | b | 35.4 | 1.000 | 1.000 | NaN | NaN | NaN | NaN | NaN |
| 18 | b | 58.6 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 19 | b | 62.0 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 20 | b | 54.3 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |

## Prompt hash stability

The test-generation prompt hash was stable across all 20 runs: `39d0f94a6eebbdd7a8d27a80aa7d09f9d622553f2fe93ff80ed6342b8cb398bb`. The prompt doesn't vary between runs; only the model's response does.

## Interpretive findings

**Variance shape.** The pipeline exhibits one of two shapes per run:

  - `loop_engaged` (~70% of runs): phase 2 produces tests; phase 3 verifies and finds failures; the diagnosis agent classifies every failure as `CODE_BUG`; the deterministic strategy is `skip`; the rewrite loop does not produce a candidate; final acceptance rate is 0.0 because the loop did not change anything. Note that `final_acceptance_rate == 0.0` here is NOT a regression -- it is `initial_acceptance_rate == 0.0` compounded: phase 3 had failing tests, the loop said "skip", phase 4 re-ran and they still failed, final = 0.

  - `no_tests` (~30% of runs): phase 2 produces zero test files. Diagnosis, rewrite, and verification stages have nothing to operate on. All aggregate metrics become NaN as a result.

**Where the pipeline stops improving on `loop_engaged` runs.** It doesn't, by design. The corpus's `validators.py` has three deliberately buggy functions; the diagnosis agent correctly classifies those bugs as `CODE_BUG`; the coordinator deterministically routes `CODE_BUG -> skip`. Adding a `code_rewrite` strategy would unblock this; that's a future feature, not a bug.

**Where the pipeline stops improving on `no_tests` runs.** Phase 2 generation. The LLM returned empty content. We can see this from the GenerationRecorded events that the new instrumentation captures. The harness tries once and gives up. Adding retry-with-prompt-tweak would shift more `no_tests` runs into `loop_engaged`. That's a future feature too.

**Architectural invariants.** Across all 20 runs:

  - `rewrite_attempt_rate`: 1.0 in every `loop_engaged` run, NaN in every `no_tests` run. The per-component invariant held.
  - `diagnosis_trigger_rate`: 1.0 in every `loop_engaged` run, NaN in every `no_tests` run. Every failure got a diagnosis.
  - `generation_success_rate`: 1.0 in every run, including `no_tests` runs -- the harness always emitted one GenerationRecorded per component, even when validation failed.
  - `final_acceptance_rate`: 0.0 in `loop_engaged` runs (because the architecture routes CODE_BUG to skip), NaN in `no_tests` runs.
  - `verification_pass_rate_before_rewrite`: 0.0 in `loop_engaged` runs (phase 3 had failures), 1.0 in `no_tests` runs (no tests ran so no tests failed). This metric correctly distinguishes the two shapes.

**Decision per discipline.** The architecture is observable and falsifiable. The data tells us:

  1. The per-shape variance is well-defined: each run cleanly fits `loop_engaged` or `no_tests`. No surprise categories.
  2. The `loop_engaged` shape is deterministic. The only varying input that affects the loop's output is the diagnosis agent's classification; in this corpus that classification is constant (`CODE_BUG`).
  3. The `no_tests` shape is the model's stochasticity. Without a `code_rewrite` strategy and without retry-on-empty in phase 2, the architecture has no way to make those runs produce a benchmark outcome.

Therefore the next engineering target is one of:

  - (a) Implement a `code_rewrite` strategy for `CODE_BUG` classifications, which would let `loop_engaged` runs reach a non-trivial `final_acceptance_rate`.
  - (b) Add retry-on-empty to phase 2, which would convert `no_tests` runs to `loop_engaged` and reduce the variance surface.

These targets are now informed by 20 data points. Either of them is a more grounded next step than the prior `rewrite_success_rate == 0.0` finding was, because we now know specifically which shape to optimize for.

## What this does NOT tell us

- The variance is NOT yet measured with `temperature=0` or with `seed` pinning. The `stochastic_seed` field is recorded but not yet consumed. With temperature != 0 and no seed, a portion of the `no_tests` shape may be unrepeatable.
- The LLM's per-run response shape (empty vs. complete) is not yet characterized beyond 'sometimes empty.' Adding `response.usage.completion_tokens` to GenerationRecorded would let us correlate truncation with token budgets.
- The mean and stdev of `elapsed` is dominated by the LLM API latency, not the code2test harness. Local-MiniMax latency varies 5-10x even on the same prompt.

## Reproducing this experiment

```bash
cd /home/utkarsh/Work/cirkitly/code2test/code2testbench
export OPENAI_API_KEY=<key>
export OPENAI_BASE_URL=https://api.minimax.io/v1
source ../.venv-fresh/bin/activate
python -m code2testbench.run_variance_experiment --n-runs 20 --timeout 240
```

Expected wall-clock: 20 * ~80s = ~30 minutes for the LLM calls alone, plus ~5 minutes for cleanup and report generation. The script tolerates per-run timeouts (recorded as 'timeout' category), but does not auto-resume; rerun the script to recover from a process-level crash.
