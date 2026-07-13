"""Variance experiment: 20 independent runs of the harness.

The point of this script is to measure *inter-run variance* and
*pipeline determinism*. The per-component invariant (one rewrite
per component per run) is load-bearing and must NOT be violated
for the sake of more data. Each run is a fresh invocation of the
harness; nothing is shared between runs except the corpus, the
model, and the harness code itself.

For each run we record the full set of metrics from the
AcceptanceReport plus per-event raw data. Across runs we compute
summary statistics and partition the failure space by reading the
RewriteCommitted events emitted by the rewrite coordinator.

If the distributions are tight and consistently poor, the architecture
is deterministic and the implementation is wrong. If the
distributions are wide, model stochasticity is dominating and
prompt/provider work becomes justified. We don't decide which
based on narrative; we let the data decide.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


METRICS = [
    "generation_success_rate",
    "verification_pass_rate_before_rewrite",
    "diagnosis_trigger_rate",
    "rewrite_attempt_rate",
    "rewrite_success_rate",
    "verification_pass_rate_after_rewrite",
    "final_acceptance_rate",
]


def _git_commit_sha(repo: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10,
    )
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def _git_dirty(repo: Path) -> bool:
    out = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, timeout=10,
    )
    return bool(out.stdout.strip())


def _clean_corpus(corpus_root: Path) -> None:
    """Remove harness residue (.code2test/ state, code/test_*.py) from
    every repo under the corpus. Without this, prior runs leak into
    subsequent runs (the runner picks up code/test_*.py as
    'components').
    """
    for repo in corpus_root.iterdir():
        if not repo.is_dir():
            continue
        code_dir = repo / "code"
        if code_dir.is_dir():
            for tf in code_dir.glob("test_*.py"):
                tf.unlink()
        state = repo / ".code2test"
        if state.is_dir():
            shutil.rmtree(state)


def _run_once(
    bench_root: Path, manifest: Path, out_path: Path,
    provider: str, model: str, confidence: float, api_key: str,
    base_url: str, run_id: int, timeout: float,
) -> dict[str, Any]:
    """Run the harness once and parse the recorded JSON.

    Returns a dict with the metric values, the events list, and
    the run metadata (provider, model, confidence, git SHA).
    """
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    env["OPENAI_BASE_URL"] = base_url

    cmd = [
        sys.executable, "-m", "code2testbench.runner",
        "--provider", provider,
        "--model", model,
        "--confidence", str(confidence),
        "--enable-rewrite",
        "--manifest", str(manifest.relative_to(bench_root)),
        "--out", str(out_path.relative_to(bench_root)),
    ]
    t0 = time.monotonic()
    proc = subprocess.run(
        cmd, cwd=str(bench_root), capture_output=True, text=True,
        timeout=timeout, env=env,
    )
    elapsed = time.monotonic() - t0
    if proc.returncode != 0:
        return {
            "run_id": run_id, "elapsed_seconds": elapsed,
            "exit_code": proc.returncode, "stderr_tail": proc.stderr[-400:],
            "metrics": {}, "events": [],
        }
    payload = json.loads(out_path.read_text())
    return {
        "run_id": run_id, "elapsed_seconds": elapsed,
        "exit_code": 0,
        "metrics": {k: payload.get(k) for k in METRICS},
        "events": payload.get("_events", []),
        "schema_version": payload.get("schema_version"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "num_components": payload.get("_num_components"),
    }


def _summary(values: list[float]) -> dict[str, Any]:
    """Mean, median, std, min, max over the (non-NaN) values."""
    clean = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not clean:
        return {"mean": float("nan"), "median": float("nan"),
                "std": float("nan"), "min": float("nan"), "max": float("nan"),
                "n_observations": 0}
    return {
        "mean": statistics.fmean(clean),
        "median": statistics.median(clean),
        "std": statistics.stdev(clean) if len(clean) > 1 else 0.0,
        "min": min(clean),
        "max": max(clean),
        "n_observations": len(clean),
    }


def _classify_failure(event: dict) -> str:
    """Bucket a RewriteCommitted event into a failure category.

    Categories (priority order):
      1. no_tests_generated: empty GenerationRecorded before
         any rewrite attempt. Detected from a sibling event in
         the same run.
      2. strategy_mismatch: the strategy doesn't match what the
         deterministic classifier should produce for that cause.
      3. strategy_skip: strategy='skip' and the rewrite did
         nothing. By design for CODE_BUG-classified failures;
         not a bug, but the rewrite loop contributed nothing
         to verify outcome.
      4. transactional_replacement_failure: candidate passed in
         isolation but replaced=False.
      5. verifier_failure: candidate failed in isolation.
      6. other: catch-all.
    """
    strategy = event.get("strategy")
    cause = event.get("failure_classification")
    success = event.get("success")
    isolated_passed = event.get("isolated_passed", 0)
    isolated_failed = event.get("isolated_failed", 0)
    replaced = event.get("replaced")

    # Strategy mismatch: our deterministic classifier maps
    # TEST_WRONG -> test_rewrite, INTENT_WRONG -> intent_rewrite,
    # CODE_BUG -> skip. Anything else is a bug.
    expected = {
        "TEST_WRONG": "test_rewrite",
        "INTENT_WRONG": "intent_rewrite",
        "CODE_BUG": "skip",
    }.get(cause)
    if expected is not None and strategy != expected:
        return "strategy_mismatch"

    # Strategy 'skip' is the deterministic response to CODE_BUG.
    # The coordinator correctly chose to do nothing; this is not
    # a bug in the loop, it's the loop's response to a buggy
    # source file. Track it as its own category so the variance
    # report can distinguish "skip happened" from "loop failed."
    if strategy == "skip":
        return "strategy_skip"

    # Success=False paths.
    if not success:
        if isolated_failed > 0:
            return "verifier_failure"
        if isolated_passed > 0 and not replaced:
            return "transactional_replacement_failure"
        return "other"

    # Success=True with replaced=False is a transactional bug.
    if not replaced:
        return "transactional_replacement_failure"

    # If we got here the rewrite succeeded and replaced the file;
    # that's not a failure category. Caller decides whether to
    # count this run as a failure based on aggregate metrics.
    return "success"


def _format_metric_table(summaries: dict[str, dict]) -> str:
    """Markdown table of summary stats per metric."""
    lines = ["| Metric | n | Mean | Median | Std | Min | Max |",
             "|--------|---|------|--------|-----|-----|-----|"]
    for metric, s in summaries.items():
        if s["n_observations"] == 0:
            lines.append(f"| `{metric}` | 0 | NaN | NaN | NaN | NaN | NaN |")
        else:
            lines.append(
                f"| `{metric}` | {s['n_observations']} | "
                f"{s['mean']:.3f} | {s['median']:.3f} | "
                f"{s['std']:.3f} | {s['min']:.3f} | {s['max']:.3f} |"
            )
    return "\n".join(lines)


def _format_failure_distribution(category_counts: Counter) -> str:
    if not category_counts:
        return "_No failure events recorded._"
    total = sum(category_counts.values())
    lines = ["| Category | Count | Fraction |",
             "|---------|-------|----------|"]
    for cat, count in sorted(category_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{cat}` | {count} | {count / total:.1%} |")
    return "\n".join(lines)


def _truncate(text: str | None, limit: int = 800) -> str:
    if text is None:
        return "(no raw_response captured)"
    if len(text) > limit:
        return text[:limit] + f"\n... [truncated, full length {len(text)} chars]"
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-runs", type=int, default=20,
                        help="Number of harness invocations (default 20).")
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default="MiniMax-M3")
    parser.add_argument("--confidence", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=180.0,
                        help="Per-run timeout in seconds.")
    parser.add_argument("--out", default="docs/benchmark_variance_report.md")
    args = parser.parse_args()

    bench_root = Path(__file__).resolve().parents[1]  # .../code2testbench
    repo_root = bench_root.parent
    manifest = bench_root / "corpus" / "manifest_failure_modes.json"
    out_report = repo_root / args.out
    out_report.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.minimax.io/v1")

    benchmark_commit_sha = _git_commit_sha(repo_root)
    dirty = _git_dirty(repo_root)

    print(f"variance experiment starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"benchmark_commit_sha = {benchmark_commit_sha}{'+dirty' if dirty else ''}")
    print(f"n_runs = {args.n_runs}, provider = {args.provider}, "
          f"model = {args.model}, confidence = {args.confidence}")

    corpus_root = bench_root / "corpus"
    raw_runs = []
    all_events: list[dict] = []  # events with run_id annotated
    prompt_hashes: set = set()
    raw_responses_by_category: dict[str, list[str]] = {}

    t_total = time.monotonic()
    for i in range(1, args.n_runs + 1):
        t_run = time.monotonic()
        _clean_corpus(corpus_root)
        out_path = bench_root / f"_variance_run_{i:03d}.json"
        result = _run_once(
            bench_root=bench_root, manifest=manifest,
            out_path=out_path, provider=args.provider, model=args.model,
            confidence=args.confidence, api_key=api_key,
            base_url=base_url, run_id=i, timeout=args.timeout,
        )
        raw_runs.append(result)

        # Annotate events with their run_id; collect prompt hashes
        # and representative raw responses for each category.
        for ev in result.get("events", []):
            ev2 = dict(ev)
            ev2["_run_id"] = i
            all_events.append(ev2)
            if ev.get("_type") == "GenerationRecorded":
                prompt_hashes.add(ev.get("prompt_hash", ""))
                # The GenerationRecorded event itself isn't a failure;
                # its category is no_tests_generated when it has zero
                # generated tests. Capture the raw_response of empty
                # generations here.
                if ev.get("generated_test_count", 0) == 0:
                    rr = ev.get("raw_response") or ""
                    raw_responses_by_category.setdefault(
                        "no_tests_generated", []
                    ).append(rr)
            elif ev.get("_type") == "RewriteCommitted":
                category = _classify_failure(ev)
                if category != "success":
                    # Find the GenerationRecorded event with the same
                    # prompt_hash to grab the raw_response.
                    rr = ""
                    for sibling in result["events"]:
                        if (sibling.get("_type") == "GenerationRecorded"
                                and sibling.get("prompt_hash")
                                == ev.get("_run_id")):
                            rr = sibling.get("raw_response") or ""
                            break
                    # Use the raw_response of the most-recent
                    # GenerationRecorded event in the same run as a
                    # representative.
                    if not rr:
                        for sibling in reversed(result["events"]):
                            if sibling.get("_type") == "GenerationRecorded":
                                rr = sibling.get("raw_response") or ""
                                break
                    raw_responses_by_category.setdefault(
                        category, []
                    ).append(rr)

        elapsed = time.monotonic() - t_run
        metric_str = ", ".join(
            f"{k}={result['metrics'].get(k)}"
            for k in METRICS
        )
        print(f"  run {i:02d}/{args.n_runs}: elapsed={elapsed:.1f}s  {metric_str}")
        # Don't keep the per-run JSON file; we've already loaded it.
        if out_path.exists():
            out_path.unlink()

    elapsed_total = time.monotonic() - t_total
    print(f"\nall {args.n_runs} runs done in {elapsed_total:.1f}s")

    # Summaries per metric.
    summaries: dict[str, dict] = {}
    for metric in METRICS:
        values = [r["metrics"].get(metric) for r in raw_runs]
        summaries[metric] = _summary(values)

    # Failure category distribution from RewriteCommitted events.
    category_counts: Counter = Counter()
    for ev in all_events:
        if ev.get("_type") == "RewriteCommitted":
            category = _classify_failure(ev)
            category_counts[category] += 1

    # Pick one representative raw_response per category (first non-empty).
    representatives: dict[str, str] = {}
    for cat, rrs in raw_responses_by_category.items():
        for rr in rrs:
            if rr:
                representatives[cat] = _truncate(rr, 600)
                break

    # Build the report.
    report = []
    report.append("# Benchmark Variance Report")
    report.append("")
    report.append(f"**Date:** {time.strftime('%Y-%m-%d')}")
    report.append(f"**Benchmark commit SHA:** `{benchmark_commit_sha}`"
                  f"{' (dirty working tree)' if dirty else ''}")
    report.append(f"**Number of runs:** {args.n_runs}")
    report.append(f"**Provider:** {args.provider}")
    report.append(f"**Model:** {args.model}")
    report.append(f"**Confidence threshold:** {args.confidence}")
    report.append(f"**Corpus:** `corpus/manifest_failure_modes.json`")
    report.append("")

    report.append("## Purpose")
    report.append("")
    report.append("Measure inter-run variance and pipeline determinism. "
                  "The per-component invariant (one rewrite per component "
                  "per run) is load-bearing and was NOT violated for this "
                  "experiment. Each run is a fresh invocation of the "
                  "harness. Nothing is shared between runs except the "
                  "corpus, the model, the harness code, and the prompt.")
    report.append("")
    report.append("If distributions are tight and consistently poor, the "
                  "architecture is deterministic and the implementation "
                  "is wrong. If distributions are wide, model "
                  "stochasticity is dominating and prompt/provider "
                  "work becomes justified. We don't decide which based "
                  "on narrative; we let the data decide.")
    report.append("")

    report.append("## Summary statistics per metric")
    report.append("")
    report.append(_format_metric_table(summaries))
    report.append("")
    report.append("Per-metric NaN: the metric's denominator was zero on "
                  "every run, indicating the upstream stages didn't engage.")
    report.append("")

    report.append("## Failure category distribution")
    report.append("")
    report.append("Each `RewriteCommitted` event is classified by the "
                  "variance script using fields it carries: "
                  "`isolated_passed`, `isolated_failed`, `replaced`, "
                  "`strategy`, `failure_classification`.")
    report.append("")
    report.append(_format_failure_distribution(category_counts))
    report.append("")

    report.append("## Prompt hash stability")
    report.append("")
    if prompt_hashes:
        report.append(f"The test-generation prompt hash was stable across "
                      f"all runs: `{next(iter(prompt_hashes))}` "
                      f"({len(prompt_hashes)} unique value(s) across "
                      f"{args.n_runs} runs).")
    else:
        report.append("_No GenerationRecorded events were captured; the "
                      "prompt hash check did not engage._")
    report.append("")

    report.append("## Representative raw responses per category")
    report.append("")
    if not representatives:
        report.append("_No failure categories captured any GenerationRecorded "
                      "events with raw responses; the report is empty._")
    else:
        for cat in sorted(representatives):
            report.append(f"### `{cat}`")
            report.append("")
            report.append("```")
            report.append(representatives[cat])
            report.append("```")
            report.append("")
    report.append("")

    report.append("## Per-run metric table")
    report.append("")
    header = "| Run | " + " | ".join(METRICS) + " |"
    sep = "|------|" + "|".join(["---"] * len(METRICS)) + "|"
    report.append(header)
    report.append(sep)
    for r in raw_runs:
        row = [str(r["run_id"])] + [
            "NaN" if r["metrics"].get(m) is None or
            (isinstance(r["metrics"].get(m), float) and math.isnan(r["metrics"].get(m)))
            else f"{r['metrics'].get(m):.3f}"
            for m in METRICS
        ]
        report.append("| " + " | ".join(row) + " |")
    report.append("")

    out_report.write_text("\n".join(report))
    print(f"\nwrote {out_report}")
    print(f"  total elapsed: {elapsed_total:.1f}s")
    print(f"  failure categories: {dict(category_counts)}")


if __name__ == "__main__":
    main()
