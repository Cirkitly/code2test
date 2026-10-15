"""Tests for run metrics and the benchmark (mutation score, diagnosis accuracy)."""

import asyncio
import json

from code2test.core.benchmark import Benchmark, break_expected_value, generate_mutants
from code2test.core.metrics import FileMetrics, RunMetrics
from code2test.core.models import TestCase as Case, TestFile as File
from tests.test_pipeline import FAILING, PASSING, _make_repo, _run, scripted, tests_reply


def test_metrics_record_first_run_and_repairs(tmp_path):
    repo = _make_repo(tmp_path)
    gen_model = scripted([tests_reply(FAILING), tests_reply(PASSING)])
    _run(repo, gen_model)

    data = json.loads((repo / ".code2test" / "metrics.json").read_text())
    assert data["summary"]["components"] == 1
    assert data["summary"]["components_with_tests"] == 1
    assert data["summary"]["acceptance_rate"] == 1.0
    assert data["summary"]["tests_generated"] == 1
    assert data["summary"]["first_run_passed"] == 0
    assert data["summary"]["first_run_pass_rate"] == 0.0
    assert data["summary"]["tests_kept"] == 1
    assert data["summary"]["repair_rounds"] == 1


def test_metrics_count_discarded_files(tmp_path):
    repo = _make_repo(tmp_path)
    _run(repo, scripted([tests_reply(FAILING)], diagnosis="TEST_WRONG"))
    summary = json.loads((repo / ".code2test" / "metrics.json").read_text())["summary"]
    assert summary["acceptance_rate"] == 0.0
    assert summary["tests_dropped"] == 1 and summary["files_removed"] == 1
    assert summary["diagnoses"] == {"TEST_WRONG": 1}


def test_xfail_only_components_do_not_count_as_accepted():
    metrics = RunMetrics(components=2)
    metrics.files["a"] = FileMetrics(component_id="a", path="a", generated=2, kept=2, xfail=2)
    metrics.files["b"] = FileMetrics(component_id="b", path="b", generated=1, kept=1)
    assert metrics.components_with_tests == 1
    assert metrics.acceptance_rate == 0.5


def test_mutants_change_one_site_each(tmp_path):
    (tmp_path / "m.py").write_text(
        'def check(x):\n    """Doc."""\n    if x > 3:\n        return x + 1\n    return "low"\n\n'
        "def untested():\n    return 1 + 1\n"
    )
    mutants = generate_mutants(tmp_path, "m.py", {"check": "m.check"})
    descriptions = {m.description for m in mutants}
    assert "Gt -> LtE" in descriptions
    assert "Add -> Sub" in descriptions
    assert "3 -> 4" in descriptions
    assert "'low' -> 'low_mutated'" in descriptions
    assert "return value -> None" in descriptions
    assert all(m.component_id == "m.check" for m in mutants)  # untested() is never mutated
    assert not any("Doc._mutated" in m.source for m in mutants)  # docstrings are left alone


def test_break_expected_value():
    assert break_expected_value("def test_x():\n    assert f(2) == 5\n") == "def test_x():\n    assert f(2) == 6"
    assert "'ab_wrong'" in break_expected_value("def test_x():\n    assert f() == 'ab'\n")
    assert break_expected_value("def test_x():\n    assert f()\n") is None


def _benchmark_repo(tmp_path):
    repo = _make_repo(tmp_path)
    tf = File(
        path="tests/calc/test_ops_add.py", component_id="calc.ops.add", component_path="calc/ops.py",
        imports=["import pytest", "from calc.ops import add"], verified=True,
        test_cases=[Case(name="test_add", intent_text="sum", test_code=PASSING)],
    )
    (repo / tf.path).parent.mkdir(parents=True)
    (repo / tf.path).write_text(tf.get_full_content())
    from code2test.core.models import Intent

    intents = {"calc.ops.add": Intent(component_id="calc.ops.add", component_path="calc/ops.py",
                                      intent_text="Return the sum", confidence=0.9)}
    components = {"calc.ops.add": {"id": "calc.ops.add", "name": "add", "relative_path": "calc/ops.py",
                                   "source_code": "def add(a, b):\n    return a + b\n"}}
    return repo, tf, intents, components


def test_benchmark_kills_mutants_and_restores_source(tmp_path):
    repo, tf, intents, components = _benchmark_repo(tmp_path)
    original = (repo / "calc/ops.py").read_text()

    result = asyncio.run(Benchmark(repo, [tf], intents, components).run(max_mutants=10))

    assert result.mutants_total == 2  # a + b -> a - b, return value -> None
    assert result.mutants_killed == 2 and result.mutation_score == 1.0
    assert (repo / "calc/ops.py").read_text() == original


def test_benchmark_scores_diagnoses_against_known_causes(tmp_path):
    from code2test.agents.diagnosis_agent import DiagnosisAgent

    repo, tf, intents, components = _benchmark_repo(tmp_path)
    agent = DiagnosisAgent(model=scripted([tests_reply(PASSING)], diagnosis="CODE_BUG"))

    result = asyncio.run(Benchmark(repo, [tf], intents, components, diagnosis_agent=agent)
                         .run(max_mutants=10, max_diagnoses=1))

    expected = sorted(c.expected for c in result.diagnosis_cases)
    assert expected == ["CODE_BUG", "TEST_WRONG"]
    assert result.diagnosis_accuracy == 0.5  # always answering CODE_BUG gets only the code-bug case right
    assert not list((repo / "tests/calc").glob("_c2t_probe_*"))
