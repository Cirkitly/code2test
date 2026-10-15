#!/usr/bin/env python3
"""
Collect the results of the Code2Test experiment runs into research/data/.

Usage:
    python research/scripts/collect_results.py RUNS_DIR [SECOND_RUNS_DIR]

RUNS_DIR holds the main runs reported in the paper's results table. The optional
SECOND_RUNS_DIR holds a second, independent run of each configuration, used to
show run-to-run variation.

Run it with the Python environment where code2test is installed: it re-runs the
static intent analysis and the mutant sampling to attribute intents and mutants.

Each directory holds one directory per run, named <subject>-<model> (for example
inflection-flash), each containing:
    project/.code2test/metrics.json    written by `code2test test --auto`
    project/.code2test/benchmark.json  written by `code2test benchmark`
    project/.code2test/code2test.db    intents and the test registry
    project/tests/                     the generated test suite
    verify.log                         output of `code2test verify tests/`
    seconds.txt                        wall time of `code2test test --auto`, in seconds

Outputs (second runs go to research/data/second-runs/ instead of research/data/runs/):
    research/data/runs/<run>/{metrics,benchmark}.json and verify.log (copies)
    research/data/runs/<run>/tests/    the generated test suite (copy)
    research/data/runs/<run>/intents.json  inferred intents, and whether the model re-inferred them
    research/data/results.csv          one row per run (column "run": 1 or 2)
    research/paper/results.tex         LaTeX macros used by the paper, so the
                                       measured results are not typed by hand
"""

import collections
import csv
import json
import math
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
SUBJECTS = {"inflection": "Inflection", "tinydb": "TinyDB"}
MODELS = {"flash": "Flash", "m3": "MThree"}


def percent(value) -> int:
    """Percentage rounded half up (Python's round() rounds 72.5 down and 77.5 up)."""
    return math.floor(100 * value + 0.5 + 1e-9)


def pct(value):
    return "n/a" if value is None else f"{percent(value)}\\%"


def verify_counts(log: str):
    """(passed, total, skipped) from `code2test verify` output."""
    match = re.search(r"(\d+)/(\d+) tests passed", log)
    passed, total = (int(match.group(1)), int(match.group(2))) if match else (None, None)
    skipped = None
    rows = re.findall(r"│\s*\S+\s*│\s*(\d+)\s*│\s*(\d+)\s*│\s*(\d+)\s*│", log)
    if rows:
        skipped = sum(int(r[2]) for r in rows)
    return passed, total, skipped


def static_intents(project: Path, threshold: float = 0.6):
    """Intents from static analysis alone, as `code2test test` computes them before any model call."""
    from code2test.core.intent import IntentExtractor
    from code2test.src.be.dependency_analyzer import DependencyGraphBuilder
    from code2test.src.config import Config

    with tempfile.TemporaryDirectory() as tmp:
        # Analyze the project as it was before generation: without tests/ and .code2test/
        work = Path(tmp) / project.name
        shutil.copytree(project, work, ignore=shutil.ignore_patterns("tests", ".code2test", "__pycache__"))
        config = Config(repo_path=str(work), output_dir="tests",
                        dependency_graph_dir=str(work / ".graphs"), docs_dir=str(work / ".docs"),
                        max_depth=2, llm_base_url="", llm_api_key="", main_model="", cluster_model="",
                        agent_instructions={"include_patterns": None, "exclude_patterns": None})
        nodes, _ = DependencyGraphBuilder(config).build_dependency_graph()
    components = {}
    for node_id, node in nodes.items():
        data = node.model_dump()
        data["dependencies"] = list(data.get("depends_on") or [])
        if str(data.get("file_path", "")).endswith(".py"):
            components[node_id] = data
    extractor, intents = IntentExtractor(threshold), {}
    for comp_id, component in components.items():
        deps = {d: intents[d] for d in component["dependencies"] if d in intents}
        intents[comp_id] = extractor.extract_intent(component, deps)
    return intents


def export_intents(project: Path, out: Path):
    """Write intents.json; return (components below the threshold, intents the model re-inferred)."""
    static = static_intents(project)
    db = sqlite3.connect(project / ".code2test" / "code2test.db")
    rows = db.execute("SELECT component_id, intent_text, confidence FROM intents ORDER BY component_id").fetchall()
    db.close()
    below = sum(1 for i in static.values() if i.needs_clarification(0.6))
    exported, from_model = [], 0
    for comp_id, text, confidence in rows:
        source = "static" if comp_id in static and static[comp_id].intent_text == text else "model"
        from_model += source == "model"
        exported.append({"component": comp_id, "intent": text, "confidence": round(confidence, 3),
                         "static_confidence": round(static[comp_id].confidence, 3) if comp_id in static else None,
                         "source": source})
    (out / "intents.json").write_text(json.dumps(exported, indent=2) + "\n")
    return below, from_model


def mutants_by_component(project: Path, total: int):
    """Sampled mutants per component, re-drawn exactly as `code2test benchmark` drew them."""
    from code2test.core.benchmark import Benchmark
    from code2test.storage.test_registry import TestRegistry

    registry = TestRegistry(str(project / ".code2test" / "code2test.db"))
    test_files = [tf for tf in registry.get_all_tests() if (project / tf.path).exists()]
    sample = Benchmark(project, test_files, {}, {}).mutants(total)
    return collections.Counter(m.component_id for m in sample)


def is_string_mutation(description: str) -> bool:
    return bool(re.match(r"^(['\"]).*\1 -> (['\"]).*\2$", description))


def collect(runs_dir: Path, run_number: int):
    """Copy one set of runs into research/data and return (rows, macros)."""
    data_dir = "runs" if run_number == 1 else "second-runs"
    tag = "" if run_number == 1 else "Second"
    rows, macros = [], []
    for run in sorted(p for p in runs_dir.iterdir() if p.is_dir() and "-" in p.name):
        subject, model = run.name.split("-", 1)
        if subject not in SUBJECTS or model not in MODELS:
            continue
        state = run / "project" / ".code2test"
        metrics = json.loads((state / "metrics.json").read_text())
        bench = json.loads((state / "benchmark.json").read_text())
        verify_log = (run / "verify.log").read_text()
        seconds = int((run / "seconds.txt").read_text().strip())

        out = RESEARCH / "data" / data_dir / run.name
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        shutil.copy(state / "metrics.json", out / "metrics.json")
        shutil.copy(state / "benchmark.json", out / "benchmark.json")
        (out / "verify.log").write_text(verify_log)
        shutil.copytree(run / "project" / "tests", out / "tests",
                        ignore=shutil.ignore_patterns("__pycache__", "reports", ".pytest_cache"))
        intents_below, intents_from_model = export_intents(run / "project", out)

        # Where the mutants were, and which survived
        sampled = mutants_by_component(run / "project", bench["mutants_total"])
        survived = collections.Counter(x["component"] for x in bench["survivors"])
        top, top_mutants = sampled.most_common(1)[0]
        top_killed = top_mutants - survived[top]
        string_survivors = sum(1 for x in bench["survivors"] if is_string_mutation(x["mutation"]))

        s = metrics["summary"]
        # Recompute rates from counts: the summary stores them rounded, and rounding twice can be off by one point
        def ratio(num, den):
            return num / den if den else None
        passed, total, skipped = verify_counts(verify_log)
        diag = bench["diagnosis_by_expected_cause"]
        row = {
            "run": run_number, "subject": subject, "model": model,
            "components": s["components"], "components_with_tests": s["components_with_tests"],
            "acceptance_rate": ratio(s["components_with_tests"], s["components"]),
            "tests_generated": s["tests_generated"], "first_run_passed": s["first_run_passed"],
            "first_run_pass_rate": ratio(s["first_run_passed"], s["tests_generated"]),
            "tests_kept": s["tests_kept"], "tests_xfail": s["tests_xfail"], "tests_dropped": s["tests_dropped"],
            "repair_rounds": s["repair_rounds"], "llm_failures": s["llm_failures"],
            "suite_cases_passed": passed, "suite_cases_total": total, "suite_cases_skipped": skipped,
            "seconds": seconds,
            "mutants_total": bench["mutants_total"], "mutants_killed": bench["mutants_killed"],
            "mutation_score": bench["mutation_score"],
            "mutants_killed_by_own_tests": bench.get("mutants_killed_by_own_tests"),
            "own_tests_mutation_score": bench.get("own_tests_mutation_score"),
            "diagnosis_accuracy": bench["diagnosis_accuracy"],
            "code_bug_correct": diag.get("CODE_BUG", {}).get("correct"),
            "code_bug_cases": diag.get("CODE_BUG", {}).get("cases"),
            "test_wrong_correct": diag.get("TEST_WRONG", {}).get("correct"),
            "test_wrong_cases": diag.get("TEST_WRONG", {}).get("cases"),
            "intents_below_threshold": intents_below, "intents_from_model": intents_from_model,
            "survivors": len(bench["survivors"]), "string_literal_survivors": string_survivors,
            "most_mutated_component": top, "most_mutated_sampled": top_mutants,
            "most_mutated_killed": top_killed,
        }
        rows.append(row)

        p = SUBJECTS[subject] + MODELS[model] + tag
        def m(name, value):
            macros.append(f"\\newcommand{{\\{p}{name}}}{{{value}}}")
        m("Components", row["components"])
        m("WithTests", row["components_with_tests"])
        m("Acceptance", pct(row["acceptance_rate"]))
        m("Generated", row["tests_generated"])
        m("FirstPassed", row["first_run_passed"])
        m("FirstRate", pct(row["first_run_pass_rate"]))
        m("Kept", row["tests_kept"])
        m("Xfail", row["tests_xfail"])
        m("Dropped", row["tests_dropped"])
        m("Repairs", row["repair_rounds"])
        m("CasesPassed", passed)
        m("CasesTotal", total)
        m("CasesSkipped", skipped or 0)
        m("Seconds", seconds)
        m("Mutants", row["mutants_total"])
        m("Killed", row["mutants_killed"])
        m("MutationScore", pct(row["mutation_score"]))
        m("KilledOwn", row["mutants_killed_by_own_tests"])
        m("OwnScore", pct(row["own_tests_mutation_score"]))
        m("DiagAccuracy", pct(row["diagnosis_accuracy"]))
        m("DiagCorrect", (row["code_bug_correct"] or 0) + (row["test_wrong_correct"] or 0))
        m("DiagCases", (row["code_bug_cases"] or 0) + (row["test_wrong_cases"] or 0))
        m("CodeBugCorrect", row["code_bug_correct"])
        m("CodeBugCases", row["code_bug_cases"])
        m("TestWrongCorrect", row["test_wrong_correct"])
        m("TestWrongCases", row["test_wrong_cases"])
        m("IntentsBelow", intents_below)
        m("IntentsFromModel", intents_from_model)
        m("Survivors", row["survivors"])
        m("StringSurvivors", string_survivors)
        m("TopComponent", "\\code{" + top.split(".")[-1].replace("_", "\\_") + "}")
        m("TopMutants", top_mutants)
        m("TopKilled", top_killed)
        m("RestMutants", row["mutants_total"] - top_mutants)
        m("RestKilled", row["mutants_killed"] - top_killed)

    # Ranges across runs, for the abstract and summary sentences
    for key, name in [("acceptance_rate", "Acceptance"), ("first_run_pass_rate", "FirstRate"),
                      ("mutation_score", "MutationScore"), ("own_tests_mutation_score", "OwnScore"),
                      ("diagnosis_accuracy", "DiagAccuracy")]:
        values = [r[key] for r in rows if r[key] is not None]
        if values:
            macros.append(f"\\newcommand{{\\{tag}Min{name}}}{{{pct(min(values))}}}")
            macros.append(f"\\newcommand{{\\{tag}Max{name}}}{{{pct(max(values))}}}")
    macros.append(f"\\newcommand{{\\{tag}NumRuns}}{{{len(rows)}}}")
    return rows, macros


def main(runs_dir: Path, second_runs_dir: Path = None) -> None:
    rows, macros = collect(runs_dir, 1)
    all_rows = list(rows)
    if second_runs_dir is not None:
        second_rows, second_macros = collect(second_runs_dir, 2)
        all_rows += second_rows
        macros += second_macros
    with open(RESEARCH / "data" / "results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    header = "% Generated by research/scripts/collect_results.py from research/data. Do not edit.\n"
    (RESEARCH / "paper" / "results.tex").write_text(header + "\n".join(macros) + "\n")
    write_abstract(rows)
    print(f"Collected {len(all_rows)} runs")


ABSTRACT = """Large language models (LLMs) can write unit tests for untested legacy code, but practical generators keep only tests that pass, and recent studies show that this filter locks existing bugs into the generated suite. We present Code2Test, an open-source tool for Python that first infers, stores and lets developers edit an explicit statement of intent for every function and class. It generates pytest tests against that intent, executes them, repairs failures from their pytest output, and diagnoses tests that still fail as a wrong test, a code bug or a wrong intent. Suspected code bugs are kept as expected failures with the diagnosis attached, so the written suite always passes while the signal survives. A built-in benchmark reports mutation score and the accuracy of the diagnosis on failures of known cause. On two open-source libraries (426 and 2,170 lines) with two MiniMax models, Code2Test produced passing tests for {acceptance} of components. Before any repair, {first} of generated tests passed, and the suites killed {mutation} of sampled mutants. The diagnosis was correct on {diagnosis} of failures of known cause. Second runs gave similar results; one kept a test as an expected failure that exposes a real defect in inflection, which singularizes "campuses" to "campuse". Surviving mutants concentrated in one function that a run tested only structurally and in string literals that tests do not observe, and nearly all intents came from docstrings. Because both libraries are mature, the study measures validity and fault detection, not whether intent-first generation avoids locking in bugs; we describe the experiment that would. We also report eight failure modes that appeared only with a real model. Each of the tool's techniques has a precedent; its contribution is their combination in one open tool and the empirical lessons from running it."""


def write_abstract(rows) -> None:
    """Plain-text abstract for the arXiv metadata form (max 1,920 characters)."""
    def span(key):
        values = [r[key] for r in rows if r[key] is not None]
        lo, hi = percent(min(values)), percent(max(values))
        return f"{lo}%" if lo == hi else f"{lo}-{hi}%"
    text = ABSTRACT.format(acceptance=span("acceptance_rate"), first=span("first_run_pass_rate"),
                           mutation=span("mutation_score"), diagnosis=span("diagnosis_accuracy"))
    assert len(text) <= 1920, f"arXiv abstracts are limited to 1,920 characters ({len(text)})"
    (RESEARCH / "paper" / "abstract.txt").write_text(text + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
