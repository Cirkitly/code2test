"""End-to-end tests for the generate -> write -> verify pipeline, using an offline model."""

import asyncio
from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from code2test.agents import test_agent as test_agent_mod
from code2test.core import generator as generator_mod
from code2test.core.models import GenerationConfig
from code2test.src.be.dependency_analyzer import DependencyGraphBuilder
from code2test.src.config import Config

SOURCE = '''
def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    return a + b
'''


def _make_repo(tmp_path: Path) -> Path:
    pkg = tmp_path / "calc"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "ops.py").write_text(SOURCE)
    return tmp_path


def _components(repo: Path) -> dict:
    """Build component dicts the same way the `test` CLI command does."""
    config = Config(
        repo_path=str(repo),
        output_dir=str(repo / "tests"),
        dependency_graph_dir=str(repo / ".code2test" / "dependency_graphs"),
        docs_dir=str(repo / ".code2test" / "docs"),
        max_depth=2,
        llm_base_url="",
        llm_api_key="",
        main_model="",
        cluster_model="",
        agent_instructions={"include_patterns": None, "exclude_patterns": ["tests", "test_*.py"]},
    )
    nodes, _ = DependencyGraphBuilder(config).build_dependency_graph()
    components = {}
    for key, node in nodes.items():
        data = node.model_dump()
        data["dependencies"] = list(data.get("depends_on", []))
        components[key] = data
    return components


def _run(repo: Path, test_code: str):
    gen = generator_mod.TestGenerator(
        repo_path=str(repo),
        config=GenerationConfig(auto_accept=True, confidence_threshold=0.0, output_dir="tests"),
    )
    gen.test_agent.model = TestModel(
        custom_output_args={
            "tests": [{
                "name": "test_add",
                "description": "adds",
                "test_code": test_code,
                "tests_behavior": "returns the sum",
            }],
            "imports": ["from calc.ops import add"],
        }
    )
    gen.diagnosis_agent.model = TestModel()
    return asyncio.run(gen.generate_tests_for_module(str(repo), _components(repo)))


def test_passing_test_is_written_under_output_dir_and_verified(tmp_path):
    repo = _make_repo(tmp_path)
    suite = _run(repo, "def test_add():\n    assert add(2, 3) == 5\n")

    assert len(suite.test_files) == 1
    test_file = suite.test_files[0]
    assert test_file.path == "tests/calc/test_ops_add.py"
    assert (repo / test_file.path).exists()
    assert test_file.verified


def test_failing_test_is_not_verified(tmp_path):
    repo = _make_repo(tmp_path)
    suite = _run(repo, "def test_add():\n    assert add(2, 3) == 6\n")

    assert len(suite.test_files) == 1
    assert not suite.test_files[0].verified


@pytest.mark.parametrize(
    "source, component, expected",
    [
        ("/repo/calc/ops.py", {"name": "add"}, "tests/calc/test_ops_add.py"),
        ("src/pkg/mod.py", {"id": "pkg.mod.Foo"}, "tests/pkg/test_mod_foo.py"),
        ("mod.py", None, "tests/test_mod.py"),
    ],
)
def test_generate_test_path(source, component, expected):
    agent = test_agent_mod.TestAgent(model="test", repo_path="/repo", output_dir="tests")
    assert agent._generate_test_path(source, component) == expected
