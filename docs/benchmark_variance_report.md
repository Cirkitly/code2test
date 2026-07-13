# Benchmark Variance Report

**Date:** 2026-07-13
**Benchmark commit SHA:** `f20744d8ae31ec4968b676c9457001d36d4fa4f7` (dirty working tree)
**Number of runs:** 2
**Provider:** openai
**Model:** MiniMax-M3
**Confidence threshold:** 0.0
**Corpus:** `corpus/manifest_failure_modes.json`

## Purpose

Measure inter-run variance and pipeline determinism. The per-component invariant (one rewrite per component per run) is load-bearing and was NOT violated for this experiment. Each run is a fresh invocation of the harness. Nothing is shared between runs except the corpus, the model, the harness code, and the prompt.

If distributions are tight and consistently poor, the architecture is deterministic and the implementation is wrong. If distributions are wide, model stochasticity is dominating and prompt/provider work becomes justified. We don't decide which based on narrative; we let the data decide.

## Summary statistics per metric

| Metric | n | Mean | Median | Std | Min | Max |
|--------|---|------|--------|-----|-----|-----|
| `generation_success_rate` | 2 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| `verification_pass_rate_before_rewrite` | 2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `diagnosis_trigger_rate` | 2 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| `rewrite_attempt_rate` | 2 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |
| `rewrite_success_rate` | 2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `verification_pass_rate_after_rewrite` | 0 | NaN | NaN | NaN | NaN | NaN |
| `final_acceptance_rate` | 2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Per-metric NaN: the metric's denominator was zero on every run, indicating the upstream stages didn't engage.

## Failure category distribution

Each `RewriteCommitted` event is classified by the variance script using fields it carries: `isolated_passed`, `isolated_failed`, `replaced`, `strategy`, `failure_classification`.

| Category | Count | Fraction |
|---------|-------|----------|
| `strategy_skip` | 2 | 100.0% |

## Prompt hash stability

The test-generation prompt hash was stable across all runs: `39d0f94a6eebbdd7a8d27a80aa7d09f9d622553f2fe93ff80ed6342b8cb398bb` (1 unique value(s) across 2 runs).

## Representative raw responses per category

### `strategy_skip`

```
<think>The user wants me to generate pytest tests for a "validators" component. The intent is "Function validators" with 73% confidence.

Looking at the source code, this is actually a "failure-mode corpus" - deliberately broken implementations. The component contains three functions:
1. `is_valid_email(s: str) -> bool` - has a bug: doesn't check for dot in domain
2. `clamp(x: int, low: int, high: int) -> int` - has a bug: off-by-one in lower bound
3. `reverse_words(s: str) -> str` - has a bug: doesn't handle multiple spaces correctly

The signature `validators() -> None` doesn't match the act
... [truncated, full length 11129 chars]
```


## Per-run metric table

| Run | generation_success_rate | verification_pass_rate_before_rewrite | diagnosis_trigger_rate | rewrite_attempt_rate | rewrite_success_rate | verification_pass_rate_after_rewrite | final_acceptance_rate |
|------|---|---|---|---|---|---|---|
| 1 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
| 2 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | NaN | 0.000 |
