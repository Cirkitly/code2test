"""
Test quality of a generated suite: behavioral coverage and diagnostic accuracy.

Behavioral coverage is reported per component in two ways:

- Behaviors tested: the distinct behaviors that the component's passing tests check,
  as stated by the model for each generated test, next to the component's inferred intent.
- Mutation score: the share of injected single-site behavior changes (mutants) that the
  generated suite detects, from the last `code2test benchmark` run.

Diagnostic accuracy also comes from that benchmark run: how often the diagnosis agent named
the right cause of a failure whose cause is known.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from code2test.core.models import TestFile, TestStatus, is_xfail


def _ratio(num: int, den: int) -> Optional[float]:
    return num / den if den else None


def _behaviors(test_file: TestFile) -> List[str]:
    """Distinct behaviors checked by the file's passing tests (case and spacing ignored)."""
    seen: Dict[str, str] = {}
    for tc in test_file.test_cases:
        if tc.status != TestStatus.PASSED or is_xfail(tc):
            continue
        text = " ".join((tc.intent_text or tc.name).split())
        seen.setdefault(text.lower(), text)
    return list(seen.values())


def load_benchmark(repo_root: Path) -> Optional[Dict[str, Any]]:
    """The last `code2test benchmark` result, or None if there is none."""
    path = Path(repo_root) / ".code2test" / "benchmark.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def quality_report(
    repo_root: Path, test_files: List[TestFile], intents: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Summarize behavioral coverage and diagnostic accuracy.

    Args:
        repo_root: Project root (where .code2test/ lives)
        test_files: Generated test files, with their test cases and statuses
        intents: Component ID -> Intent

    Returns:
        A JSON-serializable dict with "summary", "components" and "benchmark" keys.
    """
    repo_root = Path(repo_root)
    bench = load_benchmark(repo_root)
    by_component = (bench or {}).get("by_component") or {}

    files_by_component: Dict[str, List[TestFile]] = {}
    for tf in test_files:
        files_by_component.setdefault(tf.component_id, []).append(tf)

    components = []
    for comp_id in sorted(set(files_by_component) | set(intents)):
        files = files_by_component.get(comp_id, [])
        behaviors: List[str] = []
        for tf in files:
            behaviors += [b for b in _behaviors(tf) if b not in behaviors]
        intent = intents.get(comp_id)
        mutants = by_component.get(comp_id)
        components.append(
            {
                "component": comp_id,
                "intent": getattr(intent, "intent_text", None),
                "tests_passing": sum(
                    1
                    for tf in files
                    for tc in tf.test_cases
                    if tc.status == TestStatus.PASSED and not is_xfail(tc)
                ),
                "tests_xfail": sum(1 for tf in files for tc in tf.test_cases if is_xfail(tc)),
                "behaviors_tested": behaviors,
                "mutants": mutants["mutants"] if mutants else None,
                "mutants_killed": mutants["killed"] if mutants else None,
                "mutation_score": _ratio(mutants["killed"], mutants["mutants"])
                if mutants
                else None,
            }
        )

    # A benchmark older than the last generation run measured a different suite
    metrics_path = repo_root / ".code2test" / "metrics.json"
    bench_path = repo_root / ".code2test" / "benchmark.json"
    stale = (
        bool(bench)
        and metrics_path.exists()
        and metrics_path.stat().st_mtime > bench_path.stat().st_mtime
    )

    benchmark = {"available": bench is not None, "stale": stale}
    if bench:
        benchmark.update(
            {
                # Results written before benchmark.json recorded a time: use the file's
                "created_at": bench.get("created_at")
                or datetime.fromtimestamp(bench_path.stat().st_mtime, timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "mutation_score": bench.get("mutation_score"),
                "mutants_killed": bench.get("mutants_killed"),
                "mutants_total": bench.get("mutants_total"),
                "diagnosis_accuracy": bench.get("diagnosis_accuracy"),
                "diagnosis_by_expected_cause": bench.get("diagnosis_by_expected_cause", {}),
            }
        )

    return {
        "summary": {
            "components": len(components),
            "components_with_passing_tests": sum(1 for c in components if c["tests_passing"]),
            "behaviors_tested": sum(len(c["behaviors_tested"]) for c in components),
            "mutation_score": benchmark.get("mutation_score"),
            "diagnosis_accuracy": benchmark.get("diagnosis_accuracy"),
        },
        "components": components,
        "benchmark": benchmark,
    }
